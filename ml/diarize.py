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
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"File audio tidak ditemukan: {audio_path}")

    hf_token = os.getenv("HF_TOKEN")
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=hf_token,
        )
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
    for segment in transcript.segments:
        mid = (segment.start + segment.end) / 2
        matched = "SPEAKER_00"
        for turn in diarization:
            if turn.start <= mid <= turn.end:
                matched = turn.speaker
                break
        segment.speaker = matched

    return transcript
