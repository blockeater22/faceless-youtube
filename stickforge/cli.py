"""Command-line interface for stickforge.

    python -m stickforge demo                 # render the showcase animation
    python -m stickforge showcase             # expression contact sheet
    python -m stickforge assets --search wave # browse the asset library
    python -m stickforge poses                # list available poses
    python -m stickforge build project.json   # render a scene/timeline spec
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .render.config import RenderConfig, RESOLUTIONS


def _export(target, out_dir: str, name: str, fmt: str, fps: int,
            backend: str = "illustrated") -> None:
    from .export.frames import render_frames
    from .export.html import write_html_player
    from .export.video import write_video, VideoUnavailable

    cfg = RenderConfig.for_format(fmt)
    print(f"rendering {name} @ {cfg.width}x{cfg.height}, {fps} fps "
          f"({target.duration:.1f}s, {backend})...")
    frames = render_frames(target, cfg, fps, backend=backend)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    html = write_html_player(frames, out / f"{name}.html", fps=fps, title=name)
    print(f"  HTML player -> {html}  ({html.stat().st_size/1e6:.1f} MB, "
          f"{len(frames)} frames)")
    try:
        mp4 = write_video(frames, out / f"{name}.mp4", fps=fps)
        print(f"  MP4 -> {mp4}  ({mp4.stat().st_size/1e6:.1f} MB)")
    except VideoUnavailable as e:
        print(f"  (MP4 skipped: {e})")


def _demo(args) -> int:
    from .studio import build_demo_timeline
    _export(build_demo_timeline(), args.out, "demo", args.format, args.fps, args.backend)
    return 0


def _showcase(args) -> int:
    from .studio import build_expression_showcase
    _export(build_expression_showcase(), args.out, "showcase",
            args.format, args.fps, args.backend)
    return 0


def _lab(args) -> int:
    from .studio import build_character_lab
    _export(build_character_lab(), args.out, "character_lab",
            args.format, args.fps, args.backend)
    return 0


def _cast(args) -> int:
    from .studio import build_cast
    _export(build_cast(), args.out, "cast", args.format, args.fps, args.backend)
    return 0


def _silhouettes(args) -> int:
    from .studio import build_silhouette_test
    from .export.frames import render_frames
    from .export.html import write_html_player
    cfg = RenderConfig.for_format(args.format)
    frames = render_frames(build_silhouette_test(), cfg, 1,
                           backend="illustrated", silhouette=True)
    from pathlib import Path
    Path(args.out).mkdir(parents=True, exist_ok=True)
    html = write_html_player(frames, Path(args.out) / "silhouettes.html", 1, "silhouettes")
    print(f"  silhouette test -> {html}")
    return 0


def _acting(args) -> int:
    from .studio import build_acting_demo
    _export(build_acting_demo(args.actor), args.out, "acting",
            args.format, args.fps, args.backend)
    return 0


def _assets(args) -> int:
    from .studio import load_core_library
    lib = load_core_library()
    results = lib.search(args.search or "", type=args.type,
                         tags=args.tags.split(",") if args.tags else None)
    print(f"{len(results)} asset(s):")
    for a in results:
        print(f"  {a.id:24s} [{a.type:11s}] {a.name:16s} "
              f"tags={','.join(a.tags)}")
    return 0


def _poses(args) -> int:
    from .pose.pose import POSES
    from .studio import load_core_library
    load_core_library()
    print("poses:", ", ".join(POSES.names()))
    return 0


def _expressions(args) -> int:
    from .expression.expression import EXPRESSIONS
    from .studio import load_core_library
    load_core_library()
    print("expressions:", ", ".join(EXPRESSIONS.names()))
    return 0


def _build(args) -> int:
    from .studio import load_core_library, register_library_assets
    from .assets.library import AssetLibrary
    from .scene.scene import Scene, Timeline

    spec = json.loads(Path(args.project).read_text(encoding="utf-8"))
    lib = load_core_library()
    for pack in spec.get("packs", []):
        lib.load_pack_file(pack, overwrite=True)
    register_library_assets(lib)

    fmt = spec.get("format", args.format)
    fps = spec.get("fps", args.fps)
    name = spec.get("name", Path(args.project).stem)

    scene_specs = spec.get("timeline") or [spec.get("scene", {})]
    scenes = [Scene.from_spec(s, lib) for s in scene_specs]
    target = Timeline(scenes=scenes) if len(scenes) > 1 else scenes[0]
    _export(target, args.out, name, fmt, fps, spec.get("backend", args.backend))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="stickforge",
                                description="modular stickman animation platform")
    p.add_argument("--out", default="output/stickforge", help="output directory")
    p.add_argument("--format", default="9:16", choices=list(RESOLUTIONS),
                   help="output resolution")
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--backend", default="illustrated",
                   help="renderer: illustrated (default) | svg (legacy line art)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("demo", help="render the showcase animation").set_defaults(fn=_demo)
    sub.add_parser("showcase", help="render the expression contact sheet").set_defaults(fn=_showcase)
    sub.add_parser("lab", help="render the character lab (recombination lineup)").set_defaults(fn=_lab)
    sub.add_parser("cast", help="render the personality-first archetype cast").set_defaults(fn=_cast)
    sub.add_parser("silhouettes", help="render the silhouette readability test").set_defaults(fn=_silhouettes)

    ac = sub.add_parser("acting", help="render an actor performing emotions")
    ac.add_argument("--actor", default="actor.max")
    ac.set_defaults(fn=_acting)

    a = sub.add_parser("assets", help="browse the asset library")
    a.add_argument("--search", default="")
    a.add_argument("--type", default=None)
    a.add_argument("--tags", default=None, help="comma-separated required tags")
    a.set_defaults(fn=_assets)

    sub.add_parser("poses", help="list poses").set_defaults(fn=_poses)
    sub.add_parser("expressions", help="list expressions").set_defaults(fn=_expressions)

    b = sub.add_parser("build", help="render a project JSON (scene or timeline)")
    b.add_argument("project")
    b.set_defaults(fn=_build)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
