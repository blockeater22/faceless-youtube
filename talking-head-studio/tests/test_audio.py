import wave

from studio.audio import wav_duration_seconds


def _write_silent_wav(path, seconds: float, framerate: int = 16000) -> None:
    n_frames = int(seconds * framerate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(b"\x00\x00" * n_frames)


def test_wav_duration_seconds(tmp_path):
    path = tmp_path / "silence.wav"
    _write_silent_wav(path, seconds=2.5)
    assert wav_duration_seconds(path) == 2.5
