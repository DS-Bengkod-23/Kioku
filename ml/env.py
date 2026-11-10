import os


def require_env(name: str) -> str:
    """Baca setting dari environment tanpa default.

    Nilai default hidup di satu tempat saja: backend/app/config.py. Di worker, nilainya
    disalin dari sana ke os.environ (lihat tasks/process_recording.py); untuk
    ml/evaluation/evaluate.py nilainya datang dari .env lewat load_dotenv. Kalau kosong,
    gagal dengan pesan yang jelas daripada diam-diam memakai angka tersembunyi.
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} tidak ditemukan di environment (isi di .env)")
    return value
