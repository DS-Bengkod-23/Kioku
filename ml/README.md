# MeetMate ML Pipeline

Speech-to-text, diarization, dan LLM extraction untuk MeetMate.

**Owner:** Azmi

---

## Stack

- **Gemini API** - transcription (speech to text) dengan speaker label per segmen, summary, dan action item extraction

---

## Struktur Folder

```
ml/
├── schemas.py          # Pydantic schemas (TranscriptResult, SummaryResult, dst)
├── transcribe.py       # fungsi transcribe() via Gemini (transkripsi + label speaker)
├── diarize.py          # no-op, dipertahankan untuk kompatibilitas signature pipeline
├── extract.py          # fungsi extract_summary() + extract_action_items()
├── prompts/
│   ├── summary.txt     # prompt template untuk summary
│   └── action_items.txt # prompt template untuk action items
├── evaluation/
│   ├── golden_dataset/ # 10 sample meeting untuk evaluasi
│   └── evaluate.py     # script ukur WER + action item F1
├── requirements.txt
└── README.md
```

---

## Setup

**1. Install dependency Python**
```bash
pip install -r requirements.txt
```

**2. Konfigurasi Gemini API**

Set di file `.env` di root repo:

```env
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.1-flash-lite
```

Dipakai bareng oleh `transcribe()` (transkripsi + diarization), `extract_summary()`, dan `extract_action_items()`.

---

## Development Workflow

Urutan development yang disarankan:

1. Pastikan function signature sesuai `docs/ML_INTERFACE.md`
2. Test masing-masing modul secara terpisah (`transcribe.py`, `extract.py`)
3. Jalankan `evaluation/evaluate.py` untuk ukur kualitas

---

## Interface dengan Backend

Backend (Celery Worker) import langsung dari folder ini:

```python
from ml.schemas import TranscriptResult, SummaryResult, ActionItem
from ml.transcribe import transcribe
from ml.diarize import diarize, merge_transcript_diarization
from ml.extract import extract_summary, extract_action_items
```

Lihat `docs/ML_INTERFACE.md` untuk detail function signature dan schema.

**Penting:** Jangan ubah function signature tanpa diskusi dengan Audi (Backend). `diarize()` dan `merge_transcript_diarization()` sudah jadi no-op (speaker label sekarang datang langsung dari `transcribe()`), tapi signature-nya sengaja dipertahankan supaya pipeline `transcribe -> diarize -> merge` di `process_recording.py` tidak perlu diubah.

---

## Evaluasi

Target metric MVP:
- WER (Word Error Rate) transcription: < 20%
- Action item F1: >= 0.6

Jalankan evaluasi:
```bash
python evaluation/evaluate.py
```

Hasil evaluasi disimpan di `evaluation/results.json`.
