# Podcast Creation Agent

Automated pipeline that turns PDFs into published Spotify podcast episodes.

## Pipeline

1. **NotebookLM** — Upload PDF, generate AI podcast (Deep Dive, Long format)
2. **Gemini API** — Transcribe audio, generate episode title and description
3. **Spotify** — Upload episode and publish immediately

## Setup

```bash
# Install dependencies
uv sync
uv run playwright install chromium

# Configure
cp .env.example .env  # Add your GEMINI_API_KEY and SPOTIFY_PODCAST_ID

# One-time login (opens browser for manual login, saves persistent session)
python login.py notebooklm   # Google account
python login.py spotify      # Spotify Creators account
```

## Usage

```bash
# Process a single PDF
PYTHONPATH=src uv run python -m pipeline.main run chapter.pdf --podcast-id YOUR_ID

# Process a folder of PDFs
PYTHONPATH=src uv run python -m pipeline.main run /path/to/folder/ --podcast-id YOUR_ID

# Debug mode (visible browser)
PYTHONPATH=src uv run python -m pipeline.main run chapter.pdf --podcast-id YOUR_ID --headed -v
```

The pipeline tracks progress in `output/progress.json` — interrupted runs resume where they left off.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Google account with NotebookLM access
- Spotify Creators account
- Gemini API key
