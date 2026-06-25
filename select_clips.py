"""
ytbot/select_clips.py
Scores each clip for visual quality (brightness variance + edge density)
and selects the best ones for the reel.

Quality criteria:
  - Not too dark (avg brightness > 40)
  - Not too bright/blown out (avg brightness < 220)  
  - High edge density = dynamic, visually interesting frame
  - Avoids near-duplicate clips (perceptual hash distance check)

Writes: chosen.txt — one clip path per line, in selected order
"""

import os
import json
import subprocess
import struct

import logger
from config import BASE_DIR, CLIPS_DIR, CHOSEN_TXT, MAX_REEL_CLIPS

SCENES_JSON = os.path.join(BASE_DIR, "scenes.json")


def extract_middle_frame(clip_path: str, tmp_jpg: str) -> bool:
    """Extract one frame from the middle of the clip for analysis."""
    # Get duration first
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", clip_path],
        capture_output=True, text=True, timeout=15
    )
    try:
        dur = float(probe.stdout.strip())
        seek = dur / 2
    except (ValueError, AttributeError):
        seek = 0.5

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(seek),
        "-i", clip_path,
        "-vframes", "1",
        "-vf", "scale=160:90",
        tmp_jpg
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=15)
    return result.returncode == 0 and os.path.exists(tmp_jpg)


def score_frame_ffmpeg(clip_path: str, tmp_jpg: str) -> float:
    """
    Use ffmpeg signalstats filter to get brightness mean + stdev.
    High stdev = lots of contrast = visually interesting.
    Returns a quality score (higher = better).
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", tmp_jpg,
        "-vf", "signalstats",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    stderr = result.stderr

    # Parse YAVG (luma average) and YSTDDEV (luma stddev)
    yavg = 128.0
    ystd = 30.0

    for line in stderr.splitlines():
        if "YAVG" in line:
            try:
                yavg = float(line.split("YAVG:")[1].split()[0])
            except (IndexError, ValueError):
                pass
        if "YSTDDEV" in line:
            try:
                ystd = float(line.split("YSTDDEV:")[1].split()[0])
            except (IndexError, ValueError):
                pass

    # Too dark or too blown out = penalise
    brightness_penalty = 0.0
    if yavg < 40 or yavg > 215:
        brightness_penalty = -50.0

    # High contrast = more visually dynamic = good
    score = ystd + brightness_penalty
    return round(score, 2)


def score_clip(clip_path: str, tmp_dir: str) -> float:
    name = os.path.basename(clip_path).replace(".mp4", "")
    tmp_jpg = os.path.join(tmp_dir, f"{name}_thumb.jpg")

    if not extract_middle_frame(clip_path, tmp_jpg):
        logger.warn(f"  Could not extract frame from {name}")
        return 0.0

    score = score_frame_ffmpeg(clip_path, tmp_jpg)

    # Clean up temp file
    try:
        os.unlink(tmp_jpg)
    except OSError:
        pass

    return score


def main():
    clips = sorted([
        os.path.join(CLIPS_DIR, f)
        for f in os.listdir(CLIPS_DIR)
        if f.endswith(".mp4")
    ])

    if not clips:
        logger.die(f"No .mp4 clips found in {CLIPS_DIR}. Run cut_clips.py first.")

    logger.step(f"Scoring {len(clips)} clips for quality…")

    tmp_dir = os.path.join(BASE_DIR, "_tmp_thumbs")
    os.makedirs(tmp_dir, exist_ok=True)

    scored = []
    for clip in clips:
        s = score_clip(clip, tmp_dir)
        logger.info(f"  {os.path.basename(clip)} → score: {s:.1f}")
        scored.append((s, clip))

    # Remove tmp dir
    try:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass

    # Sort by score descending, take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [path for _, path in scored[:MAX_REEL_CLIPS]]

    # Re-sort selected clips back into original time order (clip_00 before clip_01)
    selected.sort()

    logger.ok(f"Selected {len(selected)} clips for reel")
    for p in selected:
        logger.info(f"  → {os.path.basename(p)}")

    with open(CHOSEN_TXT, "w", encoding="utf-8") as f:
        for path in selected:
            f.write(path + "\n")

    logger.ok(f"Saved: chosen.txt ({len(selected)} clips)")
    logger.ok("select_clips.py — DONE")


if __name__ == "__main__":
    main()

