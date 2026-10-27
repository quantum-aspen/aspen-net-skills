#!/usr/bin/env python3
"""Pull screenshots out of a meeting video with ffmpeg.

  frames.py at <video> <seconds> <out.png>
      The frame showing just before <seconds>. If the screen changed in the
      last 2 s it takes the frame from before that change, since people type
      after they've seen something, and a just-changed slide is usually not
      what they meant (or is still mid-transition).

  frames.py commands <video> <chat.json> <out_dir>
      One candidate frame per `ai:` chat command (see chat.py), using `at`,
      named cmd_<H-MM-SS>.png. Not every command asks for a screenshot;
      whoever reads the commands keeps or drops each frame.
      Writes <out_dir>/commands.json: [{t, at, sender, command, frame}].

  frames.py scenes <video> <play_info.json> <out_dir> [--every 300]
      Frames where the shared screen changes, limited to the screen-share
      ranges in play_info.json (outside them the video shows webcam tiles).
      A burst of changes within 2 s counts once and takes its settled end;
      blank or black frames are dropped; any gap longer than --every seconds
      gets a fallback frame, since slow scrolling never trips the detector.
      Writes <out_dir>/scenes.json: [{t, at, reason, frame}].

<video> is the screen-share-only stream if Zoom recorded one (yt-dlp format
`view_with_share`), else the normal `view` recording. Times are seconds into
the recording, matching chat.py's `t`. Needs ffmpeg on PATH; stdlib only.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCENE_SCAN = 0.06    # whole-video scan; lower picks up cursor moves and webcam noise
SCENE_RECENT = 0.02  # checking a short window for a just-happened change
BURST = 2.0          # changes closer than this are one transition
SETTLE = 1.0         # seconds after a transition before the frame is stable
LOOKBACK = 2.0       # `at`: a change this close before the time means "take the earlier frame"
MIN_CONTRAST = 24    # luma range below this is a blank/black frame
WIDTH = 1280


def hms(t):
    t = int(t)
    return f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}"


def ffmpeg(*args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", *args],
                          capture_output=True, text=True, check=True).stderr


def duration(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(video)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def scene_changes(video, threshold, start=None, length=None):
    """Times (s, absolute) where the scene score exceeds threshold."""
    seek = ["-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-copyts"] if start is not None else []
    log = ffmpeg(*seek, "-i", str(video), "-an",
                 "-vf", f"scale=640:-2,select='gt(scene,{threshold})',showinfo", "-f", "null", "-")
    return [float(x) for x in re.findall(r"pts_time:([\d.]+)", log)]


def grab(video, t, out):
    ffmpeg("-y", "-ss", f"{max(t, 0):.3f}", "-i", str(video), "-frames:v", "1",
           "-vf", f"scale={WIDTH}:-2", str(out))


def contrast(png):
    log = ffmpeg("-i", str(png), "-vf", "signalstats,metadata=print", "-f", "null", "-")
    lo = re.search(r"signalstats\.YLOW=([\d.]+)", log)
    hi = re.search(r"signalstats\.YHIGH=([\d.]+)", log)
    return float(hi.group(1)) - float(lo.group(1)) if lo and hi else 255.0


def stable_time(video, t):
    """The time of the last stable frame at or before t."""
    recent = [c for c in scene_changes(video, SCENE_RECENT, max(t - LOOKBACK, 0), LOOKBACK) if c <= t]
    return min(recent) - 0.5 if recent else t - 0.5


def share_ranges(info, total):
    def secs(s):
        h, m, rest = s.split(":")
        return int(h) * 3600 + int(m) * 60 + float(rest)

    ranges = [(secs(r["startTime"]), secs(r["endTime"]))
              for r in (info.get("vttRanges") or {}).get("share") or []
              if r.get("text", "").startswith("Sharing Started")]
    return ranges or [(0.0, total)]


def cmd_at(a):
    grab(a.video, stable_time(a.video, a.seconds), a.out)
    print(a.out)


def cmd_commands(a):
    a.out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for m in json.loads(a.chat.read_text()):
        if m["command"] is None or m["t"] < 0:
            continue
        png = a.out_dir / f"cmd_{m['at'].replace(':', '-')}.png"
        grab(a.video, stable_time(a.video, m["t"]), png)
        rows.append({**{k: m[k] for k in ("t", "at", "sender", "command")}, "frame": png.name})
    (a.out_dir / "commands.json").write_text(json.dumps(rows, indent=1))
    print(f"{len(rows)} command frames -> {a.out_dir}/commands.json")


def cmd_scenes(a):
    a.out_dir.mkdir(parents=True, exist_ok=True)
    info = json.loads(a.play_info.read_text())
    total = duration(a.video)
    ranges = share_ranges(info, total)

    # one scan of the whole video, then keep changes inside a share range
    changes = [c for c in scene_changes(a.video, SCENE_SCAN)
               if any(s <= c < e for s, e in ranges)]

    picks = []  # (t, reason)
    for s, e in ranges:
        inside = [c for c in changes if s <= c < e]
        bursts = []
        for c in inside:
            if bursts and c - bursts[-1][-1] < BURST:
                bursts[-1].append(c)
            else:
                bursts.append([c])
        times = [(s + SETTLE, "share start")]
        for b in bursts:
            t = min(b[-1] + SETTLE, e - 0.5)
            if t - times[-1][0] < BURST:  # e.g. a change right as sharing starts
                times.pop()
            times.append((t, "scene change"))
        filled = []
        for i, (t, why) in enumerate(times):
            filled.append((t, why))
            nxt = times[i + 1][0] if i + 1 < len(times) else e
            gap = t + a.every
            while gap < nxt - a.every / 2:
                filled.append((gap, "interval"))
                gap += a.every
        picks += filled

    rows = []
    for t, why in picks:
        png = a.out_dir / f"scene_{hms(t).replace(':', '-')}.png"
        grab(a.video, t, png)
        if contrast(png) < MIN_CONTRAST:
            png.unlink()
            continue
        rows.append({"t": round(t, 1), "at": hms(t), "reason": why, "frame": png.name})
    (a.out_dir / "scenes.json").write_text(json.dumps(rows, indent=1))
    print(f"{len(changes)} raw changes in {len(ranges)} share range(s) -> "
          f"{len(rows)} frames -> {a.out_dir}/scenes.json")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("at")
    s.add_argument("video", type=Path)
    s.add_argument("seconds", type=float)
    s.add_argument("out", type=Path)
    s.set_defaults(fn=cmd_at)
    s = sub.add_parser("commands")
    s.add_argument("video", type=Path)
    s.add_argument("chat", type=Path)
    s.add_argument("out_dir", type=Path)
    s.set_defaults(fn=cmd_commands)
    s = sub.add_parser("scenes")
    s.add_argument("video", type=Path)
    s.add_argument("play_info", type=Path)
    s.add_argument("out_dir", type=Path)
    s.add_argument("--every", type=float, default=300.0)
    s.set_defaults(fn=cmd_scenes)
    a = p.parse_args()
    try:
        a.fn(a)
    except subprocess.CalledProcessError as e:
        sys.exit(f"ffmpeg failed: {' '.join(e.cmd)}\n{e.stderr[-2000:]}")


if __name__ == "__main__":
    main()
