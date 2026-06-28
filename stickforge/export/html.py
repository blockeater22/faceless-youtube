"""Write a self-contained HTML player that animates the SVG frames.

This is the zero-dependency, always-available deliverable: a single .html file
that plays the animation in any browser (no ffmpeg, no rasterizer, no server).
"""
from __future__ import annotations

import json
from pathlib import Path

_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{title}</title>
<style>
  html,body{{margin:0;height:100%;background:#0b0d12;color:#cfd8ea;
    font-family:Helvetica,Arial,sans-serif;}}
  .wrap{{display:flex;flex-direction:column;align-items:center;gap:12px;
    padding:18px;box-sizing:border-box;min-height:100%;}}
  #stage{{max-width:min(96vw,540px);box-shadow:0 10px 40px #0008;border-radius:8px;
    overflow:hidden;background:#0e1320;}}
  #stage svg{{display:block;width:100%;height:auto;}}
  .bar{{display:flex;gap:10px;align-items:center;font-size:14px;}}
  button{{background:#1b2233;color:#cfd8ea;border:1px solid #2c3650;border-radius:6px;
    padding:6px 12px;cursor:pointer;}}
  button:hover{{background:#243048;}}
  input[type=range]{{width:220px;}}
  .meta{{opacity:.6;font-size:12px;}}
</style></head>
<body><div class="wrap">
  <div id="stage"></div>
  <div class="bar">
    <button id="play">⏸ Pause</button>
    <input type="range" id="scrub" min="0" max="{last}" value="0">
    <span class="meta"><span id="cur">0</span>/{count} · {fps} fps</span>
    <label class="meta"><input type="checkbox" id="loop" checked> loop</label>
  </div>
  <div class="meta">{title} — rendered by stickforge</div>
</div>
<script>
const FRAMES = {frames};
const FPS = {fps};
const stage = document.getElementById('stage');
const scrub = document.getElementById('scrub');
const cur = document.getElementById('cur');
const playBtn = document.getElementById('play');
const loopBox = document.getElementById('loop');
let i = 0, playing = true, last = performance.now(), acc = 0;
const step = 1000 / FPS;
function show(n){{ i = n; stage.innerHTML = FRAMES[n]; scrub.value = n; cur.textContent = n; }}
function tick(now){{
  if(playing){{
    acc += now - last;
    while(acc >= step){{
      acc -= step;
      let n = i + 1;
      if(n >= FRAMES.length){{ if(loopBox.checked){{ n = 0; }} else {{ n = FRAMES.length-1; playing=false; playBtn.textContent='▶ Play'; }} }}
      show(n);
    }}
  }}
  last = now;
  requestAnimationFrame(tick);
}}
playBtn.onclick = () => {{ playing = !playing; playBtn.textContent = playing ? '⏸ Pause' : '▶ Play'; }};
scrub.oninput = (e) => {{ playing = false; playBtn.textContent='▶ Play'; show(+e.target.value); }};
show(0);
requestAnimationFrame(tick);
</script>
</body></html>
"""


def write_html_player(frames: list[str], out_path: str | Path,
                      fps: int = 24, title: str = "stickforge") -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    html = _TEMPLATE.format(
        title=title,
        frames=json.dumps(frames),
        fps=fps,
        count=len(frames),
        last=max(0, len(frames) - 1),
    )
    out.write_text(html, encoding="utf-8")
    return out
