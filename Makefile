.PHONY: init up down logs migrate restart build check pre-commit infra build-worker build-api build-frontend

# Setup awal — bikin .env dari .env.example kalau belum ada (tidak menimpa yang sudah ada)
init:
	@if [ -f .env ]; then \
		echo ".env sudah ada, tidak ditimpa."; \
	else \
		cp .env.example .env; \
		echo ".env dibuat dari .env.example — isi OPENAI_API_KEY dan HF_TOKEN dulu sebelum 'make up'."; \
	fi

# Menjalankan semua services
up:
	docker compose up -d

# Membangun ulang dan menjalankan semua services
build:
	docker compose up --build -d

# Menghentikan semua services
down:
	docker compose down

# Menghentikan semua services dan menghapus volume (reset database)
down-v:
	docker compose down -v

# Melihat logs dari semua services
logs:
	docker compose logs -f

# Melihat logs khusus backend API
logs-api:
	docker compose logs -f backend-api

# Melihat logs khusus celery worker
logs-worker:
	docker compose logs -f celery-worker

# Melihat logs khusus celery beat (scheduler reminder harian)
logs-beat:
	docker compose logs -f celery-beat

# Menjalankan migrasi database di dalam container backend
migrate:
	docker compose exec backend-api alembic upgrade head

# Menjalankan format pre-commit secara manual
pre-commit:
	pre-commit run --all-files

# [Hybrid mode] Jalankan infrastruktur + celery-worker sekaligus
infra:
	docker compose up -d postgres redis minio mailhog
	docker compose up --build -d --no-deps celery-worker

# [Hybrid mode] Rebuild celery-worker saja (jika ada perubahan di ml/ atau requirements.txt)
build-worker:
	docker compose build celery-worker
	docker compose up -d --no-deps celery-worker

# Rebuild backend-api saja (jika ada perubahan di backend/ yang dipakai FastAPI, bukan celery-worker)
build-api:
	docker compose up -d --build --no-deps backend-api

# Rebuild frontend saja (jika ada perubahan di frontend/)
build-frontend:
	docker compose up -d --build --no-deps frontend
