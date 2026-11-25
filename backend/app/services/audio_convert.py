"""Konversi audio rekaman browser (WebM/Ogg/MP4) ke m4a (AAC).

Ini satu-satunya batas ke ffmpeg. Container backend-api (tempat tes berjalan) tidak
punya ffmpeg, hanya image worker. Panggil lewat atribut modul
(`audio_convert.convert_to_m4a(...)`, bukan `from ... import`) supaya tes bisa
menggantinya dengan konverter palsu lewat monkeypatch.
"""
import subprocess


class AudioConversionError(Exception):
    """Konversi gagal (ffmpeg tidak ada, atau input tidak bisa didekode)."""


def convert_to_m4a(src_path: str, dst_path: str, *, sample_rate: int, bitrate_kbps: int) -> None:
    """Konversi `src_path` ke m4a mono di `dst_path`. Parameter dipilih untuk ucapan,
    bukan musik, agar berkas kecil. Tidak ada timeout sendiri: batas waktu total
    ditegakkan oleh time limit task Celery yang memanggilnya."""
    command = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", src_path,
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-c:a", "aac",
        "-b:a", f"{bitrate_kbps}k",
        dst_path,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise AudioConversionError("ffmpeg tidak ditemukan di server ini.") from exc

    if result.returncode != 0:
        detail = (result.stderr or "").strip()[-500:]
        raise AudioConversionError(f"Konversi audio gagal: {detail or 'ffmpeg keluar dengan kode ' + str(result.returncode)}")
