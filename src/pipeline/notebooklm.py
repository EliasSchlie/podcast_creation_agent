"""NotebookLM automation — create notebook, upload PDF, generate podcast, download audio.

UI flow (verified March 2026):
1. Home: click "+ Create new" button
2. Source dialog opens automatically — click "Upload files" → file chooser → set PDF
3. Wait for upload processing, dialog closes, source appears in sidebar
4. Click "Customize Audio Overview" (pen icon next to Audio Overview in Studio panel)
5. In dialog: format "Deep Dive" is default, click "Long" for length
6. Click "Generate" button in dialog
7. Poll for completion — "Generating" text disappears, Play button appears
8. Click "More" (three-dot) menu next to audio entry → "Download"
"""

import logging
import time
from pathlib import Path
from playwright.sync_api import Playwright, Page

from pipeline.config import NOTEBOOKLM_URL, NOTEBOOKLM_PROFILE
from pipeline.sessions import launch_persistent

log = logging.getLogger(__name__)

GENERATION_TIMEOUT_S = 30 * 60  # 30 minutes max
POLL_INTERVAL_S = 30


def create_podcast_from_pdf(
    pw: Playwright,
    pdf_path: Path,
    output_dir: Path,
    headless: bool = True,
    duration: str = "Default",
    profile_dir: Path | None = None,
) -> Path:
    """Full flow: create notebook → upload PDF → generate podcast → download audio.
    duration: "Short", "Default", or "Long"
    profile_dir: custom browser profile (for multi-account support)
    """
    log.info(
        "Starting NotebookLM podcast creation for: %s (duration=%s)",
        pdf_path.name,
        duration,
    )
    ctx = launch_persistent(pw, profile_dir or NOTEBOOKLM_PROFILE, headless=headless)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        return _run_flow(page, pdf_path, output_dir, duration=duration)
    finally:
        ctx.close()


def _run_flow(
    page: Page, pdf_path: Path, output_dir: Path, duration: str = "Default"
) -> Path:
    # 1. Navigate to home
    log.info("[1/8] Navigating to NotebookLM...")
    page.goto(NOTEBOOKLM_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(5000)
    log.info("URL: %s", page.url)

    # 2. Create new notebook — use the "+ Create new" button
    log.info("[2/8] Creating new notebook...")
    page.locator("text=Create new").first.click(force=True)
    page.wait_for_timeout(5000)
    log.info("URL after create: %s", page.url)

    # 3. Upload PDF via the auto-opened source dialog
    log.info("[3/8] Uploading PDF: %s", pdf_path.name)
    with page.expect_file_chooser(timeout=15_000) as fc_info:
        page.locator("text=Upload files").first.click()
    fc_info.value.set_files(str(pdf_path))
    log.info("File set via file chooser, waiting for processing...")

    # Wait for upload to complete — source appears in sidebar, dialog closes
    page.wait_for_timeout(10_000)
    try:
        page.wait_for_function(
            "() => !document.querySelector('[role=\"dialog\"]') || "
            "document.querySelector('[role=\"dialog\"]').offsetParent === null",
            timeout=120_000,
        )
    except Exception:
        log.warning("Upload dialog may still be open")
    page.wait_for_timeout(5000)
    page.screenshot(path=str(output_dir / "debug_after_upload.png"))
    log.info("Upload complete")

    # 4. Open Customize Audio Overview dialog
    log.info("[4/8] Opening Customize Audio Overview...")
    page.locator("[aria-label='Customize Audio Overview']").first.click()
    page.wait_for_timeout(3000)

    # 5. Set length (Short/Default/Long toggle)
    log.info("[5/8] Setting length to %s...", duration)
    if duration != "Default":
        page.get_by_text(duration, exact=True).click(force=True)
        page.wait_for_timeout(1000)
    else:
        log.info("Using default duration, no click needed")

    # 6. Click Generate
    log.info("[6/8] Clicking Generate...")
    page.locator("button:has-text('Generate')").first.click()
    page.wait_for_timeout(5000)
    page.screenshot(path=str(output_dir / "debug_after_generate.png"))

    # 7. Wait for generation to complete
    log.info("[7/8] Waiting for generation (may take 5-15 minutes)...")
    _wait_for_generation(page)

    # 8. Download audio
    log.info("[8/8] Downloading audio...")
    audio_path = _download_audio(page, output_dir, pdf_path.stem)
    log.info("Audio saved: %s (%d bytes)", audio_path, audio_path.stat().st_size)
    return audio_path


def _wait_for_generation(page: Page):
    """Poll until generation completes."""
    start = time.time()
    while time.time() - start < GENERATION_TIMEOUT_S:
        body_text = page.locator("body").inner_text()

        # Check for rate limit / error messages (fail fast)
        if "limit" in body_text.lower() and "come back later" in body_text.lower():
            raise RuntimeError(
                "NotebookLM rate limit hit: 'Audio Overview limit, come back later.' "
                "Wait for the daily limit to reset and try again."
            )

        # Check if generation is still running
        if "Generating" in body_text:
            elapsed = time.time() - start
            if (
                elapsed % 120 < POLL_INTERVAL_S
            ):  # Log every ~2 min instead of every poll
                log.info("Still generating... (%.0fs elapsed)", elapsed)
            page.wait_for_timeout(POLL_INTERVAL_S * 1000)
            continue

        # Check for Play button = generation complete
        play_count = page.locator("[aria-label='Play']").count()
        if play_count > 0:
            elapsed = time.time() - start
            log.info("Generation complete! (%.0fs)", elapsed)
            return

        # Neither generating nor play button — might be transitioning
        log.info("Waiting for state change...")
        page.wait_for_timeout(5000)

    raise TimeoutError(f"Generation did not complete within {GENERATION_TIMEOUT_S}s")


def _download_audio(page: Page, output_dir: Path, stem: str) -> Path:
    """Download via More menu → Download."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / f"{stem}.wav"

    # Click Audio Overview to make sure the audio panel is visible
    try:
        page.locator("[aria-label='Audio Overview']").first.click()
        page.wait_for_timeout(2000)
    except Exception:
        pass

    # Try all "More" buttons (aria-label='More'), clicking each and checking for Download menu
    more_buttons = page.locator("[aria-label='More']").all()
    log.info(
        "Found %d 'More' buttons, trying each for Download menu", len(more_buttons)
    )

    for i in range(len(more_buttons)):
        try:
            more_buttons[i].click()
            page.wait_for_timeout(1500)

            # Check if "Download" menu item appeared (with save_alt icon)
            dl = page.locator("text=Download").first
            if dl.is_visible(timeout=2000):
                log.info("Found Download in menu from More button %d", i)
                with page.expect_download(timeout=120_000) as dl_info:
                    dl.click()
                download = dl_info.value
                download.save_as(str(dest))
                return dest
            else:
                # Close menu
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
        except Exception as e:
            log.debug("More button %d failed: %s", i, e)
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            continue

    page.screenshot(path=str(output_dir / "debug_download_fail.png"))
    raise RuntimeError("Could not download audio")
