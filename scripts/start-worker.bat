@echo off
cd /d "%~dp0.."
set PYTHONPATH=%~dp0..\backend;%~dp0..
celery -A app.worker worker --loglevel=info --pool=solo
