#!/usr/bin/env python3
"""Interactive login script — opens headed browser for manual login.

Usage:
    python login.py notebooklm   — log in to Google/NotebookLM
    python login.py spotify      — log in to Spotify Creators
    python login.py both         — log in to both (sequentially)

The browser will stay open for 3 minutes. Log in, then close it (or wait).
Session is saved in the persistent profile automatically.
"""

import sys
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pipeline.config import (
    ensure_dirs,
    NOTEBOOKLM_PROFILE,
    SPOTIFY_PROFILE,
    NOTEBOOKLM_URL,
    SPOTIFY_CREATORS_URL,
)
from pipeline.sessions import launch_persistent

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

LOGIN_TIMEOUT = 180  # 3 minutes


def do_login(pw, profile_dir, url, name):
    log.info(
        "Opening %s login browser (you have %ds to log in)...", name, LOGIN_TIMEOUT
    )
    ctx = launch_persistent(pw, profile_dir, headless=False)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(url)

    # Wait — either the user closes the browser or we timeout
    start = time.time()
    while time.time() - start < LOGIN_TIMEOUT:
        try:
            # Check if context is still alive
            _ = page.url
            time.sleep(2)
        except Exception:
            log.info("Browser closed by user")
            break
    else:
        log.info("Timeout reached, closing browser")

    try:
        ctx.close()
    except Exception:
        pass

    log.info("✅ %s session saved to %s", name, profile_dir)


def main():
    from playwright.sync_api import sync_playwright

    if len(sys.argv) < 2 or sys.argv[1] not in ("notebooklm", "spotify", "both"):
        print(__doc__)
        sys.exit(1)

    ensure_dirs()
    target = sys.argv[1]

    with sync_playwright() as pw:
        if target in ("notebooklm", "both"):
            do_login(pw, NOTEBOOKLM_PROFILE, NOTEBOOKLM_URL, "NotebookLM")
        if target in ("spotify", "both"):
            do_login(pw, SPOTIFY_PROFILE, SPOTIFY_CREATORS_URL, "Spotify")

    log.info("🏁 Login complete!")


if __name__ == "__main__":
    main()
