from studio.captions import build_cues, build_srt, chunk_words, format_timestamp


def test_format_timestamp_basic():
    assert format_timestamp(0) == "00:00:00,000"
    assert format_timestamp(61.5) == "00:01:01,500"
    assert format_timestamp(3661.234) == "01:01:01,234"


def test_chunk_words_splits_on_max():
    words = "one two three four five six seven eight nine ten".split()
    chunks = chunk_words(" ".join(words), max_words=4)
    assert chunks == [
        "one two three four",
        "five six seven eight",
        "nine ten",
    ]


def test_chunk_words_empty_falls_back_to_text():
    assert chunk_words("") == [""]


def test_build_cues_spans_full_duration_per_segment():
    cues = build_cues([("hello there friend", 3.0)])
    assert len(cues) == 1
    assert cues[0].start == 0.0
    assert cues[0].end == 3.0


def test_build_cues_chains_across_segments():
    cues = build_cues([("a b c d e f g h i j", 2.0), ("k l m", 1.0)])
    # first segment: 10 words / 8-word chunks -> 2 cues sharing 2.0s
    assert len(cues) == 3
    assert cues[0].start == 0.0
    assert cues[-1].end == 3.0


def test_build_srt_format():
    srt = build_srt([("hi", 1.0)])
    assert srt.startswith("1\n00:00:00,000 --> 00:00:01,000\nhi")
