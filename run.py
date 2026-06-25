"""
ytbot v2 — run.py
Master pipeline. Uses Billion (self-evaluating AI brain).

Usage:
  python run.py "anime sad edit" --mood sad --no-upload
  python run.py "one piece gear 5" --mood hype
  python run.py --skip-download --mood motivation
  python run.py "naruto" --threshold 0.25
"""

import os
import sys
import time
import json
import argparse

import logger
from config import SOURCE_VIDEO, FINAL_REEL, MOODS, BRAIN_OUTPUT, CLIPS_DIR


def parse_args():
    p = argparse.ArgumentParser(description="ytbot v2 — Billion AI pipeline")
    p.add_argument("query", nargs="*", help="YouTube search query")
    p.add_argument("--mood", choices=MOODS, default=None)
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("--no-upload", action="store_true")
    p.add_argument("--threshold", type=float, default=None)
    return p.parse_args()


def run_step(name: str, fn, fatal: bool = True) -> bool:
    t0 = time.time()
    logger.step(f"[{name}]")
    try:
        fn()
        logger.ok(f"{name} — {time.time()-t0:.1f}s")
        return True
    except SystemExit as e:
        logger.err(f"{name} exited: {e.code}")
        if fatal: raise
        return False
    except Exception as e:
        import traceback
        logger.err(f"{name} error: {e}")
        traceback.print_exc()
        if fatal: raise
        return False


def emergency_brain(query: str, mood: str):
    data = {
        "caption":     "🔥 this edit goes crazy",
        "emotion":     "hype",
        "viral_score": 7.0,
        "hashtags":    ["#fyp", "#viral", "#animeedit", "#foryou"],
        "mood":        mood,
        "hashtag_str": "#fyp #viral #animeedit #foryou",
        "thought":     "",
        "ai_powered":  False,
        "billion":     False,
    }
    with open(BRAIN_OUTPUT, "w") as f:
        json.dump(data, f)


def main():
    args  = parse_args()
    query = " ".join(args.query).strip() if args.query else ""
    mood  = args.mood

    if args.threshold:
        import config
        config.SCENE_THRESHOLD = args.threshold

    logger.step("🔥 ytbot v2 — Billion pipeline starting")
    t_start = time.time()

    sys.argv = [sys.argv[0]] + (args.query or [])

    # ── 1. Download ───────────────────────────────────────────
    if args.skip_download:
        if not os.path.exists(SOURCE_VIDEO):
            logger.die("--skip-download: source_video.mp4 not found")
        logger.info("⏭  Skipping download")
    else:
        import fetch_video
        run_step("fetch_video", fetch_video.main, fatal=True)

    # ── 2. Scene detection ────────────────────────────────────
    import find_scenes
    run_step("find_scenes", find_scenes.main, fatal=True)

    # ── 3. Cut clips ──────────────────────────────────────────
    import cut_clips
    run_step("cut_clips", cut_clips.main, fatal=True)

    # ── 4. Select best clips ──────────────────────────────────
    import select_clips
    run_step("select_clips", select_clips.main, fatal=True)

    # ── 5. Clean subtitles (non-fatal) ────────────────────────
    import clean_srt
    run_step("clean_srt", clean_srt.main, fatal=False)

    # ── 6. Build ASS subs (non-fatal) ─────────────────────────
    import make_subs
    run_step("make_subs", make_subs.main, fatal=False)

    # ── 7. Billion brain ──────────────────────────────────────
    import billion
    clip_count = len([f for f in os.listdir(CLIPS_DIR) if f.endswith(".mp4")]) if os.path.exists(CLIPS_DIR) else 0

    def run_billion():
        billion.run(query=query, mood=mood, clip_count=clip_count)

    if not run_step("billion", run_billion, fatal=False):
        logger.warn("Billion failed — writing emergency brain output")
        emergency_brain(query, mood or "hype")

    # ── 8. Build reel ─────────────────────────────────────────
    import build_reel
    run_step("build_reel", build_reel.main, fatal=True)

    # ── 9. Upload ─────────────────────────────────────────────
    if args.no_upload:
        logger.info("⏭  Skipping upload")
    else:
        import upload
        run_step("upload", upload.main, fatal=False)

    # ── Summary ───────────────────────────────────────────────
    elapsed = time.time() - t_start
    logger.step(f"Pipeline done in {elapsed:.0f}s")

    if os.path.exists(FINAL_REEL):
        size = os.path.getsize(FINAL_REEL) / (1024 * 1024)
        logger.ok(f"🎬 final_reel.mp4 — {size:.1f}MB")
        logger.ok(f"📱 Copy to downloads: cp {FINAL_REEL} ~/storage/downloads/final_reel.mp4")

        if os.path.exists(BRAIN_OUTPUT):
            with open(BRAIN_OUTPUT) as f:
                brain = json.load(f)
            tag = "🧠 Billion" if brain.get("billion") else "📋 offline"
            print(f"\n  {tag}")
            print(f"  caption : {brain['caption']}")
            print(f"  tags    : {brain['hashtag_str']}")
            if brain.get("thought"):
                print(f"  thought : {brain['thought']}")
    else:
        logger.die("final_reel.mp4 not found")


if __name__ == "__main__":
    main()

