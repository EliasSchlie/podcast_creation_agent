"""Browser session management — login helpers and headless context creation."""

import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext, Playwright

from pipeline.config import SPOTIFY_PROFILE

log = logging.getLogger(__name__)

# Minimal args — avoid bot-detection flags
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
]

# agent-browser's Chrome for Testing — newer, passes Google's security checks.
# Playwright's bundled Chromium gets flagged as "insecure browser" by Google login.
_AGENT_BROWSER_CHROME = Path.home() / ".agent-browser" / "browsers"


def _find_chrome_executable() -> str | None:
    """Find agent-browser's Chrome for Testing binary (newest version)."""
    if not _AGENT_BROWSER_CHROME.exists():
        return None
    chrome_dirs = sorted(_AGENT_BROWSER_CHROME.glob("chrome-*"), reverse=True)
    for d in chrome_dirs:
        # macOS
        candidate = (
            d
            / "Google Chrome for Testing.app"
            / "Contents"
            / "MacOS"
            / "Google Chrome for Testing"
        )
        if candidate.exists():
            return str(candidate)
        # Linux
        candidate = d / "chrome"
        if candidate.exists():
            return str(candidate)
    return None


def launch_persistent(
    pw: Playwright, profile_dir: Path, headless: bool = True
) -> BrowserContext:
    """Launch a Chromium persistent context with stealth settings.

    Uses agent-browser's Chrome for Testing if available (passes Google login checks).
    Falls back to Playwright's bundled Chromium.
    """
    chrome_exe = _find_chrome_executable()
    if chrome_exe:
        log.info(
            "Using agent-browser's Chrome: %s", chrome_exe.split("/browsers/")[1][:30]
        )

    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=headless,
        args=BROWSER_ARGS,
        viewport={"width": 1280, "height": 900},
        accept_downloads=True,
        executable_path=chrome_exe,
    )
    # Apply stealth to evade bot detection
    try:
        from playwright_stealth import Stealth

        stealth = Stealth()
        for page in context.pages:
            stealth.apply_stealth_sync(page)
        context.on("page", lambda p: stealth.apply_stealth_sync(p))
        log.info("Stealth applied successfully")
    except ImportError as e:
        log.warning("playwright-stealth not installed, skipping: %s", e)
    except Exception as e:
        log.error("Stealth failed unexpectedly: %s", e, exc_info=True)
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


def get_spotify_context(pw: Playwright, headless: bool = True) -> BrowserContext:
    """Get a headless Spotify browser context with saved session."""
    return launch_persistent(pw, SPOTIFY_PROFILE, headless=headless)


def check_session(pw: Playwright, service: str, profile_dir: Path, url: str) -> bool:
    """Check if a browser session is still valid (not redirected to login).

    Returns True if logged in, False if session expired.
    """
    log.info("Checking %s session (%s)...", service, profile_dir.name)
    ctx = launch_persistent(pw, profile_dir, headless=True)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(3000)
        final_url = page.url

        # Google services redirect to accounts.google.com on expired session
        if "accounts.google.com" in final_url:
            log.warning("❌ %s session expired (redirected to Google login)", service)
            return False

        # Spotify redirects to login page or shows Log in button
        if service == "Spotify":
            login_btn = page.locator("text=Log in").first
            try:
                if login_btn.is_visible(timeout=2000):
                    log.warning("❌ %s session expired (login page shown)", service)
                    return False
            except Exception:
                pass

        log.info("✅ %s session is valid (URL: %s)", service, final_url[:80])
        return True
    except Exception as e:
        log.error("❌ %s session check failed: %s", service, e)
        return False
    finally:
        ctx.close()
