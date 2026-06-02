import os
from pyannote.audio import Pipeline
try:
    from .schemas import TranscriptResult, TranscriptSegment
except ImportError:
    from schemas import TranscriptResult, TranscriptSegment


def diarize(audio_path: str) -> list[TranscriptSegment]:
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"File audio tidak ditemukan: {audio_path}")

    hf_token = os.getenv("HF_TOKEN")
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=hf_token,
        )
        result = pipeline(audio_path)
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
