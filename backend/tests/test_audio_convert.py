from types import SimpleNamespace

import pytest
from mutagen import File as MutagenFile
from mutagen.mp4 import MP4

from app.services import audio_convert
from app.services.audio_convert import AudioConversionError


def _capture_run(monkeypatch, *, returncode: int = 0, stderr: str = ""):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=returncode, stdout="", stderr=stderr)

    monkeypatch.setattr(audio_convert.subprocess, "run", fake_run)
    return calls


def test_convert_asks_ffmpeg_for_mono_speech_m4a_with_configured_quality(monkeypatch):
    calls = _capture_run(monkeypatch)

    audio_convert.convert_to_m4a("/tmp/in.webm", "/tmp/out.m4a", sample_rate=16000, bitrate_kbps=48)

    command = calls[0]
    assert command[0] == "ffmpeg"
    assert command[command.index("-i") + 1] == "/tmp/in.webm"
    assert command[command.index("-ac") + 1] == "1"
    assert command[command.index("-ar") + 1] == "16000"
    assert command[command.index("-b:a") + 1] == "48k"
    assert command[-1] == "/tmp/out.m4a"


def test_convert_failure_raises_with_ffmpeg_message(monkeypatch):
    _capture_run(monkeypatch, returncode=1, stderr="Invalid data found when processing input")

    with pytest.raises(AudioConversionError) as excinfo:
        audio_convert.convert_to_m4a("/tmp/in.webm", "/tmp/out.m4a", sample_rate=16000, bitrate_kbps=48)

    assert "Invalid data found" in str(excinfo.value)


def test_convert_without_ffmpeg_installed_raises_conversion_error(monkeypatch):
    def missing(command, **kwargs):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(audio_convert.subprocess, "run", missing)

    with pytest.raises(AudioConversionError):
        audio_convert.convert_to_m4a("/tmp/in.webm", "/tmp/out.m4a", sample_rate=16000, bitrate_kbps=48)


def test_fake_converter_writes_an_m4a_that_passes_upload_validation(fake_converter, tmp_path):
    # Aset tiny.m4a harus lolos pemeriksaan yang sama dengan jalur upload
    # (mutagen, tipe MP4, durasi > 0), kalau tidak tes finalize nanti menyesatkan.
    destination = tmp_path / "out.m4a"

    audio_convert.convert_to_m4a(str(tmp_path / "in.webm"), str(destination), sample_rate=16000, bitrate_kbps=48)

    audio = MutagenFile(str(destination))
    assert isinstance(audio, MP4)
    assert audio.info.length > 0
    assert fake_converter.calls == [(str(tmp_path / "in.webm"), str(destination))]


def test_fake_converter_can_be_told_to_fail(fake_converter, tmp_path):
    fake_converter.error = AudioConversionError("konversi gagal")

    with pytest.raises(AudioConversionError, match="konversi gagal"):
        audio_convert.convert_to_m4a(str(tmp_path / "in.webm"), str(tmp_path / "out.m4a"), sample_rate=16000, bitrate_kbps=48)
