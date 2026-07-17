class MLError(Exception):
    """Base class for ML pipeline errors."""


class PermanentMLError(MLError):
    """Non-retryable: input tidak valid/didukung, error auth/permission/config,
    atau provider menolak request dengan cara yang akan gagal identik kalau
    diulang. Semua yang TIDAK di-raise sebagai ini tetap di jalur default
    (retryable) — kegagalan yang tidak diklasifikasi tetap berperilaku persis
    seperti sekarang."""
