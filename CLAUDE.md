# Podcast Creation Agent

Automated pipeline: PDF -> NotebookLM podcast -> Gemini transcription -> Spotify upload.

## Quick Start

```bash
cd ~/projects/podcast_creation_agent
uv sync && uv run playwright install chromium

# Configure (copy .env.example, add your keys)
cp .env.example .env
# Required: GEMINI_API_KEY, SPOTIFY_PODCAST_ID

# One-time login (headed browsers, log in manually, press Enter)
podcast-pipeline login

# Verify sessions before running (catches expired logins early)
podcast-pipeline check-session

# Run pipeline
podcast-pipeline run /path/to/pdfs --duration Default

# Target a specific podcast (overrides SPOTIFY_PODCAST_ID in .env)
podcast-pipeline run paper.pdf --podcast-id <id>

# Multi-account (bypass per-account rate limits)
podcast-pipeline run /path/to/pdfs --notebooklm-profile sessions/notebooklm-profile-2
```

## Browser Profiles

- Stored in `sessions/` at **repo root** (gitignored) -- never in worktrees
- `config.py` auto-resolves `SESSIONS_DIR` to git root via `git rev-parse --git-common-dir` -- works from worktrees automatically
- `sessions/notebooklm-profile` -- default NotebookLM profile
- `sessions/spotify-profile` -- Spotify Creators profile
- Extra profiles: `sessions/notebooklm-profile-N` for multi-account support
- Profiles persist Google/Spotify login cookies across runs
- **Must re-login** if profile is deleted or session expires
- **Session refresh shortcut**: If `check-session` reports Spotify expired, try opening `creators.spotify.com` via agent-browser with `--profile sessions/spotify-profile` first -- Google cookies may still be valid and will auto-login
- **Creating new profiles**: Always use `podcast-pipeline login-*` (not agent-browser). It uses the correct Chrome binary with stealth, avoiding Google's "insecure browser" warning. For extra NotebookLM accounts: rename the default profile, run login again, then rename back:
  ```
  mv sessions/notebooklm-profile sessions/notebooklm-profile-2
  podcast-pipeline login-notebooklm   # log in with different account
  mv sessions/notebooklm-profile sessions/notebooklm-profile-3
  mv sessions/notebooklm-profile-2 sessions/notebooklm-profile  # restore default
  ```
- `sessions/PROFILES.md` maps each profile to its Google/Spotify account

## Rate Limits

### NotebookLM
- Per-account, not per-browser -- stealth/fresh profiles don't help
- `RateLimitError` stops pipeline immediately (no point retrying same account)
- **Audio generation takes 5-30+ minutes per episode** -- don't assume it's stuck

### Gemini
- Free tier: 20 requests/day per model -- running parallel pipelines burns through this fast
- Paid key has no practical limit for this use case
- Rate limit error is `429 RESOURCE_EXHAUSTED` -- the pipeline doesn't auto-retry, re-run to resume

## Episode Metadata

Place a `<pdf-name>.meta.json` sidecar next to each PDF to provide exact paper metadata:
```json
{"title": "Paper Title", "authors": "Author et al. (2024)", "url": "https://arxiv.org/abs/..."}
```
Without it, Gemini infers metadata from the transcript (may hallucinate names/authors).

## Docs

- [Cover art generation](docs/cover-art.md) -- Pillow script for podcast cover images

## Gotchas

- **Browser binary**: Pipeline auto-detects agent-browser's Chrome for Testing (`~/.agent-browser/browsers/`) and uses it instead of Playwright's bundled Chromium. This ensures profile compatibility between agent-browser and the pipeline, and avoids Google's "insecure browser" warning during login. If agent-browser isn't installed, falls back to Playwright's Chromium.
- **Chrome lock files**: Clean `sessions/*/SingletonLock,Socket,Cookie` when switching between agent-browser and Playwright. Use `unlink` or `rm` without `-f` (`rm -f` blocked in this env)
- **Spotify Creators delete flow**: Settings -> scroll to bottom -> Management -> Delete podcast. For episodes: options menu -> Delete episode (needs JS click, not in a11y tree)
- **Progress tracking caveat**: `spotify_uploaded: true` in progress.json doesn't guarantee the episode appeared on Spotify -- verify manually if in doubt
- **Spotify episode ordering**: No manual reorder -- episodes sort by publish date only
- **Parallel pipelines**: Multiple pipelines can run with different `--notebooklm-profile` flags, but they share `progress.json` and `spotify-profile` -- Spotify upload conflicts possible. Serialize uploads or run sequentially for reliability.
- **Gemini file cleanup**: `client.files.delete(name=uploaded.name)` -- keyword arg required
- **playwright-stealth v2 API**: `Stealth().apply_stealth_sync(page)` (not `stealth_sync(page)`)
- **Spotify popovers**: Options menu items (Delete/Download) aren't in accessibility snapshots -- use JS `querySelector` + `.click()` workaround
