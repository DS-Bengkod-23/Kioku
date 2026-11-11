import re
from pathlib import Path

import pytest

from app.config import Settings

# Di container, docker-compose.yml me-mount .env.example ke /app/.env.example
# (sejajar dengan folder tests/); di luar Docker, file-nya ada di root repo.
_CANDIDATES = [
    Path(__file__).resolve().parents[1] / ".env.example",
    Path(__file__).resolve().parents[2] / ".env.example",
]


def _documented_keys() -> set[str]:
    path = next((p for p in _CANDIDATES if p.is_file()), None)
    if path is None:
        pytest.skip(".env.example tidak ditemukan (di Docker: cek volume di docker-compose.yml)")
    text = path.read_text(encoding="utf-8")
    # Baris yang di-comment (mis. opsi Gmail "# SMTP_HOST=...") tetap dihitung
    # terdokumentasi, karena memang sengaja ditawarkan sebagai pilihan.
    return set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]*)=", text, flags=re.MULTILINE))


def test_every_setting_is_documented_in_env_example():
    settings_keys = {name.upper() for name in Settings.model_fields}

    missing = sorted(settings_keys - _documented_keys())

    assert not missing, (
        "Setting ini ada di backend/app/config.py tapi belum ada di .env.example: "
        f"{missing}. Tambahkan lengkap dengan penjelasannya supaya tim tahu setting-nya ada."
    )
