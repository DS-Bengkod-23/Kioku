## Code Review — ML Pipeline

**Reviewer:** Audi
**Referensi:** `docs/ML_INTERFACE.md`, `docs/PRD.md`

---

> [!CAUTION]
> **Status: TIDAK BISA MERGE** — Ada 9 breaking contract violation yang akan bikin Backend gagal total saat integrasi.

Secara umum fondasi sudah oke: struktur folder sesuai, Whisper/pyannote/Ollama sudah terhubung, logika WER dan F1 di evaluate.py benar. Tapi semua schema Pydantic dan signature fungsi `extract_*` melenceng dari kontrak yang sudah kita sepakati di `ML_INTERFACE.md`.

---

### 🔴 Critical — Breaking Contract (wajib fix sebelum merge)

#### 1. `schemas.py` — TranscriptResult

Field `duration` **hilang**. Backend butuh ini untuk fitur "notulen terkirim < 50% durasi meeting".

```python
# Kontrak
class TranscriptResult(BaseModel):
    segments: list[TranscriptSegment]
    language: str       # required, bukan Optional
    duration: float     # ← TIDAK ADA di implementasimu

# Implementasimu (schemas.py:12-16)
class TranscriptResult(BaseModel):
    segments: list[TranscriptSegment]
    full_text: str        # tidak ada di kontrak
    language: Optional[str] = None  # diubah jadi Optional tanpa diskusi
```

---

#### 2. `schemas.py` — ActionItem

Dua field diganti nama. Ini langsung bikin `AttributeError` di sisi Backend.

```python
# Kontrak
class ActionItem(BaseModel):
    task: str
    assignee_name: Optional[str]   # ← bukan 'assignee'
    due_date_text: Optional[str]   # ← bukan 'deadline'

# Implementasimu (schemas.py:18-21)
class ActionItem(BaseModel):
    assignee: Optional[str]         # ← harusnya assignee_name
    task: str
    deadline: Optional[str] = None  # ← harusnya due_date_text
```

---

#### 3. `schemas.py` — SummaryResult

Semua field berbeda dari kontrak.

```python
# Kontrak
class SummaryResult(BaseModel):
    tldr: str
    decisions: list[str]
    topics: list[str]

# Implementasimu (schemas.py:24-27)
class SummaryResult(BaseModel):
    summary: str                    # ← harusnya tldr
    action_items: list[ActionItem]  # ← harusnya decisions: list[str]
    key_points: list[str]           # ← harusnya topics
```

`action_items` tidak seharusnya ada di dalam `SummaryResult`. Ada `extract_action_items()` sendiri untuk itu.

---

#### 4. `extract.py` — `extract_summary()` — Input dan Output dua-duanya salah

```python
# Kontrak
def extract_summary(transcript_text: str) -> SummaryResult: ...

# Implementasimu (extract.py:17)
def extract_summary(transcript: TranscriptResult) -> str: ...
```

Backend akan kirim `str`, langsung `TypeError`. Dan output-nya `str` mentah dari LLM — Backend expect object dengan `.tldr`, `.decisions`, `.topics`.

---

#### 5. `extract.py` — `extract_action_items()` — Parameter hilang, input salah

```python
# Kontrak
def extract_action_items(transcript_text: str, participant_names: list[str]) -> list[ActionItem]: ...

# Implementasimu (extract.py:28)
def extract_action_items(transcript: TranscriptResult) -> list[ActionItem]: ...
```

`participant_names` bukan opsional. LLM butuh konteks nama peserta supaya bisa resolve siapa assignee-nya. Tanpa ini, akurasi action item turun.

---

#### 6. `diarize.py` — `diarize()` — Return type salah

```python
# Kontrak
def diarize(audio_path: str) -> list[TranscriptSegment]: ...

# Implementasimu (diarize.py:9)
def diarize(audio_path: str) -> list[dict]: ...
```

---

### 🟠 High — Perlu Fix Sebelum Week 4

#### 7. Error handling tidak ada

Kontrak mewajibkan exception yang spesifik supaya Celery Worker bisa handle retry dengan benar:

| Fungsi | Exception yang Dijanjikan | Status |
|--------|--------------------------|--------|
| `transcribe()` | `FileNotFoundError`, `ValueError`, `RuntimeError` | ❌ Tidak ada |
| `diarize()` | `FileNotFoundError`, `RuntimeError` | ❌ Tidak ada |
| `extract_summary()` | `RuntimeError`, `ValueError` | ❌ Tidak ada |
| `extract_action_items()` | `RuntimeError`, `ValueError` | ❌ `json.loads()` tanpa try/except di line 40 |

#### 8. Evaluation dataset — baru 1 dari 10 sample

PRD Week 4 target 10 golden samples. Sekarang baru ada `sample_01`. Angka WER dan F1 dari 1 sample tidak representatif.

#### 9. WER tidak memenuhi target MVP

```
results.json → avg_wer: 0.3333 (33.33%)
Target PRD   → WER < 20%
```

Perlu investigasi: coba audio preprocessing, normalisasi teks sebelum WER hitung, atau turun ke Whisper medium kalau memang hardware jadi bottleneck.

---

### 🟡 Medium — Notes

<details>
<summary>Prompt engineering issues</summary>

- `prompts/summary.txt` minta output paragraf biasa, padahal Backend butuh JSON untuk parse ke `SummaryResult`. Update prompt supaya output JSON dengan key `tldr`, `decisions`, `topics`.
- `prompts/action_items.txt` tidak menyertakan injeksi `participant_names`. Setelah signature diperbaiki, update prompt juga.
- Tidak ada few-shot example di kedua prompt. PRD mention ini sebagai mitigasi risiko kualitas LLM lokal.

</details>

<details>
<summary>evaluate.py issues</summary>

- Di `evaluate.py:60`, `extract_action_items(transcript)` dipanggil tanpa `participant_names` — tidak sesuai kontrak yang harusnya kita uji.
- `extract_summary()` tidak dievaluasi sama sekali. Perlu tambah metric untuk kualitas summary.

</details>

<details>
<summary>Notebooks belum ada</summary>

README dokumentasikan 3 notebook (`01_whisper_test.ipynb`, `02_diarization_test.ipynb`, `03_llm_extraction_test.ipynb`) tapi tidak ada satu pun di repo. PRD Week 1 target "ML pipeline standalone di notebook".

</details>

---

### ✅ Yang Sudah Bagus

- `TranscriptSegment` schema — persis sesuai kontrak
- Struktur folder `ml/` — sesuai
- Whisper, pyannote, Ollama semuanya pakai versi yang benar (tech stack sesuai)
- `requirements.txt` — lengkap dan versi di-pin
- Konfigurasi model via env var (`WHISPER_MODEL`, `OLLAMA_MODEL`) — good practice
- Merge strategy di `merge_transcript_diarization` (midpoint matching) — pendekatan valid
- Implementasi `compute_wer()` dan `compute_action_item_f1()` di evaluate.py — algoritmanya benar
- README ML — dokumentasi lengkap

---

### Prioritas Perbaikan

1. **Selaraskan semua schema** di `schemas.py` dengan `ML_INTERFACE.md`
2. **Perbaiki signature** `extract_summary()` dan `extract_action_items()`
3. **Perbaiki return type** `diarize()` jadi `list[TranscriptSegment]`
4. **Tambah error handling** eksplisit di semua fungsi
5. **Update prompt** `summary.txt` supaya output JSON terstruktur dan inject `participant_names` ke `action_items.txt`
6. **Tambah golden dataset** sampai 10 sample
7. **Investigasi WER** — target < 20%

Kalau ada reasoning di balik keputusan desain (misalnya kenapa `full_text` ditambah, atau kenapa `diarize()` return dict), silakan reply di sini — mungkin ada yang bisa kita sesuaikan di kontrak. Tapi untuk field rename dan missing parameter, itu harus balik ke kontrak karena Backend sudah mulai development berdasarkan schema yang disepakati.

cc @azmi
