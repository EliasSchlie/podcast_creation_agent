"""Browser session management — login helpers and headless context creation."""

import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext, Playwright

from pipeline.config import (
    NOTEBOOKLM_PROFILE,
    SPOTIFY_PROFILE,
    NOTEBOOKLM_URL,
    SPOTIFY_CREATORS_URL,
)

log = logging.getLogger(__name__)

BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-infobars",
]


def _launch_persistent(
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


def login_notebooklm():
    """Open a headed browser for manual Google/NotebookLM login. Run once."""
    log.info("Opening headed browser for NotebookLM login...")
    log.info("Please log in to your Google account, then press Enter in the terminal.")
    with sync_playwright() as pw:
        ctx = _launch_persistent(pw, NOTEBOOKLM_PROFILE, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(NOTEBOOKLM_URL)
        input("\n>>> Log in to NotebookLM, then press ENTER here to save session... ")
        log.info("Session saved to %s", NOTEBOOKLM_PROFILE)
        ctx.close()


def login_spotify():
    """Open a headed browser for manual Spotify Creators login. Run once."""
    log.info("Opening headed browser for Spotify Creators login...")
    log.info("Please log in, then press Enter in the terminal.")
    with sync_playwright() as pw:
        ctx = _launch_persistent(pw, SPOTIFY_PROFILE, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(SPOTIFY_CREATORS_URL)
        input(
            "\n>>> Log in to Spotify Creators, then press ENTER here to save session... "
        )
        log.info("Session saved to %s", SPOTIFY_PROFILE)
        ctx.close()


def get_notebooklm_context(pw: Playwright, headless: bool = True) -> BrowserContext:
    """Get a headless NotebookLM browser context with saved session."""
    return _launch_persistent(pw, NOTEBOOKLM_PROFILE, headless=headless)


def get_spotify_context(pw: Playwright, headless: bool = True) -> BrowserContext:
    """Get a headless Spotify browser context with saved session."""
    return _launch_persistent(pw, SPOTIFY_PROFILE, headless=headless)
