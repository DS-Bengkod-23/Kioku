import os
import json
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

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    try:
        client = genai.Client(api_key=api_key)
        audio_file = client.files.upload(file=audio_path)
        prompt = (
            "Transcribe this audio recording accurately. "
            "Return a JSON array of segments. Each segment must have:\n"
            '- "start": start time in seconds (float)\n'
            '- "end": end time in seconds (float)\n'
            '- "text": the spoken text for that segment\n'
            '- "language": detected language code (e.g. "id", "en")\n\n'
            "Return ONLY a valid JSON array, no markdown, no explanation."
        )

        response = client.models.generate_content(
            model=model_name,
            contents=[audio_file, prompt],
            config={"response_mime_type": "application/json"},
        )
        raw = response.text.strip()
        segments_data = json.loads(raw)

    except json.JSONDecodeError as e:
        raise ValueError(f"Output Gemini bukan JSON valid: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Gemini STT gagal: {e}") from e

    segments = [
        TranscriptSegment(
            speaker="SPEAKER_00",
            start=float(seg.get("start", 0.0)),
            end=float(seg.get("end", 0.0)),
            text=seg.get("text", "").strip(),
        )
        for seg in segments_data
        if seg.get("text", "").strip()
    ]

    duration = segments[-1].end if segments else 0.0
    language = segments_data[0].get("language", "id") if segments_data else "id"

    return TranscriptResult(
        segments=segments,
        language=language,
        duration=duration,
    )
