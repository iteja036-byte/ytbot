"""
ytbot/cut_clips.py
Cuts source_video.mp4 into individual 9:16 clips using timestamps from scenes.json.
Re-encodes each clip (no keyframe misalignment), scales to 1080×1920, keeps audio.
"""

import os
import json
import subprocess

import logger
from config import (
    BASE_DIR, SOURCE_VIDEO, CLIPS_DIR,
    TARGET_W, TARGET_H, TARGET_FPS,
    VIDEO_BITRATE, AUDIO_BITRATE, MAX_CLIPS
)

SCENES_JSON = os.path.join(BASE_DIR, "scenes.json")


def load_scenes() -> tuple[list[float], float]:
    if not os.path.exists(SCENES_JSON):
        logger.die("scenes.json not found. Run find_scenes.py first.")
    with open(SCENES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["timestamps"], data["total_duration"]


def cut_clip(start: float, duration: float, output_path: str) -> bool:
    """
    Cut one clip with re-encode.
    -ss after -i  = frame-accurate (slower but correct)
    scale+crop    = always outputs exact TARGET_W × TARGET_H
    audio kept    = essential for viral content
    """
    scale_filter = (
        f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_W}:{TARGET_H},"
        f"fps={TARGET_FPS}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", SOURCE_VIDEO,
        "-ss", str(start),
        "-t", str(duration),
        "-vf", scale_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-b:v", VIDEO_BITRATE,
        "-c:a", "aac",
        "-b:a", AUDIO_BITRATE,
        "-movflags", "+faststart",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.warn(f"ffmpeg error for {output_path}:\n{result.stderr[-300:]}")
            return False
        if not os.path.exists(output_path) or os.path.getsize(output_path) < 10_000:
            logger.warn(f"Output missing or too small: {output_path}")
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.warn(f"Timeout cutting clip at {start:.2f}s")
        return False


def main():
    if not os.path.exists(SOURCE_VIDEO):
        logger.die("source_video.mp4 not found.")

    timestamps, total_duration = load_scenes()

    os.makedirs(CLIPS_DIR, exist_ok=True)

    # Clear old clips
    for f in os.listdir(CLIPS_DIR):
        if f.endswith(".mp4"):
            os.unlink(os.path.join(CLIPS_DIR, f))

    logger.step(f"Cutting {len(timestamps)} clips…")

    success_count = 0
    pairs = []
    for i in range(len(timestamps)):
        start = timestamps[i]
        end   = timestamps[i + 1] if i + 1 < len(timestamps) else total_duration
        dur   = round(end - start, 3)
        pairs.append((start, dur))

    # Respect MAX_CLIPS cap
    pairs = pairs[:MAX_CLIPS]

    for i, (start, dur) in enumerate(pairs):
        out = os.path.join(CLIPS_DIR, f"clip_{i:02d}.mp4")
        logger.info(f"  Cutting clip_{i:02d}.mp4 @ {start:.2f}s  dur={dur:.2f}s")
        if cut_clip(start, dur, out):
            success_count += 1
        else:
            logger.warn(f"  Skipped clip_{i:02d}.mp4 (cut failed)")

    if success_count == 0:
        logger.die("All clip cuts failed. Check ffmpeg is installed.")

    logger.ok(f"Cut {success_count}/{len(pairs)} clips → {CLIPS_DIR}")
    logger.ok("cut_clips.py — DONE")


if __name__ == "__main__":
    main()

