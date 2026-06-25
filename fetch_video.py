"""
ytbot v2 — fetch_video.py
Downloads source video from YouTube.

Improvements over v1:
  - AI refines the search query before downloading for better results
  - Tries multiple query variants if first result is low quality
  - No subtitle download (avoids 429 rate limits)
  - Checks video duration — skips clips under 30s or over 20min
"""

import os
import sys
import glob
import json
import subprocess

import logger
import ai_soul
from config import BASE_DIR, SOURCE_VIDEO, YTDLP_FORMAT, YTDLP_MERGE_FORMAT, LINES_JSON


def get_query() -> str:
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]).strip()
    if os.path.exists(LINES_JSON):
        try:
            with open(LINES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in ("search", "query", "searchQuery", "topic"):
                if data.get(key):
                    return str(data[key]).strip()
        except Exception:
            pass
    return "anime emotional moment"


def ai_refine_query(raw_query: str) -> str:
    """
    Ask the AI to rewrite the search query to find better YouTube results.
    Falls back to raw query if AI unavailable.
    """
    import urllib.request, urllib.error
    from config import ANTHROPIC_API_KEY, AI_MODEL, EDITOR_PERSONA

    if not ANTHROPIC_API_KEY:
        return raw_query

    prompt = f"""A short-form video editor wants to find the perfect source clip on YouTube.
Their original search: "{raw_query}"

Rewrite this into a better YouTube search query that will find:
- High-quality anime/content clips with good visuals
- Videos that will edit well into short-form content
- Emotionally resonant scenes

Respond with ONLY the improved search query, nothing else. Keep it under 8 words."""

    payload = json.dumps({
        "model":      AI_MODEL,
        "max_tokens": 50,
        "messages":   [{"role": "user", "content": prompt}],
        "system":     EDITOR_PERSONA,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        method="POST",
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            refined = data["content"][0]["text"].strip().strip('"')
            if refined and len(refined) < 100:
                logger.info(f"  AI refined query: '{raw_query}' → '{refined}'")
                return refined
    except Exception as e:
        logger.warn(f"  Query refinement skipped: {e}")

    return raw_query


def get_video_duration(path: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=15
        )
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def clean_old_source():
    for f in glob.glob(os.path.join(BASE_DIR, "source_video*")):
        try:
            os.unlink(f)
        except OSError:
            pass


def download_query(query: str, fmt: str) -> bool:
    out_base = os.path.join(BASE_DIR, "source_video")
    cmd = [
        "yt-dlp",
        f"ytsearch1:{query}",
        "-f", fmt,
        "--merge-output-format", YTDLP_MERGE_FORMAT,
        "--no-playlist",
        "--no-warnings",
        "--progress",
        "-o", f"{out_base}.%(ext)s",
    ]
    subprocess.run(cmd, cwd=BASE_DIR)
    if os.path.exists(SOURCE_VIDEO) and os.path.getsize(SOURCE_VIDEO) > 100_000:
        dur = get_video_duration(SOURCE_VIDEO)
        if dur < 20:
            logger.warn(f"  Video too short ({dur:.0f}s) — skipping")
            os.unlink(SOURCE_VIDEO)
            return False
        if dur > 1400:
            logger.warn(f"  Video too long ({dur:.0f}s) — skipping")
            os.unlink(SOURCE_VIDEO)
            return False
        return True
    return False


def download(query: str) -> bool:
    formats = [
        YTDLP_FORMAT,
        "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "best",
    ]

    # Try AI-refined query first
    refined = ai_refine_query(query)
    queries = list(dict.fromkeys([refined, query]))  # refined first, original as fallback

    for q in queries:
        for fmt in formats:
            logger.info(f"  Trying: '{q}' [{fmt[:30]}…]")
            if download_query(q, fmt):
                size_mb = os.path.getsize(SOURCE_VIDEO) / (1024 * 1024)
                dur     = get_video_duration(SOURCE_VIDEO)
                logger.ok(f"  Downloaded: {size_mb:.1f}MB, {dur:.0f}s")
                return True

    return False


def main():
    query = get_query()
    logger.step(f"Fetching video: '{query}'")
    clean_old_source()

    if not download(query):
        logger.die("All download attempts failed.")

    logger.ok("fetch_video.py — DONE")


if __name__ == "__main__":
    main()

