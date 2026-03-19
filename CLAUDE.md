# Podcast Creation Agent

Automated pipeline: PDF → NotebookLM podcast → Gemini transcription → Spotify upload.

## Quick Start

```bash
cd ~/projects/podcast_creation_agent
uv sync && uv run playwright install chromium

# One-time login (headed browsers)
python login.py notebooklm
python login.py spotify

# Run pipeline
PYTHONPATH=src GEMINI_API_KEY=... uv run python -m pipeline.main run /path/to/pdfs --podcast-id <ID>
```

## Architecture

- `src/pipeline/config.py` — paths, env vars, URLs
- `src/pipeline/sessions.py` — Playwright persistent browser profiles (headless/headed)
- `src/pipeline/notebooklm.py` — NotebookLM automation (create notebook, upload PDF, generate audio, download)
- `src/pipeline/transcribe.py` — Gemini 2.5 Flash transcription + metadata generation
- `src/pipeline/spotify.py` — Spotify Creators episode upload + podcast creation
- `src/pipeline/main.py` — CLI orchestrator with progress tracking
- `login.py` — Interactive login helper (3-min headed browser)

## Key Details

- **Browser profiles** stored in `sessions/` (gitignored). Login persists across headless runs.
- **NotebookLM UI** (verified March 2026): `+ Create new` → upload dialog → `Customize Audio Overview` → set Long → Generate → More menu → Download.
- **NotebookLM quirks**: `force=True` needed for notebook card clicks (button intercepts pointer events). `domcontentloaded` not `networkidle` for page loads.
- **Spotify podcast creation**: Avatar menu (top-right "S") → "Add a new show" → "Create a new show" (force click) → fill form (name, desc, creator, category select, language select) → Next → upload cover → Next → done.
- **Spotify episode wizard URL**: `creators.spotify.com/pod/show/{id}/episode/wizard`
- **Progress file**: `output/progress.json` — tracks which PDFs completed which stages. Pipeline resumes from last completed step.
- **Gemini model**: `gemini-2.5-flash` (2.0 models deprecated for new users as of March 2026)
- **Cover image generation**: Imagen 4 (`imagen-4.0-generate-001`)

## Environment Variables (.env)

```
GEMINI_API_KEY=...
SPOTIFY_PODCAST_ID=...
```

## Accounts

- NotebookLM: Google account (elias.fake31@gmail.com)
- Spotify Creators: Super Scraper (jtagyt5521@gmail.com)
- Podcast: "Positive Psychology Explored" (ID: 4TMhEZZTVP3K29m2OtgUjI)

## Git

Worktree workflow — develop in `.wt/`, merge via PR, don't commit to main directly.
