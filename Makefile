.PHONY: up down logs migrate restart build check pre-commit

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

# Menjalankan migrasi database di dalam container backend
migrate:
	docker compose exec backend-api alembic upgrade head

# Menjalankan format pre-commit secara manual
pre-commit:
	pre-commit run --all-files
