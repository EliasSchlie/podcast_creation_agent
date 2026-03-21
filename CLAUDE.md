# Podcast Creation Agent

Automated pipeline: PDF -> NotebookLM podcast -> Gemini transcription -> Spotify upload.

## Quick Start

```bash
cd ~/projects/podcast_creation_agent
uv sync && uv run playwright install chromium

# One-time login (headed browsers, log in manually, press Enter)
podcast-pipeline login

# Run pipeline
podcast-pipeline run /path/to/pdfs --duration Default

# Multi-account (bypass per-account rate limits)
podcast-pipeline run /path/to/pdfs --notebooklm-profile sessions/notebooklm-profile-2
```

## Browser Profiles

- Stored in `sessions/` at **repo root** (gitignored) -- never in worktrees
- When running from a worktree, always use `--notebooklm-profile` pointing to the root `sessions/`
- `sessions/notebooklm-profile` -- default NotebookLM profile
- `sessions/spotify-profile` -- Spotify Creators profile
- Extra profiles: `sessions/notebooklm-profile-N` for multi-account support
- Profiles persist Google/Spotify login cookies across runs
- **Must re-login** if profile is deleted or session expires

## Rate Limits (NotebookLM)

- Per-account, not per-browser -- stealth/fresh profiles don't help
- `RateLimitError` stops pipeline immediately (no point retrying same account)

## Gotchas

- **Browser binary**: Pipeline auto-detects agent-browser's Chrome for Testing (`~/.agent-browser/browsers/`) and uses it instead of Playwright's bundled Chromium. This ensures profile compatibility between agent-browser and the pipeline, and avoids Google's "insecure browser" warning during login. If agent-browser isn't installed, falls back to Playwright's Chromium.
- **Chrome lock files**: Clean `sessions/*/SingletonLock,Socket,Cookie` when switching between agent-browser and Playwright
- **Spotify episode ordering**: No manual reorder -- episodes sort by publish date only
- **Gemini file cleanup**: `client.files.delete(name=uploaded.name)` -- keyword arg required
- **playwright-stealth v2 API**: `Stealth().apply_stealth_sync(page)` (not `stealth_sync(page)`)
- **Spotify popovers**: Options menu items (Delete/Download) aren't in accessibility snapshots -- use JS `querySelector` + `.click()` workaround
