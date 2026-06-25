"""
ytbot/brain.py
Content intelligence engine.

Given captions.json (or auto-generated caption bank) and a mood,
produces the optimal caption, hashtag set, and viral score for posting.

Handles all moods: sad, hype, motivation, nostalgia, rage, joy
Returns clean dict safe to pass to upload.py
"""

import os
import json
import random

import logger
from config import BASE_DIR, CAPTIONS_JSON, EMOTION_BOOST, MOODS

BRAIN_OUTPUT = os.path.join(BASE_DIR, "brain_output.json")


# ── Default caption banks (used if captions.json missing) ─────────────────

DEFAULT_CAPTIONS: dict[str, list[dict]] = {
    "sad": [
        {"text": "they left and took the warmth with them 🥀", "emotion": "heartbreak", "intensity": 9.5},
        {"text": "missing someone who doesn't miss you back hurts different 💔", "emotion": "missing-you", "intensity": 8.8},
        {"text": "some goodbyes last forever", "emotion": "sad-love", "intensity": 8.2},
        {"text": "the silence after them is the loudest thing", "emotion": "heartbreak", "intensity": 9.1},
        {"text": "i still check my phone hoping it's you", "emotion": "missing-you", "intensity": 8.5},
    ],
    "hype": [
        {"text": "no cap this is going crazy 🔥", "emotion": "hype", "intensity": 9.3},
        {"text": "the wait is over. era begins NOW 👑", "emotion": "hype", "intensity": 9.6},
        {"text": "this scene STILL lives rent free", "emotion": "hype", "intensity": 8.9},
        {"text": "bro said what we were all thinking 💀", "emotion": "hype", "intensity": 8.7},
    ],
    "motivation": [
        {"text": "you're not tired. you're close. keep going 🏆", "emotion": "motivation", "intensity": 9.4},
        {"text": "the version of you they doubted is loading", "emotion": "motivation", "intensity": 9.7},
        {"text": "rest if you must. but never quit.", "emotion": "motivation", "intensity": 8.6},
        {"text": "main character energy. always.", "emotion": "motivation", "intensity": 8.3},
    ],
    "nostalgia": [
        {"text": "we didn't know those were the good days 🌅", "emotion": "nostalgia", "intensity": 9.0},
        {"text": "some songs teleport you straight back", "emotion": "nostalgia", "intensity": 8.4},
        {"text": "the feeling of that era never left", "emotion": "nostalgia", "intensity": 8.7},
    ],
    "rage": [
        {"text": "nah they really did that 😤", "emotion": "rage", "intensity": 9.2},
        {"text": "at this point it's personal", "emotion": "rage", "intensity": 8.9},
        {"text": "some disrespect cannot go unanswered", "emotion": "rage", "intensity": 9.5},
    ],
    "joy": [
        {"text": "this is the serotonin we deserve 😭✨", "emotion": "joy", "intensity": 8.8},
        {"text": "peak fiction. no notes.", "emotion": "joy", "intensity": 9.1},
        {"text": "the pure happiness in this clip 🥹", "emotion": "joy", "intensity": 8.5},
    ],
}

DEFAULT_HASHTAGS: dict[str, list[str]] = {
    "sad":        ["#heartbreak", "#sadanime", "#animeedit", "#fyp", "#viral", "#sadvibes", "#animelove"],
    "hype":       ["#animeedit", "#fyp", "#viral", "#hype", "#bestscene", "#goated", "#foryou"],
    "motivation": ["#motivation", "#animeedit", "#fyp", "#viral", "#mindset", "#grindset", "#levelup"],
    "nostalgia":  ["#nostalgia", "#animeedit", "#fyp", "#throwback", "#childhood", "#viral", "#anime"],
    "rage":       ["#anime", "#animeedit", "#fyp", "#viral", "#rage", "#noway", "#unhinged"],
    "joy":        ["#anime", "#animeedit", "#fyp", "#viral", "#happy", "#serotonin", "#peak"],
}


# ── Core functions ─────────────────────────────────────────────────────────

def load_captions() -> dict:
    """Load captions.json, fall back to DEFAULT_CAPTIONS if missing."""
    if os.path.exists(CAPTIONS_JSON):
        try:
            with open(CAPTIONS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Loaded captions.json")
            return data
        except (json.JSONDecodeError, KeyError) as e:
            logger.warn(f"captions.json invalid ({e}) — using defaults")
    return DEFAULT_CAPTIONS


def viral_score(caption: dict) -> float:
    """Score a caption for estimated viral potential."""
    boost = EMOTION_BOOST.get(caption.get("emotion", ""), 1.0)
    intensity = float(caption.get("intensity", 5.0))
    return round(intensity * boost, 3)


def select_caption(captions_by_mood: dict, mood: str) -> dict | None:
    """
    Pick the highest-viral-score caption for the given mood.
    Falls back to a random caption from any mood if none found.
    """
    pool = []

    if mood in captions_by_mood:
        pool = captions_by_mood[mood]
    else:
        # Flatten all captions if mood not found
        for v in captions_by_mood.values():
            pool.extend(v)

    if not pool:
        return None

    return max(pool, key=lambda c: viral_score(c))


def select_hashtags(mood: str, extra: list[str] | None = None, limit: int = 7) -> list[str]:
    """Return top hashtags for mood, optionally injecting custom ones."""
    base = DEFAULT_HASHTAGS.get(mood, DEFAULT_HASHTAGS["hype"])
    combined = list(dict.fromkeys(base + (extra or [])))  # deduplicate, preserve order
    return combined[:limit]


def detect_mood_from_context(context: str) -> str:
    """
    Simple keyword-based mood detector for when no mood is passed explicitly.
    """
    context = context.lower()
    mood_keywords = {
        "sad":        ["sad", "heartbreak", "cry", "miss", "lonely", "love", "pain", "tears"],
        "hype":       ["hype", "fire", "crazy", "goat", "best", "epic", "lit", "banger"],
        "motivation": ["motivat", "grind", "hustle", "win", "level up", "goal", "focus"],
        "nostalgia":  ["nostalgic", "throwback", "remember", "old", "childhood", "classic"],
        "rage":       ["rage", "angry", "mad", "furious", "disrespect", "betrayal"],
        "joy":        ["happy", "joy", "funny", "cute", "wholesome", "serotonin", "smile"],
    }
    scores = {mood: 0 for mood in mood_keywords}
    for mood, keywords in mood_keywords.items():
        for kw in keywords:
            if kw in context:
                scores[mood] += 1
    best = max(scores, key=lambda m: scores[m])
    return best if scores[best] > 0 else "hype"


def run(mood: str | None = None, context: str = "") -> dict:
    """
    Main brain function.
    mood: one of MOODS, or None (auto-detect from context)
    context: free text about the video for mood auto-detection

    Returns dict with: caption, emotion, viral_score, hashtags, mood
    """
    data = load_captions()

    if mood is None or mood not in MOODS:
        mood = detect_mood_from_context(context)
        logger.info(f"  Auto-detected mood: {mood}")

    caption = select_caption(data, mood)
    if caption is None:
        logger.warn("No caption found — using emergency fallback")
        caption = {"text": "🔥 this one's different", "emotion": "hype", "intensity": 7.0}

    score  = viral_score(caption)
    tags   = select_hashtags(mood)

    result = {
        "caption":     caption["text"],
        "emotion":     caption.get("emotion", "unknown"),
        "viral_score": score,
        "hashtags":    tags,
        "mood":        mood,
        "hashtag_str": " ".join(tags),
    }

    logger.info(f"  Caption : {result['caption']}")
    logger.info(f"  Emotion : {result['emotion']}  (score: {score})")
    logger.info(f"  Tags    : {result['hashtag_str']}")

    return result


def main():
    logger.step("Running brain…")

    # Try to infer mood from lines.json if present
    from config import LINES_JSON
    context = ""
    mood = None
    if os.path.exists(LINES_JSON):
        try:
            with open(LINES_JSON, "r", encoding="utf-8") as f:
                lines = json.load(f)
            context = " ".join(str(v) for v in lines.values())
            mood    = lines.get("mood") or lines.get("vibe")
        except Exception:
            pass

    result = run(mood=mood, context=context)

    with open(BRAIN_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    logger.ok(f"Saved: brain_output.json")
    logger.ok("brain.py — DONE")


if __name__ == "__main__":
    main()

