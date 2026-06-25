"""
ytbot v2 — memory.py
The editor remembers everything.

Tracks across runs:
  - What queries were searched
  - What moods performed best
  - Which captions were used
  - What the AI said about each video
  - A running "taste profile" that evolves over time

This makes the bot smarter with every video it makes.
"""

import os
import json
from datetime import datetime

from config import MEMORY_DIR, MEMORY_FILE

os.makedirs(MEMORY_DIR, exist_ok=True)


def load() -> dict:
    """Load editor memory from disk. Returns empty structure if missing."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "runs": [],
        "mood_wins": {},
        "caption_history": [],
        "taste_notes": [],
        "total_videos": 0,
    }


def save(mem: dict):
    """Save editor memory to disk."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2, ensure_ascii=False)


def record_run(query: str, mood: str, caption: str, ai_thoughts: str, viral_score: float):
    """Log a completed run into memory."""
    mem = load()

    run = {
        "timestamp": datetime.now().isoformat(),
        "query":     query,
        "mood":      mood,
        "caption":   caption,
        "viral_score": viral_score,
        "ai_thoughts": ai_thoughts,
    }

    mem["runs"].append(run)
    mem["total_videos"] = len(mem["runs"])

    # Track mood performance
    if mood not in mem["mood_wins"]:
        mem["mood_wins"][mood] = {"count": 0, "avg_score": 0.0}
    old = mem["mood_wins"][mood]
    n   = old["count"] + 1
    mem["mood_wins"][mood] = {
        "count":     n,
        "avg_score": round((old["avg_score"] * (n - 1) + viral_score) / n, 3)
    }

    # Caption history (avoid repeating)
    if caption not in mem["caption_history"]:
        mem["caption_history"].append(caption)
    # Keep last 50
    mem["caption_history"] = mem["caption_history"][-50:]

    save(mem)
    return mem


def get_context_for_ai() -> str:
    """
    Build a context string for the AI about what the editor has done before.
    Injected into every AI prompt so it learns from history.
    """
    mem = load()
    if not mem["runs"]:
        return "This is your first video. Make it count."

    total  = mem["total_videos"]
    recent = mem["runs"][-3:]  # last 3 runs

    # Best mood
    best_mood = max(
        mem["mood_wins"].items(),
        key=lambda x: x[1]["avg_score"]
    )[0] if mem["mood_wins"] else "unknown"

    recent_lines = []
    for r in recent:
        recent_lines.append(f'  - "{r["query"]}" ({r["mood"]}) → "{r["caption"]}"')

    used_captions = mem["caption_history"][-10:]

    return f"""You've made {total} videos before this one.
Your best-performing mood so far: {best_mood}
Your last 3 videos:
{chr(10).join(recent_lines)}
Captions you've already used (don't repeat these):
  {', '.join(f'"{c}"' for c in used_captions)}
Build on what worked. Avoid what didn't. Evolve your style."""


def add_taste_note(note: str):
    """Add a creative taste note to memory (AI can call this)."""
    mem = load()
    mem["taste_notes"].append({
        "timestamp": datetime.now().isoformat(),
        "note": note
    })
    mem["taste_notes"] = mem["taste_notes"][-20:]
    save(mem)


def get_taste_notes() -> list[str]:
    mem = load()
    return [n["note"] for n in mem.get("taste_notes", [])]

