from __future__ import annotations

from pathlib import Path

from saddleback.stages import transcribe


def test_parse_srt_basic(tmp_path: Path):
    srt = tmp_path / "sample.srt"
    srt.write_text(
        """1
00:00:00,000 --> 00:00:02,500
Hello there.

2
00:00:02,500 --> 00:00:05,000
This is a test.
""",
        encoding="utf-8",
    )
    segments = transcribe.parse_srt(srt)
    assert len(segments) == 2
    assert segments[0].text == "Hello there."
    assert segments[0].start == 0.0
    assert segments[0].end == 2.5
    assert segments[1].id == 1
    assert segments[1].text == "This is a test."


def test_find_srt_sidecar(tmp_path: Path):
    src = tmp_path / "video.mp4"
    src.write_bytes(b"fake")
    assert transcribe.find_srt_sidecar(src) is None
    srt = tmp_path / "video.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n", encoding="utf-8")
    found = transcribe.find_srt_sidecar(src)
    assert found == srt
