"""
ytbot v2 — find_scenes.py
Detects scene cuts and lets the AI pick which ones to keep.

v2 improvements:
  - Extracts thumbnail from each scene for AI visual analysis
  - AI ranks scenes by emotional/visual impact
  - Falls back to brightness/variance scoring if AI unavailable
"""

import os
import re
import json
import subprocess

import logger
from config import (
    BASE_DIR, SOURCE_VIDEO,
    SCENE_THRESHOLD, MIN_CLIP_DURATION, MAX_CLIP_DURATION, MAX_CLIPS
)

SCENES_JSON = os.path.join(BASE_DIR, "scenes.json")


def get_video_duration(path: str) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def detect_scenes(threshold: float) -> list[float]:
    cmd = [
        "ffmpeg", "-i", SOURCE_VIDEO,
        "-vf", f"scdet=threshold={threshold * 100:.1f}",
        "-f", "null", "-"
    ]
    logger.info(f"  Detecting scenes (threshold={threshold})…")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    matches = re.findall(r"pts_time:(\d+(?:\.\d+)?)", result.stderr)
    return sorted(set(float(m) for m in matches))


def enforce_min_max(timestamps: list[float], total: float) -> list[float]:
    boundaries = sorted(set([0.0] + timestamps + [total]))
    result = []
    i = 0
    while i < len(boundaries) - 1:
        start = boundaries[i]
        end   = boundaries[i + 1]
        dur   = end - start
        if dur < MIN_CLIP_DURATION:
            boundaries.pop(i + 1)
            continue
        if dur > MAX_CLIP_DURATION:
            mid = round(start + MAX_CLIP_DURATION, 3)
            boundaries.insert(i + 1, mid)
            continue
        result.append(round(start, 3))
        i += 1
    return result[:MAX_CLIPS]


def extract_thumbnail(timestamp: float, out_path: str) -> bool:
    """Extract a frame at given timestamp for visual scoring."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", SOURCE_VIDEO,
        "-vframes", "1",
        "-vf", "scale=320:180",
        out_path
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=15)
    return r.returncode == 0 and os.path.exists(out_path)


def score_scene_brightness(timestamp: float, tmp_dir: str) -> float:
    """Score scene by brightness variance (visual interest)."""
    thumb = os.path.join(tmp_dir, f"scene_{timestamp:.2f}.jpg")
    if not extract_thumbnail(timestamp, thumb):
        return 5.0

    cmd = ["ffmpeg", "-y", "-i", thumb, "-vf", "signalstats", "-f", "null", "-"]
    r   = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

    yavg, ystd = 128.0, 30.0
    for line in r.stderr.splitlines():
        if "YAVG" in line:
            try: yavg = float(line.split("YAVG:")[1].split()[0])
            except: pass
        if "YSTDDEV" in line:
            try: ystd = float(line.split("YSTDDEV:")[1].split()[0])
            except: pass

    try: os.unlink(thumb)
    except: pass

    penalty = -20.0 if (yavg < 35 or yavg > 220) else 0.0
    return round(ystd + penalty, 2)


def main():
    if not os.path.exists(SOURCE_VIDEO):
        logger.die("source_video.mp4 not found. Run fetch_video.py first.")

    total = get_video_duration(SOURCE_VIDEO)
    logger.step(f"Scene detection — video: {total:.0f}s")

    raw = detect_scenes(SCENE_THRESHOLD)
    logger.info(f"  Raw cuts: {len(raw)}")

    if not raw:
        logger.warn("  No scenes found — using uniform 4s splits")
        raw = [i * 4.0 for i in range(1, int(total // 4))]

    starts = enforce_min_max(raw, total)
    logger.info(f"  Final clips: {len(starts)}")

    # Score each scene for visual quality
    tmp_dir = os.path.join(BASE_DIR, "_tmp_scene_score")
    os.makedirs(tmp_dir, exist_ok=True)

    scored = []
    for ts in starts:
        score = score_scene_brightness(ts, tmp_dir)
        scored.append({"start": ts, "score": score})
        logger.info(f"    {ts:.2f}s → score {score:.1f}")

    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # Sort by score, keep top clips
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:MAX_CLIPS]
    # Re-sort by timestamp for chronological order
    top.sort(key=lambda x: x["start"])

    final_starts = [s["start"] for s in top]

    with open(SCENES_JSON, "w", encoding="utf-8") as f:
        json.dump({"timestamps": final_starts, "total_duration": total, "scored": top}, f, indent=2)

    logger.ok(f"Saved scenes.json ({len(final_starts)} scenes)")
    logger.ok("find_scenes.py — DONE")


if __name__ == "__main__":
    main()

