"""
ytbot/build_reel.py
Assembles the final vertical reel from chosen.txt clips.

Strategy:
  - Reads clip paths from chosen.txt (time-ordered, quality-filtered)
  - Applies ramping durations (long → short) for viral fast-cut feel
  - Burns in subtitles from subs.ass if available
  - Outputs final_reel.mp4 to output/

Uses ffmpeg concat demuxer (no re-encode quality loss on concat).
Each clip was already encoded to 1080×1920 by cut_clips.py so concat
is fast and lossless.
"""

import os
import json
import subprocess
import tempfile

import logger
from config import (
    BASE_DIR, CHOSEN_TXT, SUBS_ASS, FINAL_REEL, OUTPUT_DIR,
    TARGET_W, TARGET_H, TARGET_FPS,
    VIDEO_BITRATE, AUDIO_BITRATE,
    REEL_DURATIONS, MAX_REEL_CLIPS
)


def load_chosen_clips() -> list[str]:
    if not os.path.exists(CHOSEN_TXT):
        logger.die("chosen.txt not found. Run select_clips.py first.")
    with open(CHOSEN_TXT, "r", encoding="utf-8") as f:
        paths = [line.strip() for line in f if line.strip()]
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        for m in missing:
            logger.warn(f"  Missing clip (skipped): {m}")
        paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        logger.die("No valid clips in chosen.txt")
    return paths[:MAX_REEL_CLIPS]


def trim_clip_to_duration(clip_path: str, duration: float, out_path: str) -> bool:
    """
    Trim a clip to the target duration for the reel.
    Takes from the beginning of the clip.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", clip_path,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast",
        "-b:v", VIDEO_BITRATE,
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        "-r", str(TARGET_FPS),
        "-movflags", "+faststart",
        out_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.warn(f"  Trim failed for {os.path.basename(clip_path)}:\n{result.stderr[-200:]}")
        return False
    return os.path.exists(out_path) and os.path.getsize(out_path) > 5000


def build_concat_list(trimmed_clips: list[str], tmp_dir: str) -> str:
    """Write ffmpeg concat demuxer list file."""
    list_path = os.path.join(tmp_dir, "concat_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for clip in trimmed_clips:
            # ffmpeg concat requires absolute paths with forward slashes
            safe_path = clip.replace("\\", "/")
            f.write(f"file '{safe_path}'\n")
    return list_path


def concat_clips(list_path: str, output: str, burn_subs: bool) -> bool:
    """Concatenate all trimmed clips into one video."""

    if burn_subs and os.path.exists(SUBS_ASS):
        # Concat + burn subtitles in one pass
        logger.info("  Burning subtitles into reel…")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-vf", f"ass={SUBS_ASS}",
            "-c:v", "libx264", "-preset", "fast",
            "-b:v", VIDEO_BITRATE,
            "-c:a", "aac", "-b:a", AUDIO_BITRATE,
            "-movflags", "+faststart",
            output
        ]
    else:
        # Stream copy (fastest, no quality loss)
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            "-movflags", "+faststart",
            output
        ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        logger.warn(f"  Concat failed:\n{result.stderr[-400:]}")
        return False
    return os.path.exists(output) and os.path.getsize(output) > 50_000


def get_clip_duration(path: str) -> float:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, timeout=15
    )
    try:
        return float(probe.stdout.strip())
    except ValueError:
        return 999.0


def main():
    logger.step("Building final reel…")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    clips = load_chosen_clips()
    logger.info(f"  {len(clips)} clips loaded")

    tmp_dir = os.path.join(BASE_DIR, "_tmp_reel")
    os.makedirs(tmp_dir, exist_ok=True)

    trimmed = []
    for i, clip_path in enumerate(clips):
        target_dur = REEL_DURATIONS[i] if i < len(REEL_DURATIONS) else 0.2

        # Don't try to use more duration than clip actually has
        actual_dur = get_clip_duration(clip_path)
        target_dur = min(target_dur, actual_dur)

        out_path = os.path.join(tmp_dir, f"reel_{i:02d}.mp4")
        logger.info(f"  Trimming clip_{i:02d} → {target_dur:.2f}s")

        if trim_clip_to_duration(clip_path, target_dur, out_path):
            trimmed.append(out_path)
        else:
            logger.warn(f"  Skipping clip_{i:02d} (trim failed)")

    if not trimmed:
        logger.die("All clip trims failed — cannot build reel")

    logger.info(f"  {len(trimmed)} clips trimmed, concatenating…")

    list_path = build_concat_list(trimmed, tmp_dir)
    burn_subs = os.path.exists(SUBS_ASS)

    success = concat_clips(list_path, FINAL_REEL, burn_subs)

    # Cleanup tmp
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if not success:
        logger.die("Reel concat failed")

    size_mb = os.path.getsize(FINAL_REEL) / (1024 * 1024)
    logger.ok(f"Final reel: {FINAL_REEL} ({size_mb:.1f} MB)")
    logger.ok("build_reel.py — DONE")


if __name__ == "__main__":
    main()

