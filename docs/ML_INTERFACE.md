# ML Interface

**Status:** Draft v0.1
**Owner:** Azmi (ML), Audi (Backend)

Dokumen ini mendefinisikan function signature dan schema yang dipakai Backend (Celery Worker) untuk memanggil ML pipeline. Semua output menggunakan Pydantic schema agar Backend tidak perlu parsing teks bebas.

---

## Pydantic Schemas

```python
from pydantic import BaseModel
from typing import Optional

class TranscriptSegment(BaseModel):
    speaker: str        # "SPEAKER_00", "SPEAKER_01", dst
    start: float        # detik, contoh: 0.0
    end: float          # detik, contoh: 14.5
    text: str           # teks transkrip segmen ini

class TranscriptResult(BaseModel):
    segments: list[TranscriptSegment]
    language: str       # "id", "en", atau "id+en"
    duration: float     # total durasi audio dalam detik

class SummaryResult(BaseModel):
    tldr: str                   # ringkasan 2-3 kalimat
    decisions: list[str]        # list keputusan yang diambil
    topics: list[str]           # topik-topik yang dibahas

class ActionItem(BaseModel):
    task: str                           # deskripsi tugas
    assignee_name: Optional[str]        # nama assignee kalau disebut, None kalau tidak
    due_date_text: Optional[str]        # teks deadline asli, misal "Jumat", "minggu depan"
```

---

## Functions

### 1. transcribe

Konversi file audio menjadi teks transkrip mentah (tanpa diarization).

```python
def transcribe(audio_path: str) -> TranscriptResult:
    """
    Args:
        audio_path: path absolut ke file audio lokal

    Returns:
        TranscriptResult dengan segments, language, duration

    Raises:
        FileNotFoundError: jika file tidak ditemukan
        ValueError: jika format file tidak didukung
        RuntimeError: jika Whisper gagal proses
    """
```

**Contoh input:**
```python
transcribe("/tmp/recordings/meeting-123/audio.mp3")
```

**Contoh output:**
```python
TranscriptResult(
    segments=[
        TranscriptSegment(
            speaker="SPEAKER_00",
            start=0.0,
            end=14.5,
            text="Oke selamat pagi semua, kita mulai sprint planning."
        ),
        TranscriptSegment(
            speaker="SPEAKER_00",
            start=14.5,
            end=28.0,
            text="Agenda hari ini ada tiga poin."
        )
    ],
    language="id",
    duration=3612.5
)
```

> Catatan: Hasil transcribe belum ada diarization. Semua segment speaker-nya "SPEAKER_00". Diarization dilakukan terpisah di fungsi `diarize`, lalu digabungkan di `merge_transcript_diarization`.

---

### 2. diarize

Pisahkan segmen audio per speaker (siapa ngomong kapan).

```python
def diarize(audio_path: str) -> list[TranscriptSegment]:
    """
    Args:
        audio_path: path absolut ke file audio lokal (file yang sama dengan transcribe)

    Returns:
        list TranscriptSegment dengan speaker label dan timestamp,
        tapi text masih kosong (diisi saat merge)

    Raises:
        FileNotFoundError: jika file tidak ditemukan
        RuntimeError: jika pyannote gagal proses
    """
```

**Contoh output:**
```python
[
    TranscriptSegment(speaker="SPEAKER_00", start=0.0, end=45.2, text=""),
    TranscriptSegment(speaker="SPEAKER_01", start=45.2, end=78.9, text=""),
    TranscriptSegment(speaker="SPEAKER_00", start=78.9, end=120.0, text=""),
]
```

---

### 3. merge_transcript_diarization

Gabungkan hasil Whisper (text) dengan hasil pyannote (speaker label).

```python
def merge_transcript_diarization(
    transcript: TranscriptResult,
    diarization: list[TranscriptSegment]
) -> TranscriptResult:
    """
    Args:
        transcript: output dari transcribe()
        diarization: output dari diarize()

    Returns:
        TranscriptResult baru dengan speaker label yang sudah diisi
        berdasarkan overlap timestamp terbesar antara Whisper dan pyannote
    """
```

---

### 4. extract_summary

Generate summary, keputusan, dan topik dari teks transkrip.

```python
def extract_summary(transcript_text: str) -> SummaryResult:
    """
    Args:
        transcript_text: teks transkrip lengkap sebagai string
                         (gabungan semua segment.text dengan format
                          "SPEAKER_00: teks\nSPEAKER_01: teks\n...")

    Returns:
        SummaryResult dengan tldr, decisions, topics

    Raises:
        RuntimeError: jika API provider (OpenAI/Gemini) tidak bisa diakses
        ValueError: jika output LLM tidak valid JSON
    """
```

**Contoh input:**
```python
transcript_text = """
SPEAKER_00: Oke selamat pagi semua, kita mulai sprint planning.
SPEAKER_01: Siap, saya sudah review backlog-nya.
SPEAKER_00: Bagus. Kita putuskan deploy ke staging hari Rabu ya.
SPEAKER_01: Setuju. Saya akan handle testing-nya.
"""

extract_summary(transcript_text)
```

**Contoh output:**
```python
SummaryResult(
    tldr="Sprint planning membahas deployment ke staging dan pembagian task testing minggu ini.",
    decisions=["Deploy ke staging hari Rabu", "SPEAKER_01 handle testing"],
    topics=["Review backlog", "Jadwal deployment", "Pembagian task"]
)
```

---

### 5. extract_action_items

Extract action item dari teks transkrip.

```python
def extract_action_items(
    transcript_text: str,
    participant_names: list[str]
) -> list[ActionItem]:
    """
    Args:
        transcript_text: teks transkrip lengkap (format sama dengan extract_summary)
        participant_names: list nama peserta meeting sebagai context untuk LLM
                           contoh: ["Audi", "Helena", "Azmi"]

    Returns:
        list ActionItem. Bisa kosong jika tidak ada action item ditemukan.

    Raises:
        RuntimeError: jika API provider (OpenAI/Gemini) tidak bisa diakses
        ValueError: jika output LLM tidak valid JSON
    """
```

**Contoh output:**
```python
[
    ActionItem(
        task="Handle testing deployment staging",
        assignee_name="Helena",
        due_date_text="Rabu"
    ),
    ActionItem(
        task="Finalize backlog untuk sprint berikutnya",
        assignee_name=None,
        due_date_text=None
    )
]
```

---

## Urutan Pemanggilan di Celery Worker

Backend memanggil fungsi-fungsi di atas dalam urutan ini:

```python
from ml.transcribe import transcribe
from ml.diarize import diarize, merge_transcript_diarization
from ml.extract import extract_summary, extract_action_items

def process_recording(audio_path: str, participant_names: list[str]):
    # Step 1: Transcribe
    transcript = transcribe(audio_path)

    # Step 2: Diarize
    diarization = diarize(audio_path)

    # Step 3: Merge
    transcript_with_speakers = merge_transcript_diarization(transcript, diarization)

    # Step 4: Buat teks transkrip untuk LLM
    transcript_text = "\n".join(
        f"{seg.speaker}: {seg.text}"
        for seg in transcript_with_speakers.segments
    )

    # Step 5: Extract summary
    summary = extract_summary(transcript_text)

    # Step 6: Extract action items
    action_items = extract_action_items(transcript_text, participant_names)

    return transcript_with_speakers, summary, action_items
```

---

## Lokasi File di Repo

```
ml/
├── transcribe.py       # fungsi transcribe()
├── diarize.py          # fungsi diarize() + merge_transcript_diarization()
├── extract.py          # fungsi extract_summary() + extract_action_items()
├── schemas.py          # semua Pydantic schemas (TranscriptResult, dll)
├── requirements.txt    # dependency ML
└── notebooks/          # eksperimen Azmi (tidak dipakai Backend)
```

Backend import langsung dari folder `ml/`:
```python
from ml.schemas import TranscriptResult, SummaryResult, ActionItem
from ml.transcribe import transcribe
```

---

## Notes untuk Azmi (ML)

1. Output wajib pakai Pydantic schema yang sudah didefinisikan di atas. Jangan return dict biasa.
2. Setiap fungsi wajib raise exception yang spesifik (bukan silent fail) supaya Backend bisa handle error dengan benar.
3. `OPENAI_API_KEY` (atau `GEMINI_API_KEY` kalau `LLM_PROVIDER=gemini`) dan `HF_TOKEN` harus terisi di `.env` sebelum Worker dijalankan — transcribe/extract lewat API cloud, diarize butuh HF_TOKEN untuk download model pyannote.
4. Untuk development awal, boleh hardcode `audio_path` di notebook. Tapi function signature harus sudah sesuai dokumen ini sebelum Backend mulai integrasi.
5. Kalau ada perubahan schema atau function signature, diskusi dulu dengan Audi sebelum diubah.