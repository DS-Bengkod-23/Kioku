import os
from google import genai
try:
    from .schemas import TranscriptResult, TranscriptSegment
except ImportError:
    from schemas import TranscriptResult, TranscriptSegment


def transcribe(audio_path: str) -> TranscriptResult:
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"File audio tidak ditemukan: {audio_path}")

    supported = (".mp3", ".mp4", ".wav", ".m4a", ".flac", ".ogg", ".webm")
    if not audio_path.lower().endswith(supported):
        raise ValueError(f"Format file tidak didukung: {audio_path}")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY tidak ditemukan di environment")

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    try:
        client = genai.Client(api_key=api_key)
        audio_file = client.files.upload(file=audio_path)

        prompt = (
            "Transcribe this audio recording accurately and completely. "
            "Return ONLY the transcribed text, nothing else. "
            "No timestamps, no speaker labels, no explanation."
        )

        response = client.models.generate_content(
            model=model_name,
            contents=[audio_file, prompt],
        )
        full_text = response.text.strip()

    except Exception as e:
        raise RuntimeError(f"Gemini STT gagal: {e}") from e

    segments = [
        TranscriptSegment(
            speaker="SPEAKER_00",
            start=0.0,
            end=0.0,
            text=full_text,
        )
    ]

    return TranscriptResult(
        segments=segments,
        language="id",
        duration=0.0,
    )
