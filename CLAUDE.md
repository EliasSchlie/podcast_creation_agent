# Podcast Creation Agent

Automated pipeline: PDF → NotebookLM podcast → Gemini transcription → Spotify upload.

## Quick Start

```bash
cd ~/projects/podcast_creation_agent
uv sync && uv run playwright install chromium

# One-time: log in to services (headed browsers)
python login.py notebooklm
python login.py spotify

# Run pipeline
PYTHONPATH=src uv run python -m pipeline.main run /path/to/pdfs --podcast-id <ID>
```

## Architecture

```
src/pipeline/
├── main.py          # CLI + orchestrator (run, login, create-podcast)
├── config.py        # Paths, env vars, URLs
├── sessions.py      # Persistent browser profiles + stealth
├── notebooklm.py    # NotebookLM automation (create notebook, upload, generate, download)
├── transcribe.py    # Gemini API (transcribe audio + generate title/description)
└── spotify.py       # Spotify Creators (upload episode + publish)
```

## Key Details

- **Browser profiles** in `sessions/` (gitignored) — persist Google/Spotify logins
- **Progress tracking** in `output/progress.json` — resume interrupted runs
- **Headless by default** — use `--headed` flag for debugging
- `.env` holds `GEMINI_API_KEY` and `SPOTIFY_PODCAST_ID`

## NotebookLM UI Flow (verified March 2026)

1. Home → click "Create new" (force=True needed, button intercepts text click)
2. Source dialog auto-opens → "Upload files" → file chooser → set PDF
3. Wait for dialog to close (up to 2min for large PDFs)
4. Click "Customize Audio Overview" (aria-label, in Studio panel)
5. Dialog: format=Deep Dive (default), Length=Long, click "Generate"
6. Poll for completion: check "Generating" in body text + Play button count
7. Download: click `[aria-label='More']` → "Download" menu item

## Spotify UI Flow (verified March 2026)

- Episode wizard: `creators.spotify.com/pod/show/{id}/episode/wizard`
- Upload → file input → wait for title field → fill title/description → Next → Publish → Now → Publish
- Cookie consent must be accepted or API calls fail silently
- New podcast creation URL: `creators.spotify.com/pod/show/{id}/podcast/new`

## Env Vars

- `GEMINI_API_KEY` — Google Gemini API key for transcription
- `SPOTIFY_PODCAST_ID` — target Spotify podcast ID
