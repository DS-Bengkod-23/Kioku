import os
import re
import time
import soundfile as sf
from openai import OpenAI, BadRequestError, AuthenticationError, PermissionDeniedError, NotFoundError
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
try:
    from .schemas import TranscriptResult, TranscriptSegment
except ImportError:
    from schemas import TranscriptResult, TranscriptSegment
try:
    from .errors import PermanentMLError
except ImportError:
    from errors import PermanentMLError


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


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _transcribe_openai(audio_path: str) -> TranscriptResult:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY tidak ditemukan di environment")

    model_name = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")

    try:
        ext = os.path.splitext(audio_path)[1].lower()
        mime_type = _AUDIO_MIME_TYPES.get(ext, "audio/mpeg")

        # whisper-1 menolak file berekstensi .mp4 walau 'mp4' ada di daftar format
        # yang didukung (bug/quirk dari OpenAI) — .m4a adalah kontainer yang sama
        # persis (MPEG-4 audio-only), jadi aman di-relabel biar diterima.
        send_ext = ".m4a" if ext == ".mp4" else ext

        client = OpenAI(api_key=api_key)
        with open(audio_path, "rb") as f:
            file_bytes = f.read()

        response = client.audio.transcriptions.create(
            model=model_name,
            file=(f"audio{send_ext}", file_bytes, mime_type),
            response_format="verbose_json",
            language="id",
        )
    except (BadRequestError, AuthenticationError, PermissionDeniedError, NotFoundError) as e:
        raise PermanentMLError(f"OpenAI Whisper gagal (permanen): {e}") from e
    except Exception as e:
        raise RuntimeError(f"OpenAI Whisper gagal: {e}") from e

    raw_segments = getattr(response, "segments", None) or []
    segments = [
        TranscriptSegment(
            speaker="SPEAKER_00",
            start=round(seg.start, 2),
            end=round(seg.end, 2),
            text=seg.text.strip(),
        )
        for seg in raw_segments
    ]

    duration = getattr(response, "duration", None) or 0.0

    if not segments:
        segments = [TranscriptSegment(
            speaker="SPEAKER_00",
            start=0.0,
            end=duration,
            text=response.text.strip(),
        )]

    return TranscriptResult(
        segments=segments,
        language=getattr(response, "language", None) or "id",
        duration=duration,
    )


def _transcribe_gemini(audio_path: str) -> TranscriptResult:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY tidak ditemukan di environment")

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    try:
        ext = os.path.splitext(audio_path)[1].lower()
        mime_type = _AUDIO_MIME_TYPES.get(ext, "audio/mpeg")

        client = genai.Client(api_key=api_key)
        audio_file = client.files.upload(
            file=audio_path,
            config=types.UploadFileConfig(mimeType=mime_type),
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

    except genai_errors.ClientError as e:
        raise PermanentMLError(f"Gemini STT gagal (permanen): {e}") from e
    except Exception as e:
        raise RuntimeError(f"Gemini STT gagal: {e}") from e

    duration = _get_duration(audio_path)
    sentences = _split_sentences(full_text)

    if not sentences:
        sentences = [full_text]

    total_chars = sum(len(s) for s in sentences)
    segments = []
    current_time = 0.0

    for sentence in sentences:
        ratio = len(sentence) / total_chars if total_chars > 0 else 1 / len(sentences)
        seg_duration = max(duration * ratio, 0.5)
        segments.append(TranscriptSegment(
            speaker="SPEAKER_00",
            start=round(current_time, 2),
            end=round(current_time + seg_duration, 2),
            text=sentence,
        ))
        current_time += seg_duration

    return TranscriptResult(
        segments=segments,
        language="id",
        duration=duration,
    )

def transcribe(audio_path: str) -> TranscriptResult:
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"File audio tidak ditemukan: {audio_path}")

    supported = (".mp3", ".mp4", ".wav", ".m4a", ".flac", ".ogg", ".webm")
    if not audio_path.lower().endswith(supported):
        raise ValueError(f"Format file tidak didukung: {audio_path}")

    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "gemini":
        return _transcribe_gemini(audio_path)
    return _transcribe_openai(audio_path)
