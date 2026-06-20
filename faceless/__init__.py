"""faceless - a tiny engine that turns a JSON story into narrated stick-figure videos.

Pipeline:  story.json  ->  TTS per scene  ->  procedural frames (Pillow)  ->  ffmpeg mp4
Renders the same script to multiple aspect ratios (9:16 Shorts and 16:9 long-form).
"""

__version__ = "0.1.0"
