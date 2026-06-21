from pathlib import Path

from studio import compose
from studio.config import ComposeConfig


def test_build_normalize_cmd_includes_resolution_and_fps():
    cfg = ComposeConfig(resolution=(1280, 720), fps=24)
    cmd = compose.build_normalize_cmd(Path("in.mp4"), Path("out.mp4"), cfg)
    joined = " ".join(cmd)
    assert "scale=1280:720" in joined
    assert "fps=24" in joined
    assert cmd[0] == "ffmpeg"
    assert cmd[-1] == "out.mp4"


def test_build_concat_cmd_uses_concat_demuxer():
    cmd = compose.build_concat_cmd(Path("list.txt"), Path("out.mp4"))
    assert "-f" in cmd and "concat" in cmd
    assert str(Path("list.txt")) in cmd


def test_write_concat_list_quotes_resolved_paths(tmp_path):
    clips = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
    for c in clips:
        c.touch()
    list_path = compose.write_concat_list(clips, tmp_path / "concat.txt")
    content = list_path.read_text()
    assert content.count("file '") == 2
    assert str(clips[0].resolve()) in content


def test_build_caption_burn_cmd_references_srt():
    cfg = ComposeConfig()
    cmd = compose.build_caption_burn_cmd(Path("in.mp4"), Path("cap.srt"), Path("out.mp4"), cfg)
    joined = " ".join(cmd)
    assert "subtitles=cap.srt" in joined


def test_build_music_mix_cmd_uses_amix():
    cfg = ComposeConfig(music_volume_db=-20.0)
    cmd = compose.build_music_mix_cmd(Path("in.mp4"), Path("music.mp3"), Path("out.mp4"), cfg)
    joined = " ".join(cmd)
    assert "amix=inputs=2" in joined
    assert "volume=-20.0dB" in joined


def test_build_logo_overlay_cmd_positions_top_right():
    cmd = compose.build_logo_overlay_cmd(Path("in.mp4"), Path("logo.png"), Path("out.mp4"))
    assert "overlay=W-w-30:30" in " ".join(cmd)
