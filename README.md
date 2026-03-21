# Podcast Creation Agent

Automated pipeline that turns PDFs into published Spotify podcast episodes using Google's NotebookLM, Gemini, and Spotify Creators.

```
PDF --> NotebookLM --> Gemini --> Spotify
 |         |             |          |
 |    Upload PDF,    Transcribe   Upload &
 |    generate AI    audio, gen   publish
 |    podcast        metadata     episode
```

## How it works

1. **NotebookLM** -- Uploads your PDF, creates a notebook, and generates an AI podcast conversation (two hosts discussing the content)
2. **Gemini API** -- Transcribes the generated audio and creates an episode title + description
3. **Spotify Creators** -- Uploads the episode and publishes it to your podcast

The entire pipeline runs headless after initial login setup. It tracks progress per-PDF, so interrupted runs resume where they left off.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Google account with [NotebookLM](https://notebooklm.google.com) access
- [Spotify Creators](https://creators.spotify.com) account with a podcast
- [Gemini API key](https://aistudio.google.com/apikey)

## Setup

```bash
git clone https://github.com/EliasSchlie/podcast_creation_agent.git
cd podcast_creation_agent

# Install dependencies
uv sync
uv run playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and SPOTIFY_PODCAST_ID
```

### One-time login

The pipeline uses persistent browser profiles to stay logged in. Run these once to save your sessions:

```bash
# Log in to Google (for NotebookLM)
podcast-pipeline login-notebooklm

# Log in to Spotify Creators
podcast-pipeline login-spotify

# Or both at once
podcast-pipeline login
```

A headed browser opens for each service. Log in manually, then press Enter in the terminal to save the session.

## Usage

```bash
# Process a single PDF
podcast-pipeline run chapter.pdf

# Process a directory of PDFs
podcast-pipeline run ./pdfs/

# Visible browser + verbose logging (for debugging)
podcast-pipeline run chapter.pdf --headed -v

# Override podcast ID
podcast-pipeline run chapter.pdf --podcast-id YOUR_PODCAST_ID

# Choose episode duration: Short, Default, or Long
podcast-pipeline run chapter.pdf --duration Long
```

### Multi-account support

NotebookLM has a daily generation limit (~8 per account). To work around this, use multiple Google accounts with separate browser profiles:

```bash
# First login to a second account
podcast-pipeline login-notebooklm  # log in with a different Google account
# Then move the profile:
mv sessions/notebooklm-profile sessions/notebooklm-profile-2

# Re-login with your primary account
podcast-pipeline login-notebooklm

# Use the alternate profile
podcast-pipeline run chapter.pdf --notebooklm-profile sessions/notebooklm-profile-2
```

### Create a new podcast

```bash
podcast-pipeline create-podcast "My Podcast Name"
# Prints the podcast ID to set in .env
```

## Project structure

```
src/pipeline/
  main.py          CLI + orchestrator
  config.py        Paths, env vars, URLs
  sessions.py      Persistent browser profiles + stealth
  notebooklm.py    NotebookLM automation
  transcribe.py    Gemini transcription + metadata generation
  spotify.py       Spotify Creators upload + publish
```

## Known limitations

- **NotebookLM rate limit**: ~8 audio generations per day per Google account. The pipeline detects this and stops early rather than wasting time retrying.
- **NotebookLM sessions**: Browser sessions go stale after ~2.5 hours of continuous use. Restart the pipeline if this happens.
- **Spotify episode ordering**: Episodes are sorted by publish date only (no manual reorder in Spotify Creators).
- **Browser automation**: NotebookLM and Spotify UIs change over time. Selectors may need updating if the services update their frontend.

## License

[MIT](LICENSE)
