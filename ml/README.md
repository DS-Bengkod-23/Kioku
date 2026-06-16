# MeetMate ML Pipeline

Speech-to-text, diarization, dan LLM extraction untuk MeetMate.

**Owner:** Azmi

---

## Stack

- **Whisper large-v3** - transcription (speech to text)
- **pyannote.audio** - speaker diarization
- **Hybrid LLM (OpenAI API / Ollama qwen2.5:7b)** - summary + action item extraction

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

Whisper butuh `ffmpeg` untuk membaca file audio. Tanpa ini akan muncul `[WinError 2] The system cannot find the file specified`.

**2. Install dependency Python**
```bash
pip install -r requirements.txt
```

**2. Konfigurasi LLM Provider**

Set di file `.env` di root repo (pilih salah satu):

```env
# Opsi A: OpenAI API (rekomendasi, tidak perlu GPU)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Opsi B: Ollama lokal (butuh GPU, gratis)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

Jika pakai Ollama, install dan jalankan dulu di host machine:
```bash
ollama pull qwen2.5:7b
ollama serve
```

**3. Pyannote setup**

pyannote butuh Hugging Face token untuk download model pertama kali. Buat akun di https://huggingface.co, accept terms model `pyannote/speaker-diarization-3.1`, lalu set di `.env`:
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

| Model | Minimum RAM | Rekomendasi |
|---|---|---|
| Whisper large-v3 | 10GB VRAM / 16GB RAM | GPU |
| pyannote.audio | 4GB RAM | CPU ok |
| qwen2.5:7b | 8GB VRAM / 16GB RAM | GPU |

Kalau RAM terbatas, ganti Whisper ke `medium` atau `small` di `.env`.