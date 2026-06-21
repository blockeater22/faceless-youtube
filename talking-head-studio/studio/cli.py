from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import StudioConfig
from .pipeline import generate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="studio", description="Generate a talking-head video from a topic.")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate a full video for a topic.")
    gen.add_argument("--face", required=True, type=Path, help="~15s clip of your face (mp4).")
    gen.add_argument("--voice-sample", required=True, type=Path, help="A few seconds of your voice (wav).")
    gen.add_argument("--topic", required=True, help="What the video should be about.")
    gen.add_argument("--seconds", type=int, default=60, help="Target video length in seconds.")
    gen.add_argument("--avatar-engine", choices=["sadtalker", "wav2lip"], default="sadtalker")
    gen.add_argument("--sadtalker-dir", type=Path, default=Path("third_party/SadTalker"))
    gen.add_argument("--wav2lip-dir", type=Path, default=Path("third_party/Wav2Lip"))
    gen.add_argument("--wav2lip-checkpoint", type=Path, default=Path("third_party/Wav2Lip/checkpoints/wav2lip_gan.pth"))
    gen.add_argument("--music", type=Path, default=None)
    gen.add_argument("--logo", type=Path, default=None)
    gen.add_argument("--out-dir", type=Path, default=Path("output"))

    args = parser.parse_args(argv)

    if args.command == "generate":
        config = StudioConfig(target_seconds=args.seconds, out_dir=args.out_dir)
        config.avatar.engine = args.avatar_engine
        config.compose.logo_path = str(args.logo) if args.logo else None

        if not config.anthropic_api_key:
            print("ANTHROPIC_API_KEY is not set.", file=sys.stderr)
            return 1

        final = generate(
            face_video=args.face,
            voice_sample=args.voice_sample,
            topic=args.topic,
            config=config,
            sadtalker_dir=args.sadtalker_dir,
            wav2lip_dir=args.wav2lip_dir,
            wav2lip_checkpoint=args.wav2lip_checkpoint,
            music_path=args.music,
        )
        print(f"done: {final}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
