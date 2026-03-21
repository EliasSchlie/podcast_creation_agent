"""Gemini-based transcription and metadata generation for podcast episodes."""

import logging
from pathlib import Path
from google import genai

from pipeline.config import GEMINI_API_KEY

log = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Get a cached Gemini API client (lazy singleton)."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set. Add it to .env or environment.")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def transcribe_audio(audio_path: Path) -> str:
    """Transcribe podcast audio using Gemini."""
    log.info("Transcribing audio: %s", audio_path.name)
    client = _get_client()

    # Upload the audio file
    log.info("Uploading audio to Gemini...")
    uploaded = client.files.upload(file=audio_path)
    log.info("Upload complete, file URI: %s", uploaded.uri)

    # Transcribe
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                uploaded,
                "Transcribe this podcast audio. Include speaker labels (Host 1, Host 2, etc). "
                "Output the full transcript, nothing else.",
            ],
        )
        transcript = response.text
        log.info("Transcription complete (%d characters)", len(transcript))
        return transcript
    finally:
        try:
            client.files.delete(name=uploaded.name)
            log.info("Deleted uploaded file: %s", uploaded.name)
        except Exception as e:
            log.warning("Failed to delete uploaded file %s: %s", uploaded.name, e)


def generate_metadata(
    transcript: str, source_name: str, source_info: dict | None = None
) -> dict:
    """Generate episode title and description from transcript and source info.

    source_info (optional): dict with keys like "title", "authors", "url" to avoid
    hallucinating paper metadata. Loaded from <pdf>.meta.json sidecar if present.
    """
    log.info("Generating episode metadata for source: %s", source_name)
    client = _get_client()

    # Build source context from real metadata if available
    if source_info:
        source_context = (
            f'Source: "{source_info.get("title", source_name)}"\n'
            f"Authors: {source_info.get('authors', 'Unknown')}\n"
            f"URL: {source_info.get('url', 'N/A')}\n"
        )
        desc_instruction = (
            "The description MUST start with exactly this attribution line:\n"
            f'\'Based on "{source_info.get("title", source_name)}" '
            f"by {source_info.get('authors', 'the authors')}. "
            f"{source_info.get('url', '')}'\n"
            "Then add 2-3 sentences summarizing the key points discussed."
        )
    else:
        source_context = f"Source filename: {source_name}\n"
        desc_instruction = "The description should summarize the key points discussed in 2-3 sentences."

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[
            f"This is a podcast episode transcript.\n{source_context}\n"
            f"Transcript:\n{transcript[:10000]}\n\n"  # Limit to avoid token issues
            "Generate a podcast episode title and description.\n"
            "The title should be engaging and reflect the main topics discussed. "
            "Do NOT add chapter numbers or prefixes. Just a good, descriptive title.\n"
            f"{desc_instruction}\n\n"
            "Respond in exactly this format:\n"
            "TITLE: <title>\n"
            "DESCRIPTION: <description>",
        ],
    )

    text = response.text.strip()
    title = ""
    description = ""

    for line in text.split("\n"):
        if line.startswith("TITLE:"):
            title = line[6:].strip()
        elif line.startswith("DESCRIPTION:"):
            description = line[12:].strip()

    if not title:
        title = f"Podcast: {source_name}"
    if not description:
        description = f"An AI-generated podcast discussion about {source_name}."

    log.info("Generated title: %s", title)
    log.info("Generated description: %s", description[:100])
    return {"title": title, "description": description}


def _load_source_info(source_name: str, pdf_dir: Path | None = None) -> dict | None:
    """Load source metadata from a <name>.meta.json sidecar file if it exists.

    Expected format: {"title": "...", "authors": "...", "url": "..."}
    """
    if pdf_dir is None:
        return None
    meta_path = pdf_dir / f"{source_name}.meta.json"
    if meta_path.exists():
        import json

        info = json.loads(meta_path.read_text())
        log.info("Loaded source metadata from %s", meta_path.name)
        return info
    return None


def process_audio(
    audio_path: Path, source_name: str, pdf_dir: Path | None = None
) -> dict:
    """Full transcription + metadata pipeline. Returns dict with title, description, transcript."""
    transcript = transcribe_audio(audio_path)
    source_info = _load_source_info(source_name, pdf_dir)
    metadata = generate_metadata(transcript, source_name, source_info=source_info)

    # Save transcript to file
    transcript_path = audio_path.with_suffix(".transcript.txt")
    transcript_path.write_text(transcript, encoding="utf-8")
    log.info("Transcript saved to: %s", transcript_path)

    return {
        "title": metadata["title"],
        "description": metadata["description"],
        "transcript_path": str(transcript_path),
    }
