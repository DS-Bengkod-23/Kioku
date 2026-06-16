@echo off
cd /d "%~dp0.."

if "%1" == "up" (
    docker compose up -d
    goto :EOF
)

if "%1" == "build" (
    docker compose up --build -d
    goto :EOF
)

if "%1" == "down" (
    docker compose down
    goto :EOF
)

if "%1" == "down-v" (
    docker compose down -v
    goto :EOF
)

if "%1" == "logs" (
    docker compose logs -f
    goto :EOF
)

if "%1" == "logs-api" (
    docker compose logs -f backend-api
    goto :EOF
)

if "%1" == "logs-worker" (
    docker compose logs -f celery-worker
    goto :EOF
)

if "%1" == "migrate" (
    docker compose exec backend-api alembic upgrade head
    goto :EOF
)

if "%1" == "pre-commit" (
    pre-commit run --all-files
    goto :EOF
)

echo Usage: make [up^|build^|down^|down-v^|logs^|logs-api^|logs-worker^|migrate^|pre-commit]
