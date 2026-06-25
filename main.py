"""
ytbot v2 — main.py
Entry point. Runs preflight checks then launches AI pipeline.
"""

import os
import sys
import subprocess

import logger
from config import CAPTIONS_JSON, ANTHROPIC_API_KEY, MEMORY_FILE
from validator import validate_and_fix


def preflight():
    logger.step("Pre-flight checks")

    # captions.json
    if os.path.exists(CAPTIONS_JSON):
        data = validate_and_fix(CAPTIONS_JSON)
        if data:
            total = sum(len(v) for v in data.values())
            logger.ok(f"captions.json: {total} captions across {len(data)} moods")
    else:
        logger.info("captions.json not found — using built-in caption bank")

    # ffmpeg
    r = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    if r.returncode != 0:
        logger.die("ffmpeg not found. Install: pkg install ffmpeg")
    logger.ok("ffmpeg: ready")

    # yt-dlp
    r = subprocess.run(["yt-dlp", "--version"], capture_output=True)
    if r.returncode != 0:
        logger.warn("yt-dlp not found. Install: pip install yt-dlp")
    else:
        logger.ok("yt-dlp: ready")

    # AI soul status
    if ANTHROPIC_API_KEY:
        logger.ok("🧠 AI soul: active (Claude API connected)")
    else:
        logger.warn("🧠 AI soul: offline mode (set ANTHROPIC_API_KEY to enable)")
        logger.info("  export ANTHROPIC_API_KEY='sk-ant-...'")

    # Memory
    import memory
    mem = memory.load()
    total_vids = mem.get("total_videos", 0)
    if total_vids > 0:
        logger.ok(f"📼 Memory: {total_vids} videos in editor history")
    else:
        logger.info("📼 Memory: fresh start (no history yet)")

    logger.ok("Pre-flight complete\n")


def main():
    preflight()
    import run
    run.main()


if __name__ == "__main__":
    main()

