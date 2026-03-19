"""Gemini-based transcription and metadata generation for podcast episodes."""

import logging
from pathlib import Path
from google import genai

from pipeline.config import GEMINI_API_KEY

log = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    """Get a Gemini API client."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set. Add it to .env or environment.")
    return genai.Client(api_key=GEMINI_API_KEY)


def transcribe_audio(audio_path: Path) -> str:
    """Transcribe podcast audio using Gemini."""
    log.info("Transcribing audio: %s", audio_path.name)
    client = _get_client()

    # Upload the audio file
    log.info("Uploading audio to Gemini...")
    uploaded = client.files.upload(file=audio_path)
    log.info("Upload complete, file URI: %s", uploaded.uri)

    # Transcribe
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            uploaded,
            "Transcribe this podcast audio. Include speaker labels (Host 1, Host 2, etc). "
            "Output the full transcript, nothing else.",
        ],
    )
    transcript = response.text
    log.info("Transcription complete (%d characters)", len(transcript))
    return transcript


def generate_metadata(transcript: str, source_name: str) -> dict:
    """Generate episode title and description from transcript and source info."""
    log.info("Generating episode metadata for source: %s", source_name)
    client = _get_client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            f"This is a podcast episode transcript generated from: {source_name}\n\n"
            f"Transcript:\n{transcript[:10000]}\n\n"  # Limit to avoid token issues
            "Generate a podcast episode title and description.\n"
            "The title MUST start with the chapter number prefix from the source name "
            "(e.g. 'Chapter 1: ...' or 'Chapter 12: ...'). After the prefix, add an "
            "engaging subtitle that reflects the main topics discussed.\n"
            "The description should be 2-3 sentences summarizing the key points.\n\n"
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


def process_audio(audio_path: Path, source_name: str) -> dict:
    """Full transcription + metadata pipeline. Returns dict with title, description, transcript."""
    transcript = transcribe_audio(audio_path)
    metadata = generate_metadata(transcript, source_name)

    # Save transcript to file
    transcript_path = audio_path.with_suffix(".transcript.txt")
    transcript_path.write_text(transcript, encoding="utf-8")
    log.info("Transcript saved to: %s", transcript_path)

    return {
        "title": metadata["title"],
        "description": metadata["description"],
        "transcript": transcript,
        "transcript_path": str(transcript_path),
    }
