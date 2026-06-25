"""
ytbot v2 — capsule.py
Generates a context capsule you can paste into a new chat
to continue exactly where you left off.

Run: python capsule.py
Output: capsule.txt — paste this at the start of any new chat
"""

import os
import json
from datetime import datetime

from config import BASE_DIR, MEMORY_FILE, BRAIN_OUTPUT, FINAL_REEL, CLIPS_DIR, OUTPUT_DIR
import memory as mem_module

CAPSULE_FILE = os.path.join(BASE_DIR, "capsule.txt")


def build_capsule() -> str:
    mem        = mem_module.load()
    total_vids = mem.get("total_videos", 0)
    mood_wins  = mem.get("mood_wins", {})
    taste      = mem.get("taste_notes", [])
    runs       = mem.get("runs", [])
    captions   = mem.get("caption_history", [])

    # Best mood
    best_mood = max(mood_wins.items(), key=lambda x: x[1]["avg_score"])[0] if mood_wins else "unknown"

    # Recent runs
    recent = runs[-5:]
    recent_str = "\n".join(
        f'  [{r["mood"]}] "{r["query"]}" → "{r["caption"]}" (score {r["viral_score"]})'
        for r in recent
    ) or "  none yet"

    # Taste notes
    taste_str = "\n".join(f'  - {n["note"]}' for n in taste[-10:]) or "  none yet"

    # Used captions
    used_str = "\n".join(f'  - {c}' for c in captions[-15:]) or "  none"

    # Mistake patterns from Billion
    evals = mem.get("billion_evaluations", [])
    mistake_summary = ""
    if evals:
        all_issues = []
        for ev in evals:
            for m in ev.get("mistakes", []):
                all_issues.extend(m.get("issues", []))
        from collections import Counter
        top = Counter(i.split("—")[0].strip()[:50] for i in all_issues).most_common(5)
        mistake_summary = "\n".join(f"  - {issue} (x{count})" for issue, count in top)
    else:
        mistake_summary = "  none logged yet"

    # Current state
    reel_exists   = os.path.exists(FINAL_REEL)
    clips_count   = len([f for f in os.listdir(CLIPS_DIR) if f.endswith(".mp4")]) if os.path.exists(CLIPS_DIR) else 0

    capsule = f"""════════════════════════════════════════════════════════
YTBOT v2 CONTEXT CAPSULE
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Paste this at the start of a new chat to continue where you left off.
════════════════════════════════════════════════════════

WHAT THIS PROJECT IS
────────────────────
ytbot v2 — a fully automated short-form video bot running on Android (Termux).
It downloads YouTube videos, cuts the best scenes, burns subtitles, and 
generates viral captions using "Billion" — a self-evaluating AI brain that 
scores every caption against 8 quality criteria before outputting anything.
Everything runs offline, no API key needed.

CURRENT STATE
────────────────────
Videos made so far : {total_vids}
Best performing mood: {best_mood}
Final reel exists  : {"yes — output/final_reel.mp4" if reel_exists else "not yet / needs a run"}
Clips in folder    : {clips_count}

EDITOR MEMORY (last 5 runs)
────────────────────
{recent_str}

CAPTIONS ALREADY USED (never repeat these)
────────────────────
{used_str}

TASTE NOTES (what the editor has learned)
────────────────────
{taste_str}

BILLION MISTAKE PATTERNS (what it keeps finding and fixing)
────────────────────
{mistake_summary}

FILE STRUCTURE
────────────────────
~/ytbot/
  main.py          ← entry point
  run.py           ← pipeline orchestrator  
  config.py        ← all settings
  billion.py       ← self-evaluating AI brain (NEW in v2)
  ai_soul.py       ← Claude API brain (needs API key)
  memory.py        ← persistent editor memory
  fetch_video.py   ← YouTube downloader
  find_scenes.py   ← scene detection
  cut_clips.py     ← 9:16 clip cutter
  select_clips.py  ← quality-based clip selector
  clean_srt.py     ← subtitle cleaner
  make_subs.py     ← SRT → ASS subtitle converter
  build_reel.py    ← final reel assembler
  upload.py        ← TikTok/Instagram/YouTube uploader
  validator.py     ← data validation
  logger.py        ← colored logging
  capsule.py       ← this file
  captions.json    ← custom caption bank
  lines.json       ← search query config
  memory/          ← editor_memory.json lives here
  clips/           ← cut clips
  output/          ← final_reel.mp4

HOW TO RUN
────────────────────
cd ~/ytbot
python main.py "anime sad edit" --mood sad --no-upload
python main.py "one piece gear 5" --mood hype --no-upload
python main.py --skip-download --mood motivation --no-upload

# After testing, run with upload:
python main.py "anime emotional" --mood sad

UPLOAD CREDENTIALS NEEDED
────────────────────
export TIKTOK_SESSION_ID="your_session_id"
export INSTAGRAM_USERNAME="your_username"
export INSTAGRAM_PASSWORD="your_password"
# For YouTube: place client_secrets.json in ~/ytbot/

WHAT WAS FIXED FROM V1
────────────────────
- fetch_video: removed subtitle download (was causing 429 errors)
- brain: replaced with Billion — self-evaluates before outputting
- select-scenes: replaced random 8% sampling with brightness scoring
- cut-scene: fixed keyframe misalignment (was using -c copy)  
- run.py: fixed script name mismatch (hyphens vs underscores)
- validator.py: created (was missing, crashed main.py)
- build_reel.py: created (was referenced but never existed)
- upload.py: created with TikTok/Instagram/YouTube support
- config.py: BRAIN_OUTPUT was missing (hot-fix applied)
- All files: consistent naming, no more hyphen/underscore confusion

WHAT TO CONTINUE / IDEAS
────────────────────
- Test a full run and check output/final_reel.mp4 in VLC
- Set ANTHROPIC_API_KEY for live AI captions (costs ~$0.001/run)
- Add more captions to captions.json for your niche
- Tune SCENE_THRESHOLD in config.py if too many/few cuts
- Set upload credentials and run without --no-upload
- Schedule with cron for daily automated posting

════════════════════════════════════════════════════════
END OF CAPSULE — paste everything above into new chat
════════════════════════════════════════════════════════
"""
    return capsule


def main():
    capsule = build_capsule()

    with open(CAPSULE_FILE, "w", encoding="utf-8") as f:
        f.write(capsule)

    print(capsule)
    print(f"\n✅ Saved to: {CAPSULE_FILE}")
    print(f"📋 Copy it with: cat ~/ytbot/capsule.txt")


if __name__ == "__main__":
    main()

