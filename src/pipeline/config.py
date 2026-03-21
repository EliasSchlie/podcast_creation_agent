"""Configuration and paths for the podcast pipeline."""

import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv


def _git_root() -> Path:
    """Get the real git root, not the worktree root.

    Browser profiles must live in the main repo so they survive worktree deletion.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        if result.returncode == 0:
            # --git-common-dir returns <root>/.git, go up one level
            return Path(result.stdout.strip()).parent
    except FileNotFoundError:
        pass
    return Path(__file__).parent.parent.parent


# Directories
PROJECT_ROOT = Path(__file__).parent.parent.parent
GIT_ROOT = _git_root()

load_dotenv(PROJECT_ROOT / ".env")
SESSIONS_DIR = GIT_ROOT / "sessions"
OUTPUT_DIR = PROJECT_ROOT / "output"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"

# Browser profile dirs (persistent login state)
NOTEBOOKLM_PROFILE = SESSIONS_DIR / "notebooklm-profile"
SPOTIFY_PROFILE = SESSIONS_DIR / "spotify-profile"

# API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Spotify
SPOTIFY_PODCAST_ID = os.environ.get("SPOTIFY_PODCAST_ID", "")

# URLs
NOTEBOOKLM_URL = "https://notebooklm.google.com"
SPOTIFY_WIZARD_URL = "https://creators.spotify.com/pod/show/{podcast_id}/episode/wizard"
SPOTIFY_CREATORS_URL = "https://creators.spotify.com"


def ensure_dirs():
    """Create necessary directories."""
    SESSIONS_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    NOTEBOOKLM_PROFILE.mkdir(parents=True, exist_ok=True)
    SPOTIFY_PROFILE.mkdir(parents=True, exist_ok=True)
