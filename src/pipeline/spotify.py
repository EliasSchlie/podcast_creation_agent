"""Spotify Creators automation — create podcasts and upload episodes."""

import logging
from pathlib import Path
from playwright.sync_api import Playwright

from pipeline.config import SPOTIFY_WIZARD_URL, SPOTIFY_CREATORS_URL, OUTPUT_DIR
from pipeline.sessions import get_spotify_context

log = logging.getLogger(__name__)


def create_new_podcast(pw: Playwright, podcast_name: str, headless: bool = True) -> str:
    """
    Create a new podcast on Spotify Creators.
    Returns the podcast ID from the URL.

    Flow (as of 2026-03): User settings menu > Add a new show > Create a new show >
    fill form (name, description, category, language) > Next > upload cover art > Next >
    lands on dashboard with podcast ID in URL.
    """
    log.info("Creating new Spotify podcast: %s", podcast_name)
    ctx = get_spotify_context(pw, headless=headless)

    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(SPOTIFY_CREATORS_URL, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(3000)
        log.info("Current URL after login: %s", page.url)

        # Step 1: Open user settings menu (top-right)
        user_menu = page.get_by_role("button", name="User settings menu")
        user_menu.wait_for(state="visible", timeout=10_000)
        user_menu.click()
        page.wait_for_timeout(1000)

        # Step 2: Click "Add a new show"
        add_show = page.get_by_role("button", name="Add a new show")
        add_show.wait_for(state="visible", timeout=5_000)
        add_show.click()
        page.wait_for_timeout(2000)

        # Step 3: Click "Create a new show" in the dialog
        create_show = page.get_by_role("button", name="Create a new show")
        create_show.wait_for(state="visible", timeout=5_000)
        create_show.click()
        page.wait_for_timeout(3000)

        # Step 4: Fill the form
        log.info("Filling podcast details...")
        page.get_by_role("textbox", name="Show name").fill(podcast_name)
        page.get_by_role("textbox", name="Description").fill(
            f"AI-generated podcast: {podcast_name}"
        )

        # Select category and language
        category_select = page.get_by_role("combobox", name="Category")
        if category_select.is_visible(timeout=3000):
            category_select.select_option("Technology")
        language_select = page.get_by_role("combobox", name="Language")
        if language_select.is_visible(timeout=3000):
            language_select.select_option("English")

        # Click Next
        page.get_by_role("button", name="Next").click()
        page.wait_for_timeout(3000)

        # Step 5: Cover art page -- skip if possible, or upload placeholder
        next_btn = page.get_by_role("button", name="Next")
        if next_btn.is_visible(timeout=3000):
            # Next visible means cover art is optional or already set
            next_btn.click()
        else:
            log.info("Cover art required, looking for file input...")
            file_input = page.locator('input[type="file"]')
            if file_input.count() > 0:
                # Generate a minimal cover art on the fly
                cover_path = _generate_placeholder_cover(podcast_name)
                file_input.set_input_files(cover_path)
                page.wait_for_timeout(3000)
                next_btn = page.get_by_role("button", name="Next")
                next_btn.wait_for(state="visible", timeout=10_000)
                next_btn.click()

        page.wait_for_timeout(5000)

        # Extract podcast ID from URL
        current_url = page.url
        log.info("After creation URL: %s", current_url)

        podcast_id = ""
        if "/pod/show/" in current_url:
            parts = current_url.split("/pod/show/")[1].split("/")
            podcast_id = parts[0]

        if not podcast_id:
            page.screenshot(path=str(OUTPUT_DIR / "debug_spotify_podcast_created.png"))
            log.warning("Could not extract podcast ID from URL: %s", current_url)

        log.info("Created podcast with ID: %s", podcast_id)
        return podcast_id

    finally:
        ctx.close()


def _generate_placeholder_cover(title: str) -> str:
    """Generate a minimal 1400x1400 cover art image. Returns path to temp file."""
    from PIL import Image, ImageDraw, ImageFont
    import tempfile

    img = Image.new("RGB", (1400, 1400))
    draw = ImageDraw.Draw(img)

    for y in range(1400):
        for x in range(1400):
            r = int(10 + (y / 1400) * 20)
            g = int(30 + (1 - y / 1400) * 60 + (x / 1400) * 20)
            b = min(255, int(80 + (y / 1400) * 100 + (x / 1400) * 40))
            img.putpixel((x, y), (r, g, b))

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
    except OSError:
        font = ImageFont.load_default()

    words = title.split()
    y_pos = 500
    for word in words:
        draw.text((100, y_pos), word, fill=(255, 255, 255), font=font)
        y_pos += 100

    path = tempfile.mktemp(suffix=".jpg")
    img.save(path, "JPEG", quality=95)
    return path


def upload_episode(
    pw: Playwright,
    podcast_id: str,
    audio_path: Path,
    title: str,
    description: str,
    headless: bool = True,
) -> bool:
    """Upload an episode to a Spotify podcast. Returns True on success."""
    log.info("Uploading episode '%s' to podcast %s", title, podcast_id)
    ctx = get_spotify_context(pw, headless=headless)

    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        wizard_url = SPOTIFY_WIZARD_URL.format(podcast_id=podcast_id)
        log.info("Navigating to wizard: %s", wizard_url)
        page.goto(wizard_url, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(3000)

        # Step 1: Upload audio file
        log.info("Uploading audio file: %s", audio_path.name)
        file_input = page.locator('input[type="file"]')
        file_input.wait_for(state="attached", timeout=10_000)
        file_input.set_input_files(str(audio_path))
        log.info("File attached, waiting for upload to process...")

        # Step 2: Wait for title field (means upload processed and page transitioned)
        log.info("Waiting for episode form to load...")
        title_field = page.get_by_role("textbox", name="Title (required)")
        title_field.wait_for(state="visible", timeout=120_000)  # Large files take time
        page.wait_for_timeout(2000)

        # Step 3: Fill title
        log.info("Filling title: %s", title)
        title_field.fill(title)

        # Step 4: Fill description
        log.info("Filling description...")
        desc_field = page.get_by_role("textbox").filter(
            has_text="What else do you want your"
        )
        try:
            desc_field.wait_for(state="visible", timeout=5000)
            desc_field.fill(description)
        except Exception:
            # Fallback: try second textbox
            log.warning(
                "Could not find description field by placeholder, trying second textbox"
            )
            textboxes = page.get_by_role("textbox").all()
            if len(textboxes) > 1:
                textboxes[1].fill(description)

        # Step 5: Click Next
        log.info("Clicking Next...")
        page.get_by_role("button", name="Next").click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        # Step 6: Wait for Publish button to be enabled (large files take time to upload)
        log.info("Waiting for Publish button to be enabled...")
        publish_btn = page.get_by_role("button", name="Publish")
        publish_btn.wait_for(state="visible", timeout=300_000)  # 5 min for large files
        # Wait for it to become enabled (not just visible)
        page.wait_for_function(
            "() => { const btn = document.querySelector('button[type=\"submit\"]'); "
            "return btn && !btn.disabled; }",
            timeout=300_000,
        )
        log.info("Publish button enabled!")
        publish_btn.click()
        page.wait_for_timeout(2000)

        # Step 7: Select "Now"
        log.info("Selecting 'Now' option...")
        now_option = page.get_by_text("Now", exact=True)
        now_option.wait_for(state="visible", timeout=10_000)
        now_option.click()
        page.wait_for_timeout(1000)

        # Step 8: Confirm publish
        log.info("Confirming publish...")
        page.get_by_role("button", name="Publish").click()
        page.wait_for_timeout(5000)

        log.info("✅ Episode '%s' published successfully!", title)
        return True

    except Exception as e:
        log.error("Failed to upload episode: %s", e)
        page.screenshot(
            path=str(OUTPUT_DIR / f"debug_spotify_upload_error_{audio_path.stem}.png")
        )
        raise
    finally:
        ctx.close()
