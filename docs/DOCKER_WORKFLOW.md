# Panduan Docker dan Software Engineering Workflow Kioku

Dokumen ini menjelaskan struktur infrastruktur yang baru saja diperbarui menggunakan Docker dan best-practices software engineering. Tujuannya adalah untuk memudahkan kolaborasi antar developer (Frontend, Backend, dan ML) tanpa perlu memikirkan bentrok versi *dependencies*.

## Apa Saja yang Berubah?
1. **Containerisasi Seluruh Komponen:** 
   Frontend, Backend API, dan Celery Worker sekarang di-run via Docker. Worker ML dan Backend telah dibungkus menjadi satu image, sehingga tidak perlu menginstall librosa, whisper, maupun pytorch di laptop masing-masing secara manual.
2. **Makefile Shortcut:** 
   Di-generate file `Makefile` di root agar tidak perlu mengetik command docker compose yang panjang.
3. **Pre-commit Hooks:**
   Telah disiapkan `.pre-commit-config.yaml` agar *style formatting* kode Python/JS otomatis rapi saat Anda mengetik `git commit`.

---

## Cara Menjalankan

### Persiapan (Prerequisites)
Pastikan hal ini **sudah jalan di host machine** (laptop/PC) Anda:
1. Docker & Docker Compose
2. API Key salah satu LLM provider (OpenAI atau Gemini — lihat [Konfigurasi LLM](#konfigurasi-llm-openai-vs-gemini)) dan `HF_TOKEN` HuggingFace untuk model diarization pyannote.

### Langkah-Langkah Menjalankan
Cukup buka terminal di root folder (Aplikasi), lalu jalankan perintah berikut menggunakan Make:

```bash
# 1. Menjalankan semuanya di background (build otomatis jika belum pernah)
make up

# ATAU jika ada perubahan kode (bukan cuma dependencies), rebuild dulu:
make build-api       # ubah kode backend/ yang dipakai backend-api (FastAPI)
make build-worker    # ubah kode ml/ atau backend/ yang dipakai celery-worker
make build-frontend  # ubah kode frontend/
make build           # rebuild semua service sekaligus (dependency baru di banyak service, atau nggak yakin mana yang kepakai)
```

> Container full Docker tidak hot-reload — kode di dalam image cuma ter-update kalau image-nya di-rebuild. `make up` saja tidak akan memuat perubahan kode yang sudah ada di disk.

Perintah di atas akan menyalakan semua services ini:
- **Frontend** (Next.js) di `http://localhost:3000`
- **Backend API** (FastAPI) di `http://localhost:8000`
- **Mailhog** (Email Dev) di `http://localhost:8025`
- **MinIO** (S3 Local) di `http://localhost:9001`
- **Celery Worker** (Memproses ML di background)
- **Redis & Postgres** (Infrastruktur internal)

### Migrasi Database Awal
Karena backend sudah jalan di dalam Docker, jika Anda butuh menginisiasi tabel atau melakukan migrasi Alembic, cukup ketik:

```bash
make migrate
```
Ini akan otomatis mengeksekusi `alembic upgrade head` dari dalam container `backend-api`.

### Melihat Logs
Jika Anda ingin melihat apakah ada error pada Celery worker (misalnya saat proses transkripsi ML), gunakan:

```bash
make logs-worker
```
Atau untuk Backend API:
```bash
make logs-api
```

---

## Mode Development

Untuk development aktif, mode full Docker di atas kurang nyaman karena tiap ganti kode Python/JS (yang mengandung dependency baru) perlu rebuild. Mode Hybrid ini menjalankan infrastruktur + Celery Worker via Docker, tapi Backend API dan Frontend dijalankan manual di host — jadi hot-reload aktif dan perubahan kode langsung terlihat tanpa rebuild.

**1. Jalankan infrastruktur + Celery Worker** (pertama kali build ~10-15 menit)
```bash
# Pakai make (Linux/Mac/Git Bash)
make infra

# Tanpa make (Windows CMD/PowerShell)
docker compose up -d postgres redis minio mailhog
docker compose up --build -d --no-deps celery-worker
```
Perintah ini menjalankan postgres, redis, minio, mailhog, sekaligus build dan start celery-worker dalam satu langkah. Worker tetap dijalankan via Docker (bukan lokal) untuk menghindari masalah kompatibilitas DLL di Windows.

Kalau setelah ini ada perubahan di `ml/` atau `backend/requirements.txt`, jalankan:
```bash
make build-worker   # pakai make
# atau tanpa make:
docker compose build celery-worker
docker compose up -d --no-deps celery-worker
```

> Butuh `HF_TOKEN` untuk pyannote — lihat [Quick Start di README](../README.md#quick-start). Model Whisper dan pyannote akan didownload otomatis saat pertama kali memproses recording (~3-4GB).

**2. Jalankan Backend API** (terminal baru, dari folder `backend/`)
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**3. Jalankan Frontend** (terminal baru, dari folder `frontend/`)
```bash
cd frontend
npm install
npm run dev
```

**4. Buka** `http://localhost:3000`

> Bucket MinIO (`meetmate-recordings` secara default) dibuat otomatis oleh backend saat pertama kali dibutuhkan — tidak perlu setup manual lewat MinIO Console.

---

## Pre-Commit Hook (Opsional tapi Direkomendasikan)
Agar kode Anda otomatis diformat oleh `ruff` sebelum di-push ke Github:

1. Install pre-commit di lokal Anda (sekali saja):
   ```bash
   pip install pre-commit
   pre-commit install
   ```
2. Mulai sekarang setiap Anda `git commit`, `ruff` akan memperbaiki masalah spasi, import yang tidak dipakai, dll.
3. Anda juga bisa men-trigger format manual:
   ```bash
   make pre-commit
   ```

## Konfigurasi LLM (OpenAI vs Gemini)
Sistem ini mendukung provider LLM yang bisa ditukar untuk transkripsi, ringkasan, dan ekstraksi action item — cukup ganti satu baris di file `.env`. Diarisasi (siapa bicara kapan) selalu jalan lokal via pyannote.audio, tidak terpengaruh pilihan provider ini.

### Jika Menggunakan OpenAI (Default)
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
OPENAI_TRANSCRIBE_MODEL=whisper-1
OPENAI_MODEL=gpt-4o-mini
```

### Jika Menggunakan Gemini
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.1-flash-lite
```

Setelah ganti nilai, jalankan `docker compose build celery-worker && docker compose up -d celery-worker` supaya celery-worker pakai konfigurasi baru.
