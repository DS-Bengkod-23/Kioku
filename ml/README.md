# Kioku ML Pipeline

Speech-to-text, diarization, dan LLM extraction untuk Kioku.

**Owner:** Azmi

---

## Stack

- **OpenAI Whisper API** (default) atau **Gemini API** (switchable via `LLM_PROVIDER`) - transcription (speech to text), summary, dan action item extraction
- **pyannote.audio** - speaker diarization, selalu lokal, tidak terpengaruh `LLM_PROVIDER`

---

## Struktur Folder

```
ml/
├── schemas.py          # Pydantic schemas (TranscriptResult, SummaryResult, dst)
├── transcribe.py       # fungsi transcribe() via Whisper
├── diarize.py          # fungsi diarize() + merge_transcript_diarization()
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

**1. Install ffmpeg** (system dependency, bukan Python package)

```bash
# Conda (rekomendasi)
conda install -c conda-forge ffmpeg

# Atau download binary di https://ffmpeg.org/download.html dan tambah ke PATH
```

`diarize.py` butuh `ffmpeg` untuk membaca file audio (dipakai sebagai fallback loader di Windows kalau `torchaudio` gagal). Tanpa ini akan muncul `[WinError 2] The system cannot find the file specified`.

**2. Install dependency Python**
```bash
pip install -r requirements.txt
```

**2. Konfigurasi LLM Provider**

Set di file `.env` di root repo. Default-nya OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_TRANSCRIBE_MODEL=whisper-1
OPENAI_MODEL=gpt-4o-mini
```

Atau pakai Gemini:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.1-flash-lite
```

Dipakai bareng oleh `transcribe.py`, `extract_summary()`, dan `extract_action_items()`.

**3. Pyannote setup**

pyannote butuh Hugging Face token untuk download model pertama kali. Buat akun di https://huggingface.co, lalu accept license untuk **kedua** model ini (pipeline `speaker-diarization-3.1` memanggil `segmentation-3.0` secara internal — tanpa accept keduanya bakal muncul error 403 gated repo):
- `pyannote/speaker-diarization-3.1`
- `pyannote/segmentation-3.0`

Set token-nya di `.env`:
```env
HF_TOKEN=hf_...
```

---

## Development Workflow

Urutan development yang disarankan:

1. Pastikan function signature sesuai `docs/ML_INTERFACE.md`
2. Test masing-masing modul secara terpisah (`transcribe.py`, `diarize.py`, `extract.py`)
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

**Penting:** Jangan ubah function signature tanpa diskusi dengan Audi (Backend).

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

---

## Hardware Requirements

Transkripsi dan ekstraksi (summary/action items) jalan di API cloud (OpenAI/Gemini) — tidak butuh GPU atau RAM khusus di mesin lokal.

| Model | Minimum RAM | Rekomendasi |
|---|---|---|
| pyannote.audio (diarization, satu-satunya yang lokal) | 4GB RAM | CPU ok |