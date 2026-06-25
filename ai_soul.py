"""
ytbot v2 — ai_soul.py
The AI creative brain. Powered by Claude.

This replaces the old static caption picker with genuine creative intelligence.
The AI thinks about the video, feels the mood, writes original captions,
picks hashtags strategically, and explains its creative decisions.

It also learns — memory context is injected every call so it evolves over time.

Works in two modes:
  1. API mode   — calls Claude API directly (needs ANTHROPIC_API_KEY)
  2. Offline mode — falls back to scored caption bank (original brain.py logic)
"""

import os
import json
import re
import urllib.request
import urllib.error

import logger
import memory as mem_module
from config import (
    ANTHROPIC_API_KEY, AI_MODEL, AI_MAX_TOKENS,
    EDITOR_PERSONA, CAPTIONS_JSON, EMOTION_BOOST, MOODS,
    BASE_DIR
)


# ── Offline fallback caption banks ────────────────────────────────────────

FALLBACK_CAPTIONS = {
    "sad": [
        {"text": "they left and took the warmth with them 🥀", "emotion": "heartbreak", "intensity": 9.5},
        {"text": "missing someone who doesn't miss you back hurts different 💔", "emotion": "missing-you", "intensity": 8.8},
        {"text": "the silence after them is the loudest thing", "emotion": "heartbreak", "intensity": 9.1},
        {"text": "some goodbyes last forever", "emotion": "sad-love", "intensity": 8.2},
        {"text": "i still check my phone hoping it's you", "emotion": "missing-you", "intensity": 8.5},
        {"text": "loving someone who's already gone 💔", "emotion": "sad-love", "intensity": 8.9},
    ],
    "hype": [
        {"text": "no cap this is going crazy 🔥", "emotion": "hype", "intensity": 9.3},
        {"text": "the wait is over. era begins NOW 👑", "emotion": "hype", "intensity": 9.6},
        {"text": "this scene STILL lives rent free 💀", "emotion": "hype", "intensity": 8.9},
        {"text": "peak fiction. no notes.", "emotion": "hype", "intensity": 9.4},
        {"text": "the internet cannot handle this 🔥", "emotion": "hype", "intensity": 9.1},
    ],
    "motivation": [
        {"text": "you're not tired. you're close. keep going 🏆", "emotion": "motivation", "intensity": 9.4},
        {"text": "the version of you they doubted is loading ⚡", "emotion": "motivation", "intensity": 9.7},
        {"text": "they slept on you. stay quiet. let the results talk.", "emotion": "motivation", "intensity": 9.5},
        {"text": "main character energy. always.", "emotion": "motivation", "intensity": 8.3},
    ],
    "nostalgia": [
        {"text": "we didn't know those were the good days 🌅", "emotion": "nostalgia", "intensity": 9.0},
        {"text": "the feeling of that era never left", "emotion": "nostalgia", "intensity": 8.7},
        {"text": "some memories hit different at 2am", "emotion": "nostalgia", "intensity": 8.9},
    ],
    "rage": [
        {"text": "nah they really did that 😤", "emotion": "rage", "intensity": 9.2},
        {"text": "some disrespect cannot go unanswered 😤", "emotion": "rage", "intensity": 9.5},
        {"text": "the audacity is actually insane", "emotion": "rage", "intensity": 9.0},
    ],
    "joy": [
        {"text": "this is the serotonin we deserve 😭✨", "emotion": "joy", "intensity": 8.8},
        {"text": "this scene fixed something in me 🌸", "emotion": "joy", "intensity": 9.0},
        {"text": "certified serotonin boost 🌞", "emotion": "joy", "intensity": 8.4},
    ],
}

FALLBACK_HASHTAGS = {
    "sad":        ["#heartbreak", "#sadanime", "#animeedit", "#fyp", "#viral", "#sadvibes", "#animelove"],
    "hype":       ["#animeedit", "#fyp", "#viral", "#hype", "#bestscene", "#goated", "#foryou"],
    "motivation": ["#motivation", "#animeedit", "#fyp", "#viral", "#mindset", "#grindset", "#levelup"],
    "nostalgia":  ["#nostalgia", "#animeedit", "#fyp", "#throwback", "#childhood", "#viral", "#anime"],
    "rage":       ["#anime", "#animeedit", "#fyp", "#viral", "#rage", "#noway", "#unhinged"],
    "joy":        ["#anime", "#animeedit", "#fyp", "#viral", "#happy", "#serotonin", "#peak"],
}


# ── Claude API call ────────────────────────────────────────────────────────

def call_claude(prompt: str) -> str | None:
    """
    Call Claude API. Returns response text or None on failure.
    Works in Termux (pure stdlib urllib, no httpx/requests needed).
    """
    api_key = ANTHROPIC_API_KEY
    if not api_key:
        return None

    payload = json.dumps({
        "model":      AI_MODEL,
        "max_tokens": AI_MAX_TOKENS,
        "messages":   [{"role": "user", "content": prompt}],
        "system":     EDITOR_PERSONA,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        method="POST",
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        logger.warn(f"Claude API HTTP error {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        logger.warn(f"Claude API error: {e}")
        return None


def parse_ai_response(text: str) -> dict | None:
    """
    Parse JSON from Claude's response.
    Claude is instructed to return JSON — strip any markdown fences first.
    """
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find a JSON block inside the text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None


# ── AI think function ──────────────────────────────────────────────────────

def think(query: str, mood: str, clip_count: int = 0) -> dict:
    """
    The core AI creative decision. Claude thinks about the video and decides:
      - The perfect caption (original, written for THIS video)
      - The best hashtags (strategic, not just popular)
      - Its emotional read on the content
      - Creative notes for the editor's memory

    Falls back to offline scoring if API unavailable.
    """
    history_context = mem_module.get_context_for_ai()
    taste_notes     = mem_module.get_taste_notes()
    taste_str       = "\n".join(f"  - {n}" for n in taste_notes) if taste_notes else "  none yet"

    # Load any existing captions to avoid
    used = mem_module.load().get("caption_history", [])[-15:]
    used_str = "\n".join(f'  - "{c}"' for c in used) if used else "  none"

    prompt = f"""You are editing a short-form viral video.

VIDEO SEARCH QUERY: "{query}"
MOOD: {mood}
CLIPS FOUND: {clip_count} scene cuts detected

YOUR EDITOR HISTORY:
{history_context}

YOUR TASTE NOTES:
{taste_str}

CAPTIONS YOU ALREADY USED (never repeat these):
{used_str}

YOUR JOB:
Write ONE perfect caption for this video. It should feel real, emotional, and stop someone mid-scroll.
Then pick 7 hashtags that will maximize reach for this specific content.
Then write a short "thought" — your honest inner monologue about this video (1-2 sentences, raw).
Then if you learned anything creative from this that future you should remember, add a taste_note.

RULES:
- Caption must be original — not from your history
- Write lowercase, no corporate energy
- Hashtags must include #fyp and #viral plus 5 relevant ones
- Your "thought" is honest, not promotional
- Respond ONLY with valid JSON, no other text

RESPOND WITH THIS EXACT JSON FORMAT:
{{
  "caption": "your caption here",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#fyp", "#viral"],
  "emotion": "the core emotion (one word)",
  "thought": "your honest inner monologue about this video",
  "taste_note": "something you learned about editing to remember (or null)",
  "confidence": 0.95
}}"""

    logger.info("  🧠 AI is thinking…")
    raw = call_claude(prompt)

    if raw:
        parsed = parse_ai_response(raw)
        if parsed and parsed.get("caption") and parsed.get("hashtags"):
            logger.ok(f"  🧠 AI thought: {parsed.get('thought', '')}")
            # Save taste note to memory if provided
            if parsed.get("taste_note"):
                mem_module.add_taste_note(parsed["taste_note"])
            return {
                "caption":     parsed["caption"],
                "hashtags":    parsed["hashtags"][:7],
                "emotion":     parsed.get("emotion", mood),
                "viral_score": round(parsed.get("confidence", 0.85) * 10, 2),
                "mood":        mood,
                "hashtag_str": " ".join(parsed["hashtags"][:7]),
                "thought":     parsed.get("thought", ""),
                "ai_powered":  True,
            }
        else:
            logger.warn("  AI response couldn't be parsed — falling back to offline mode")
    else:
        logger.warn("  AI unavailable — using offline caption bank")

    return _offline_fallback(mood)


# ── Offline fallback ───────────────────────────────────────────────────────

def _offline_fallback(mood: str) -> dict:
    """Score-based caption selection when AI is unavailable."""
    # Try captions.json first
    captions = FALLBACK_CAPTIONS.copy()
    if os.path.exists(CAPTIONS_JSON):
        try:
            with open(CAPTIONS_JSON, "r", encoding="utf-8") as f:
                captions = json.load(f)
        except Exception:
            pass

    pool = captions.get(mood, [])
    if not pool:
        for v in captions.values():
            pool.extend(v)

    if not pool:
        caption_text = "🔥 this one's different"
        emotion      = "hype"
        score        = 7.0
    else:
        used = mem_module.load().get("caption_history", [])
        # Prefer captions not used before
        fresh = [c for c in pool if c["text"] not in used]
        pool  = fresh if fresh else pool
        best  = max(pool, key=lambda c: float(c.get("intensity", 5)) * EMOTION_BOOST.get(c.get("emotion",""), 1.0))
        caption_text = best["text"]
        emotion      = best.get("emotion", mood)
        score        = round(float(best.get("intensity", 7)) * EMOTION_BOOST.get(emotion, 1.0), 2)

    tags = FALLBACK_HASHTAGS.get(mood, FALLBACK_HASHTAGS["hype"])

    return {
        "caption":     caption_text,
        "hashtags":    tags,
        "emotion":     emotion,
        "viral_score": score,
        "mood":        mood,
        "hashtag_str": " ".join(tags),
        "thought":     "",
        "ai_powered":  False,
    }


# ── Mood detector ──────────────────────────────────────────────────────────

def detect_mood(query: str) -> str:
    """Auto-detect mood from search query keywords."""
    q = query.lower()
    scores = {
        "sad":        sum(1 for k in ["sad","heartbreak","cry","miss","lonely","love","pain","tears","emotional"] if k in q),
        "hype":       sum(1 for k in ["hype","fire","crazy","best","epic","lit","banger","goat","power"] if k in q),
        "motivation": sum(1 for k in ["motivat","grind","hustle","win","goal","focus","level up","rise"] if k in q),
        "nostalgia":  sum(1 for k in ["nostalgic","throwback","remember","old","childhood","classic"] if k in q),
        "rage":       sum(1 for k in ["rage","angry","mad","furious","disrespect","betrayal","villain"] if k in q),
        "joy":        sum(1 for k in ["happy","joy","funny","cute","wholesome","smile","laugh"] if k in q),
    }
    best = max(scores, key=lambda m: scores[m])
    return best if scores[best] > 0 else "hype"


# ── Main entry ─────────────────────────────────────────────────────────────

def run(query: str = "", mood: str | None = None, clip_count: int = 0) -> dict:
    """
    Full AI soul run. Call this from run.py.
    Returns complete brain output dict.
    """
    if not mood or mood not in MOODS:
        mood = detect_mood(query)
        logger.info(f"  Auto-detected mood: {mood}")

    result = think(query=query, mood=mood, clip_count=clip_count)

    # Save to brain_output.json
    from config import BRAIN_OUTPUT
    with open(BRAIN_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Record in memory
    mem_module.record_run(
        query=query,
        mood=mood,
        caption=result["caption"],
        ai_thoughts=result.get("thought", ""),
        viral_score=result["viral_score"],
    )

    mode = "🧠 AI" if result.get("ai_powered") else "📋 offline"
    logger.ok(f"  [{mode}] Caption: {result['caption']}")
    logger.ok(f"  Viral score: {result['viral_score']}")

    return result

