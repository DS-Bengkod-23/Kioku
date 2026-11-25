from fastapi import HTTPException


class DetailedHTTPException(HTTPException):
    """HTTPException yang membawa field tambahan di body, sejajar `detail`.

    Kontrak error API tetap `{"detail": "<pesan string>"}` (frontend membacanya lewat
    `extractApiError()`); data tambahan seperti `session_id` dikirim sebagai key
    sejajar, bukan di dalam `detail`. Handler-nya ada di main.py."""

    def __init__(self, status_code: int, detail: str, extra: dict):
        super().__init__(status_code=status_code, detail=detail)
        self.extra = extra
