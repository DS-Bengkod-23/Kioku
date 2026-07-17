try:
    from .schemas import TranscriptResult, TranscriptSegment
except ImportError:
    from schemas import TranscriptResult, TranscriptSegment


def diarize(audio_path: str) -> list[TranscriptSegment]:
    """No-op: speaker diarization sekarang dilakukan langsung oleh Gemini di
    dalam transcribe() (label speaker per segmen sudah diminta di prompt
    transkripsi). Fungsi ini dipertahankan supaya pipeline transcribe ->
    diarize -> merge di process_recording.py tidak perlu berubah.
    """
    return []


def merge_transcript_diarization(
    transcript: TranscriptResult,
    diarization: list[TranscriptSegment],
) -> TranscriptResult:
    if not diarization:
        return transcript

    for segment in transcript.segments:
        mid = (segment.start + segment.end) / 2
        matched = "SPEAKER_00"
        for turn in diarization:
            if turn.start <= mid <= turn.end:
                matched = turn.speaker
                break
        segment.speaker = matched

    return transcript
