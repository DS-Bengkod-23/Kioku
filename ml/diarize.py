import os
import subprocess
import tempfile
import torch
import soundfile as sf
from pyannote.audio import Pipeline
try:
    from .schemas import TranscriptResult, TranscriptSegment
except ImportError:
    from schemas import TranscriptResult, TranscriptSegment
try:
    from .errors import PermanentMLError
except ImportError:
    from errors import PermanentMLError

_pipeline = None


def _get_pipeline() -> Pipeline:
    # Pipeline.from_pretrained() memuat beberapa sub-model — mahal untuk dijalankan
    # ulang di tiap panggilan diarize(), dan berisiko OOM kalau worker Celery
    # concurrency > 1 (beberapa copy model resident bersamaan). Cache sekali per
    # proses worker (aman untuk prefork: tiap child dapat cache-nya sendiri
    # setelah panggilan pertamanya).
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=os.getenv("HF_TOKEN"),
        )
    return _pipeline


def _load_audio(audio_path: str):
    """Load audio as torch tensor + sample rate.
    Tries torchaudio first (Mac/Linux), falls back to ffmpeg+soundfile (Windows).
    """
    try:
        import torchaudio
        return torchaudio.load(audio_path)
    except Exception:
        pass

    # Windows fallback: torchcodec not available, convert via ffmpeg subprocess
    tmp_fd, tmp_wav = tempfile.mkstemp(suffix=".wav")
    os.close(tmp_fd)
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000", "-ac", "1", tmp_wav],
            check=True,
            capture_output=True,
        )
        data, sr = sf.read(tmp_wav, dtype="float32", always_2d=True)
        return torch.from_numpy(data.T), sr  # (channels, samples)
    finally:
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)


def diarize(audio_path: str) -> list[TranscriptSegment]:
    # Kalau LLM_PROVIDER=gemini, transcribe() sudah minta Gemini melabeli speaker
    # langsung di prompt transkripsi (lihat _transcribe_gemini di transcribe.py) —
    # skip pyannote sepenuhnya di sini, jangan load model/HF_TOKEN/torch sama
    # sekali, supaya jalur Gemini murni tidak bergantung ke pyannote.
    if os.getenv("LLM_PROVIDER", "openai").lower() == "gemini":
        return []

    # PermanentMLError (bukan FileNotFoundError polos) supaya Celery task tidak
    # buang 3x retry untuk error yang pasti gagal identik lagi.
    if not os.path.exists(audio_path):
        raise PermanentMLError(f"File audio tidak ditemukan: {audio_path}")

    try:
        pipeline = _get_pipeline()
        waveform, sample_rate = _load_audio(audio_path)
        result = pipeline({"waveform": waveform, "sample_rate": sample_rate})
    except Exception as e:
        raise RuntimeError(f"pyannote gagal memproses audio: {e}") from e

    annotation = result if hasattr(result, 'itertracks') else result.speaker_diarization

    return [
        TranscriptSegment(speaker=speaker, start=turn.start, end=turn.end, text="")
        for turn, _, speaker in annotation.itertracks(yield_label=True)
    ]


def merge_transcript_diarization(
    transcript: TranscriptResult,
    diarization: list[TranscriptSegment],
) -> TranscriptResult:
    if not diarization:
        # Kosong berarti diarize() di-skip (jalur Gemini, speaker sudah dilabeli
        # transcribe() sendiri) — jangan reset ke SPEAKER_00, biarkan apa adanya.
        return transcript

    for segment in transcript.segments:
        mid = (segment.start + segment.end) / 2
        inside = [turn for turn in diarization if turn.start <= mid <= turn.end]
        if inside:
            matched = inside[0].speaker
        else:
            # mid jatuh di jeda antar-turn (boundary Whisper vs pyannote jarang
            # persis sama) — pakai speaker dari turn terdekat, bukan hardcode
            # SPEAKER_00 yang mem-bias semua jeda ke speaker pertama.
            matched = min(
                diarization,
                key=lambda turn: min(abs(mid - turn.start), abs(mid - turn.end)),
            ).speaker
        segment.speaker = matched

    return transcript
