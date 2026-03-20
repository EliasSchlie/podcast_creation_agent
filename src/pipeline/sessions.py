"""Browser session management — login helpers and headless context creation."""

import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext, Playwright

from pipeline.config import (
    NOTEBOOKLM_PROFILE,
    SPOTIFY_PROFILE,
)

log = logging.getLogger(__name__)

BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-infobars",
]


def launch_persistent(
    pw: Playwright, profile_dir: Path, headless: bool = True
) -> BrowserContext:
    """Launch a Chromium persistent context with stealth settings."""
    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=headless,
        args=BROWSER_ARGS,
        viewport={"width": 1280, "height": 900},
        accept_downloads=True,
    )
    # Apply stealth to all pages
    try:
        from playwright_stealth import stealth_sync

        for page in context.pages:
            stealth_sync(page)
        context.on("page", lambda p: stealth_sync(p))
    except ImportError:
        log.warning("playwright-stealth not installed, skipping stealth")
    return context


def login_service(service_name: str, profile_dir: Path, url: str):
    """Open a headed browser for manual login. Run once per service."""
    log.info("Opening headed browser for %s login...", service_name)
    log.info("Please log in, then press Enter in the terminal.")
    with sync_playwright() as pw:
        ctx = launch_persistent(pw, profile_dir, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url)
        input(
            f"\n>>> Log in to {service_name}, then press ENTER here to save session... "
        )
        log.info("Session saved to %s", profile_dir)
        ctx.close()


def get_notebooklm_context(pw: Playwright, headless: bool = True) -> BrowserContext:
    """Get a headless NotebookLM browser context with saved session."""
    return launch_persistent(pw, NOTEBOOKLM_PROFILE, headless=headless)


def get_spotify_context(pw: Playwright, headless: bool = True) -> BrowserContext:
    """Get a headless Spotify browser context with saved session."""
    return launch_persistent(pw, SPOTIFY_PROFILE, headless=headless)
