"""Main pipeline orchestrator — PDF to published Spotify podcast episode."""

import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")  # noqa: E402

from pipeline.config import ensure_dirs, OUTPUT_DIR, PROGRESS_FILE, SPOTIFY_PODCAST_ID  # noqa: E402
from pipeline.sessions import login_notebooklm, login_spotify  # noqa: E402

log = logging.getLogger("pipeline")


def setup_logging(verbose: bool = False):
    """Configure logging with timestamps and levels."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")


def load_progress() -> dict:
    """Load progress file to resume interrupted runs."""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {}


def save_progress(progress: dict):
    """Save progress to disk."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def process_single_pdf(
    pdf_path: Path, podcast_id: str, progress: dict, headless: bool = True
):
    """Process a single PDF through the full pipeline."""
    from playwright.sync_api import sync_playwright
    from pipeline.notebooklm import create_podcast_from_pdf
    from pipeline.transcribe import process_audio
    from pipeline.spotify import upload_episode

    pdf_key = pdf_path.name
    pdf_progress = progress.get(pdf_key, {})

    episode_dir = OUTPUT_DIR / pdf_path.stem
    episode_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: NotebookLM — generate podcast audio
    audio_path = episode_dir / f"{pdf_path.stem}.wav"
    if pdf_progress.get("audio_downloaded") and audio_path.exists():
        log.info("⏭️  Audio already exists for %s, skipping NotebookLM", pdf_path.name)
    else:
        log.info("🎙️  Step 1/3: Generating podcast via NotebookLM for %s", pdf_path.name)
        with sync_playwright() as pw:
            audio_path = create_podcast_from_pdf(
                pw, pdf_path, episode_dir, headless=headless
            )
        pdf_progress["audio_downloaded"] = True
        pdf_progress["audio_path"] = str(audio_path)
        progress[pdf_key] = pdf_progress
        save_progress(progress)

    # Step 2: Transcribe + generate metadata
    if pdf_progress.get("metadata_generated"):
        log.info(
            "⏭️  Metadata already exists for %s, skipping transcription", pdf_path.name
        )
        metadata = pdf_progress["metadata"]
    else:
        log.info(
            "📝 Step 2/3: Transcribing and generating metadata for %s", pdf_path.name
        )
        metadata = process_audio(audio_path, pdf_path.stem)
        pdf_progress["metadata_generated"] = True
        pdf_progress["metadata"] = metadata
        progress[pdf_key] = pdf_progress
        save_progress(progress)

    # Step 3: Upload to Spotify
    if pdf_progress.get("spotify_uploaded"):
        log.info("⏭️  Already uploaded to Spotify: %s", pdf_path.name)
    else:
        log.info("🎵 Step 3/3: Uploading to Spotify for %s", pdf_path.name)
        with sync_playwright() as pw:
            upload_episode(
                pw,
                podcast_id,
                audio_path,
                title=metadata["title"],
                description=metadata["description"],
                headless=headless,
            )
        pdf_progress["spotify_uploaded"] = True
        progress[pdf_key] = pdf_progress
        save_progress(progress)

    log.info("✅ Completed full pipeline for: %s", pdf_path.name)


def run_pipeline(pdf_paths: list[Path], podcast_id: str, headless: bool = True):
    """Process multiple PDFs through the pipeline."""
    progress = load_progress()
    total = len(pdf_paths)

    for i, pdf_path in enumerate(pdf_paths, 1):
        log.info("=" * 60)
        log.info("Processing PDF %d/%d: %s", i, total, pdf_path.name)
        log.info("=" * 60)
        try:
            process_single_pdf(pdf_path, podcast_id, progress, headless=headless)
        except Exception as e:
            log.error("❌ Failed processing %s: %s", pdf_path.name, e, exc_info=True)
            log.info("Continuing to next PDF...")
            continue

    log.info("🏁 Pipeline complete. Processed %d/%d PDFs.", total, total)


def main():
    parser = argparse.ArgumentParser(description="PDF → Podcast Pipeline")
    sub = parser.add_subparsers(dest="command")

    # Login commands
    sub.add_parser("login-notebooklm", help="Log in to NotebookLM (one-time setup)")
    sub.add_parser("login-spotify", help="Log in to Spotify Creators (one-time setup)")
    sub.add_parser("login", help="Log in to both services")

    # Create podcast
    create = sub.add_parser("create-podcast", help="Create a new Spotify podcast")
    create.add_argument("name", help="Podcast name")

    # Run pipeline
    run = sub.add_parser("run", help="Run the full pipeline")
    run.add_argument(
        "pdfs", nargs="+", type=Path, help="PDF files or directory of PDFs"
    )
    run.add_argument("--podcast-id", help="Spotify podcast ID (overrides env var)")
    run.add_argument(
        "--headed", action="store_true", help="Run browsers in headed mode (visible)"
    )
    run.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    ensure_dirs()
    setup_logging(getattr(args, "verbose", False))

    if args.command == "login-notebooklm":
        login_notebooklm()
    elif args.command == "login-spotify":
        login_spotify()
    elif args.command == "login":
        login_notebooklm()
        login_spotify()
    elif args.command == "create-podcast":
        from playwright.sync_api import sync_playwright
        from pipeline.spotify import create_new_podcast

        with sync_playwright() as pw:
            pid = create_new_podcast(pw, args.name, headless=False)
            print(f"\nPodcast created! ID: {pid}")
            print(f"Set this in .env: SPOTIFY_PODCAST_ID={pid}")
    elif args.command == "run":
        podcast_id = getattr(args, "podcast_id", None) or SPOTIFY_PODCAST_ID
        if not podcast_id:
            log.error(
                "No podcast ID. Set SPOTIFY_PODCAST_ID in .env or use --podcast-id"
            )
            sys.exit(1)

        # Collect PDF files
        pdf_files = []
        for p in args.pdfs:
            if p.is_dir():
                pdf_files.extend(sorted(p.glob("*.pdf")))
            elif p.suffix.lower() == ".pdf":
                pdf_files.append(p)
            else:
                log.warning("Skipping non-PDF: %s", p)

        if not pdf_files:
            log.error("No PDF files found")
            sys.exit(1)

        log.info("Found %d PDF files to process", len(pdf_files))
        for f in pdf_files:
            log.info("  - %s", f.name)

        run_pipeline(pdf_files, podcast_id, headless=not args.headed)


if __name__ == "__main__":
    main()
