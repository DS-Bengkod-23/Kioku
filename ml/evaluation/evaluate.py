"""
Evaluasi kualitas pipeline ML MeetMate.
Metrics: WER (Word Error Rate) + Action Item F1.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

GOLDEN_DIR = Path(__file__).parent / "golden_dataset"
RESULTS_FILE = Path(__file__).parent / "results.json"


def compute_wer(reference: str, hypothesis: str) -> float:
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()

    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]
    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            cost = 0 if ref_words[i - 1] == hyp_words[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)

    return d[len(ref_words)][len(hyp_words)] / max(len(ref_words), 1)


def _task_match(golden_task: str, predicted_task: str, threshold: float = 0.4) -> bool:
    """Fuzzy match: cek apakah >= 40% kata dari golden task muncul di predicted task."""
    g_words = set(golden_task.lower().split())
    p_words = set(predicted_task.lower().split())
    if not g_words:
        return True
    overlap = len(g_words & p_words) / len(g_words)
    return overlap >= threshold


def compute_action_item_f1(golden: list[dict], predicted: list[dict]) -> float:
    if not golden:
        return 1.0 if not predicted else 0.0

    tp = 0
    for g in golden:
        for p in predicted:
            if _task_match(g["task"], p["task"]):
                tp += 1
                break

    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(golden)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return f1


def run_evaluation():
    from transcribe import transcribe
    from extract import extract_action_items

    results = []

    for sample_dir in sorted(GOLDEN_DIR.iterdir()):
        if not sample_dir.is_dir() or sample_dir.name.startswith("."):
            continue

        audio_file = sample_dir / "audio.wav"
        golden_transcript = (sample_dir / "transcript.txt").read_text(encoding="utf-8").strip()
        golden_actions = json.loads((sample_dir / "action_items.json").read_text(encoding="utf-8"))

        participants_file = sample_dir / "participants.json"
        participant_names = (
            json.loads(participants_file.read_text(encoding="utf-8"))
            if participants_file.exists()
            else []
        )

        transcript = transcribe(str(audio_file))

        hypothesis = " ".join(seg.text for seg in transcript.segments)
        wer = compute_wer(golden_transcript, hypothesis)

        transcript_text = "\n".join(
            f"{seg.speaker}: {seg.text}" for seg in transcript.segments
        )
        predicted_actions = extract_action_items(transcript_text, participant_names)
        f1 = compute_action_item_f1(golden_actions, [a.model_dump() for a in predicted_actions])

        results.append({"sample": sample_dir.name, "wer": round(wer, 4), "action_item_f1": round(f1, 4)})
        print(f"{sample_dir.name}: WER={wer:.2%}, F1={f1:.4f}")

    avg_wer = sum(r["wer"] for r in results) / len(results) if results else 0
    avg_f1 = sum(r["action_item_f1"] for r in results) / len(results) if results else 0
    print(f"\nAverage WER: {avg_wer:.2%} (target < 20%)")
    print(f"Average F1:  {avg_f1:.4f} (target >= 0.6)")

    RESULTS_FILE.write_text(
        json.dumps({"samples": results, "avg_wer": avg_wer, "avg_f1": avg_f1}, indent=2)
    )


if __name__ == "__main__":
    run_evaluation()
