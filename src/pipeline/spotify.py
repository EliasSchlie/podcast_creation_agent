"""Spotify Creators automation — create podcasts and upload episodes."""

import logging
from pathlib import Path
from playwright.sync_api import Playwright

from pipeline.config import SPOTIFY_WIZARD_URL, SPOTIFY_CREATORS_URL
from pipeline.sessions import get_spotify_context

log = logging.getLogger(__name__)


def create_new_podcast(pw: Playwright, podcast_name: str, headless: bool = True) -> str:
    """
    Create a new podcast on Spotify Creators.
    Returns the podcast ID from the URL.
    """
    log.info("Creating new Spotify podcast: %s", podcast_name)
    ctx = get_spotify_context(pw, headless=headless)

    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(SPOTIFY_CREATORS_URL, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(3000)
        log.info("Current URL after login: %s", page.url)

        # Look for "New podcast" or create button
        create_selectors = [
            "text=New podcast",
            "text=Create a podcast",
            "text=Create podcast",
            "button:has-text('New')",
            "a:has-text('New podcast')",
            "[aria-label='Create new podcast']",
        ]
        clicked = False
        for sel in create_selectors:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3000):
                    log.info("Found create podcast button: %s", sel)
                    el.click()
                    page.wait_for_timeout(3000)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            # Try the "+" icon or similar
            page.screenshot(path="debug_spotify_home.png")
            log.warning("Could not find create podcast button. Screenshot saved.")

        # Fill in podcast name
        name_input = page.get_by_role("textbox").first
        name_input.wait_for(state="visible", timeout=10_000)
        name_input.fill(podcast_name)
        page.wait_for_timeout(1000)

        # Submit / save
        save_selectors = [
            "text=Save",
            "text=Create",
            "text=Next",
            "text=Continue",
            "button:has-text('Save')",
        ]
        for sel in save_selectors:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    el.click()
                    page.wait_for_timeout(3000)
                    break
            except Exception:
                continue

        # Extract podcast ID from URL
        current_url = page.url
        log.info("After creation URL: %s", current_url)

        # URL pattern: creators.spotify.com/pod/show/<podcast_id>/...
        podcast_id = ""
        if "/pod/show/" in current_url:
            parts = current_url.split("/pod/show/")[1].split("/")
            podcast_id = parts[0]

        if not podcast_id:
            page.screenshot(path="debug_spotify_podcast_created.png")
            log.warning("Could not extract podcast ID from URL: %s", current_url)

        log.info("Created podcast with ID: %s", podcast_id)
        return podcast_id

    finally:
        ctx.close()


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

        # Step 6: Wait for and click Publish
        log.info("Waiting for Publish button...")
        publish_btn = page.get_by_role("button", name="Publish")
        publish_btn.wait_for(state="visible", timeout=30_000)
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
        page.screenshot(path=f"debug_spotify_upload_error_{audio_path.stem}.png")
        raise
    finally:
        ctx.close()
