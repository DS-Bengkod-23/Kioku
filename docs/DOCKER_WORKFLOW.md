# Panduan Docker dan Software Engineering Workflow MeetMate

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
2. [Ollama](https://ollama.com/) — (harus tetap di-run di host machine, bukan Docker, agar Ollama bisa mendapat akses langsung ke GPU untuk model `qwen2.5:7b`).

### Langkah-Langkah Menjalankan
Cukup buka terminal di root folder (Aplikasi), lalu jalankan perintah berikut menggunakan Make:

```bash
# 1. Menjalankan semuanya di background (build otomatis jika belum pernah)
make up

# ATAU jika ada perubahan dependencies (requirements.txt / package.json), gunakan:
make build
```

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

## Konfigurasi LLM (OpenAI vs Ollama)
Sistem ini mendukung **Hybrid LLM Provider**. Anda bebas memilih ingin menggunakan **OpenAI API** atau **Ollama (Lokal)** dengan cukup mengubah satu baris di file `.env`:

### Jika Menggunakan OpenAI (Rekomendasi untuk Laptop Biasa)
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
```
Anda tidak perlu mendownload model apapun. Semua teks akan diproses di cloud.

### Jika Menggunakan Ollama Lokal (Rekomendasi jika Punya GPU Kuat)
```env
LLM_PROVIDER=ollama
```
1. Pastikan Anda telah menginstall aplikasi Ollama di PC Anda (bukan di dalam Docker).
2. Jalankan perintah `ollama pull qwen2.5:7b` di terminal PC Anda.
3. Celery worker telah di-set otomatis untuk memanggil Ollama via URL `http://host.docker.internal:11434`.
