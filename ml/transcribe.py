import os
import json
import time
import soundfile as sf
from google import genai
from google.genai import types as genai_types
try:
    from .schemas import TranscriptResult, TranscriptSegment
except ImportError:
    from schemas import TranscriptResult, TranscriptSegment


# Ekstensi diaudio ini semua audio-only, tapi mimetypes stdlib nebak .mp4 sebagai
# "video/mp4" secara default — kalau dibiarkan, Gemini nyoba proses filenya sebagai
# video dan gagal internal (code=13) karena nggak ada video stream sama sekali.
_AUDIO_MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".mp4": "audio/mp4",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".webm": "audio/webm",
}


def _get_duration(audio_path: str) -> float:
    try:
        with sf.SoundFile(audio_path) as f:
            return len(f) / f.samplerate
    except Exception:
        return 0.0


def transcribe(audio_path: str) -> TranscriptResult:
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"File audio tidak ditemukan: {audio_path}")

    supported = tuple(_AUDIO_MIME_TYPES.keys())
    if not audio_path.lower().endswith(supported):
        raise ValueError(f"Format file tidak didukung: {audio_path}")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY tidak ditemukan di environment")

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    prompt = (
        "Transcribe this meeting recording accurately and completely, in the language spoken. "
        "Identify each distinct speaker by their voice and label them consistently as "
        "SPEAKER_00, SPEAKER_01, SPEAKER_02, etc. — the same person must keep the same label "
        "everywhere they speak in the recording. "
        "Split the transcript into segments, one segment per continuous utterance by a single speaker, "
        "in chronological order. "
        "Return ONLY a JSON array with this exact shape, nothing else:\n"
        '[{"speaker": "SPEAKER_00", "text": "..."}, {"speaker": "SPEAKER_01", "text": "..."}]'
    )

    try:
        ext = os.path.splitext(audio_path)[1].lower()
        mime_type = _AUDIO_MIME_TYPES.get(ext, "audio/mpeg")

        client = genai.Client(api_key=api_key)
        audio_file = client.files.upload(
            file=audio_path,
            config=genai_types.UploadFileConfig(mime_type=mime_type),
        )

        waited = 0
        while audio_file.state.name == "PROCESSING":
            if waited >= 120:
                raise RuntimeError("Timeout menunggu file selesai diproses Gemini")
            time.sleep(2)
            waited += 2
            audio_file = client.files.get(name=audio_file.name)

        if audio_file.state.name == "FAILED":
            detail = getattr(audio_file, "error", None)
            raise RuntimeError(f"Gemini gagal memproses file audio yang diupload: {detail}")

        response = client.models.generate_content(
            model=model_name,
            contents=[audio_file, prompt],
            config=genai_types.GenerateContentConfig(response_mime_type="application/json"),
        )
        raw_segments = json.loads(response.text.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Output Gemini bukan JSON valid: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Gemini STT gagal: {e}") from e

    duration = _get_duration(audio_path)

    texts = [(seg.get("speaker") or "SPEAKER_00", seg.get("text", "").strip()) for seg in raw_segments]
    texts = [(speaker, text) for speaker, text in texts if text]
    if not texts:
        raise ValueError("Gemini tidak mengembalikan segmen transkrip")

    total_chars = sum(len(text) for _, text in texts)
    segments = []
    current_time = 0.0

    for speaker, text in texts:
        ratio = len(text) / total_chars if total_chars > 0 else 1 / len(texts)
        seg_duration = max(duration * ratio, 0.5)
        segments.append(TranscriptSegment(
            speaker=speaker,
            start=round(current_time, 2),
            end=round(current_time + seg_duration, 2),
            text=text,
        ))
        current_time += seg_duration

    return TranscriptResult(
        segments=segments,
        language="id",
        duration=duration,
    )
