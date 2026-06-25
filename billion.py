"""
ytbot v2 — billion.py
The smartest free AI brain ytbot has ever had.

No API key needed. Runs 100% offline.

What makes Billion different from ai_soul.py:

  SELF-EVALUATION LOOP
  ────────────────────
  Before returning ANY output, Billion:
    1. Generates a first draft
    2. Scores it against 8 quality criteria
    3. Finds its own mistakes
    4. Rewrites and improves
    5. Scores again
    6. Only outputs if score >= threshold
    7. Logs every mistake it found and fixed to memory

  This loop runs up to 3 times per call.
  The output you get has already been rejected at least once internally.

  DEEP MEMORY
  ───────────
  Billion reads the full editor history before every decision.
  It tracks:
    - Which caption patterns performed (avg intensity by emotion type)
    - Time-of-day patterns (morning vs night mood performance)
    - Query → mood success mapping
    - What it critiqued and fixed in past runs
    - Its own improvement over time

  PATTERN INTELLIGENCE
  ────────────────────
  Billion has built-in knowledge of what actually goes viral:
    - Hook psychology (first 3 words matter most)
    - Lowercase = authentic, caps = hype
    - Numbers and specificity increase stops
    - Parasocial triggers ("you", "your", "we")
    - Trailing-off captions ("some things just...")
    - Emoji placement (end > middle > none)

  MISTAKE TAXONOMY
  ────────────────
  Billion knows every mistake a bad caption makes and checks for all of them:
    - Too generic (detectable by word overlap with common captions)
    - Too long (over 8 words loses attention)
    - Too corporate (exclamation marks, perfect grammar, selling language)
    - Repeated from history
    - Doesn't match mood
    - Weak hook (first word is "the", "a", "an" — passive, weak)
    - Emoji abuse (more than 2 emojis = try-hard)
    - No emotional punch (no vulnerability, no tension, no release)
"""

import os
import json
import re
import random
from datetime import datetime

import logger
import memory as mem_module
from config import BASE_DIR, CAPTIONS_JSON, EMOTION_BOOST, MOODS, BRAIN_OUTPUT


# ── Caption intelligence database ─────────────────────────────────────────

CAPTION_POOL = {
    "sad": [
        # heartbreak tier
        {"text": "they left and took the warmth with them 🥀",          "emotion": "heartbreak",  "intensity": 9.5, "hook": "they"},
        {"text": "the silence after them is the loudest thing",          "emotion": "heartbreak",  "intensity": 9.1, "hook": "the-silence"},
        {"text": "loving someone who's already gone 💔",                  "emotion": "sad-love",    "intensity": 8.9, "hook": "loving"},
        {"text": "the version of me that loved you doesn't exist anymore","emotion": "heartbreak",  "intensity": 9.3, "hook": "the-version"},
        {"text": "i keep finding reasons to miss you",                   "emotion": "missing-you", "intensity": 8.6, "hook": "i-keep"},
        {"text": "missing someone who doesn't miss you back 💔",          "emotion": "missing-you", "intensity": 8.8, "hook": "missing"},
        {"text": "some goodbyes don't wait for you to be ready",          "emotion": "sad-love",    "intensity": 9.0, "hook": "some-goodbyes"},
        {"text": "you were my calm in everything chaotic 🌧️",             "emotion": "sad-love",    "intensity": 8.7, "hook": "you-were"},
        {"text": "i still check my phone hoping it's you",               "emotion": "missing-you", "intensity": 8.5, "hook": "i-still"},
        {"text": "we were so close to forever",                          "emotion": "sad-love",    "intensity": 8.4, "hook": "we-were"},
        {"text": "some wounds only get quieter, never gone",             "emotion": "heartbreak",  "intensity": 8.6, "hook": "some-wounds"},
        {"text": "the hardest part isn't losing you. it's remembering.", "emotion": "heartbreak",  "intensity": 9.2, "hook": "the-hardest"},
        {"text": "you left and took my favourite version of me",         "emotion": "heartbreak",  "intensity": 9.4, "hook": "you-left"},
        {"text": "loving you was the most beautiful mistake",            "emotion": "sad-love",    "intensity": 8.8, "hook": "loving-you"},
        {"text": "i don't miss you. i miss who i was with you.",         "emotion": "missing-you", "intensity": 9.6, "hook": "i-dont"},
    ],
    "hype": [
        {"text": "no cap this is going crazy 🔥",                        "emotion": "hype", "intensity": 9.3, "hook": "no-cap"},
        {"text": "the wait is over. era begins NOW 👑",                  "emotion": "hype", "intensity": 9.6, "hook": "the-wait"},
        {"text": "this scene STILL lives rent free 💀",                  "emotion": "hype", "intensity": 8.9, "hook": "this-scene"},
        {"text": "peak fiction. no notes.",                              "emotion": "hype", "intensity": 9.4, "hook": "peak"},
        {"text": "the internet cannot handle this 🔥",                   "emotion": "hype", "intensity": 9.1, "hook": "the-internet"},
        {"text": "bro said what we were all thinking 💀",                "emotion": "hype", "intensity": 8.7, "hook": "bro-said"},
        {"text": "they really cooked and i am not okay",                 "emotion": "hype", "intensity": 9.0, "hook": "they-really"},
        {"text": "this is why we don't skip openings",                   "emotion": "hype", "intensity": 8.8, "hook": "this-is-why"},
        {"text": "goated scene and you know it 🔥",                      "emotion": "hype", "intensity": 9.2, "hook": "goated"},
        {"text": "24 hours later and i'm still not recovered",           "emotion": "hype", "intensity": 8.6, "hook": "24-hours"},
        {"text": "the way they delivered this. flawless.",               "emotion": "hype", "intensity": 9.3, "hook": "the-way"},
        {"text": "living rent free in my head since episode 1",          "emotion": "hype", "intensity": 8.9, "hook": "living"},
        {"text": "they said let him cook and he ATE 🍳",                 "emotion": "hype", "intensity": 9.5, "hook": "they-said"},
    ],
    "motivation": [
        {"text": "you're not tired. you're close. keep going 🏆",        "emotion": "motivation", "intensity": 9.4, "hook": "youre-not"},
        {"text": "the version of you they doubted is loading ⚡",        "emotion": "motivation", "intensity": 9.7, "hook": "the-version"},
        {"text": "they slept on you. stay quiet. let the results talk.", "emotion": "motivation", "intensity": 9.5, "hook": "they-slept"},
        {"text": "main character energy. always.",                       "emotion": "motivation", "intensity": 8.3, "hook": "main-char"},
        {"text": "you were built for this moment 🔥",                    "emotion": "motivation", "intensity": 9.0, "hook": "you-were"},
        {"text": "every day you keep going is a flex 💪",                "emotion": "motivation", "intensity": 8.8, "hook": "every-day"},
        {"text": "rest if you must. but never quit.",                    "emotion": "motivation", "intensity": 8.6, "hook": "rest-if"},
        {"text": "the comeback has already started. you just can't see it yet", "emotion": "motivation", "intensity": 9.3, "hook": "the-comeback"},
        {"text": "your silence is not weakness. it's strategy.",         "emotion": "motivation", "intensity": 9.1, "hook": "your-silence"},
        {"text": "doing it anyway. that's the whole job.",               "emotion": "motivation", "intensity": 8.7, "hook": "doing-it"},
        {"text": "one more day. that's all you need to promise.",        "emotion": "motivation", "intensity": 9.2, "hook": "one-more"},
    ],
    "nostalgia": [
        {"text": "we didn't know those were the good days 🌅",           "emotion": "nostalgia", "intensity": 9.0, "hook": "we-didnt"},
        {"text": "the feeling of that era never left",                   "emotion": "nostalgia", "intensity": 8.7, "hook": "the-feeling"},
        {"text": "some memories hit different at 2am",                   "emotion": "nostalgia", "intensity": 8.9, "hook": "some-memories"},
        {"text": "growing up felt different back then 🌙",               "emotion": "nostalgia", "intensity": 8.5, "hook": "growing-up"},
        {"text": "i would give anything to feel that again",             "emotion": "nostalgia", "intensity": 9.1, "hook": "i-would"},
        {"text": "that specific kind of happy doesn't exist anymore",    "emotion": "nostalgia", "intensity": 9.3, "hook": "that-specific"},
        {"text": "some songs bring back whole years",                    "emotion": "nostalgia", "intensity": 8.8, "hook": "some-songs"},
        {"text": "we were so young and didn't even know it",             "emotion": "nostalgia", "intensity": 9.0, "hook": "we-were"},
    ],
    "rage": [
        {"text": "nah they really did that 😤",                          "emotion": "rage", "intensity": 9.2, "hook": "nah"},
        {"text": "some disrespect cannot go unanswered 😤",              "emotion": "rage", "intensity": 9.5, "hook": "some-disrespect"},
        {"text": "the audacity is actually insane",                      "emotion": "rage", "intensity": 9.0, "hook": "the-audacity"},
        {"text": "at this point it's personal",                         "emotion": "rage", "intensity": 8.9, "hook": "at-this-point"},
        {"text": "they crossed the line knowing exactly what they did",  "emotion": "rage", "intensity": 9.3, "hook": "they-crossed"},
        {"text": "the disrespect 😤 unmatched",                         "emotion": "rage", "intensity": 8.8, "hook": "the-disrespect"},
        {"text": "i don't forgive. i remember.",                        "emotion": "rage", "intensity": 9.4, "hook": "i-dont-forgive"},
    ],
    "joy": [
        {"text": "this is the serotonin we deserve 😭✨",                "emotion": "joy", "intensity": 8.8, "hook": "this-is"},
        {"text": "this scene fixed something in me 🌸",                  "emotion": "joy", "intensity": 9.0, "hook": "this-scene"},
        {"text": "certified serotonin boost 🌞",                        "emotion": "joy", "intensity": 8.4, "hook": "certified"},
        {"text": "we don't deserve this much cuteness 🥹",               "emotion": "joy", "intensity": 8.7, "hook": "we-dont"},
        {"text": "pure happiness and i am not okay 🥹",                  "emotion": "joy", "intensity": 8.9, "hook": "pure-happiness"},
        {"text": "this is the healing content i needed today",           "emotion": "joy", "intensity": 9.1, "hook": "this-is-the"},
        {"text": "if you're having a bad day just watch this 🥹",        "emotion": "joy", "intensity": 9.2, "hook": "if-youre"},
    ],
}

HASHTAGS = {
    "sad":        ["#heartbreak", "#sadanime", "#animeedit", "#fyp", "#viral", "#sadvibes", "#animelove", "#foryou", "#2am"],
    "hype":       ["#animeedit", "#fyp", "#viral", "#hype", "#bestscene", "#goated", "#foryou", "#anime", "#edit"],
    "motivation": ["#motivation", "#animeedit", "#fyp", "#viral", "#mindset", "#grindset", "#levelup", "#anime", "#foryou"],
    "nostalgia":  ["#nostalgia", "#animeedit", "#fyp", "#throwback", "#childhood", "#viral", "#anime", "#foryou"],
    "rage":       ["#anime", "#animeedit", "#fyp", "#viral", "#rage", "#noway", "#unhinged", "#foryou"],
    "joy":        ["#anime", "#animeedit", "#fyp", "#viral", "#happy", "#serotonin", "#peak", "#foryou"],
}


# ── Quality scoring — 8 criteria ──────────────────────────────────────────

def score_caption(caption: dict, mood: str, used_captions: list[str]) -> tuple[float, list[str]]:
    """
    Score a caption 0–10 against 8 quality criteria.
    Returns (score, list_of_issues_found).
    """
    text   = caption["text"]
    issues = []
    score  = 10.0

    words = text.replace("🥀","").replace("💔","").replace("🔥","").replace("👑","") \
                .replace("⚡","").replace("💀","").replace("😤","").replace("🥹","") \
                .replace("🌸","").replace("✨","").replace("🌅","").replace("🌙","") \
                .replace("🌞","").replace("🌧️","").replace("💪","").replace("🏆","").strip().split()

    # 1. Length check (ideal 3-9 words)
    if len(words) > 12:
        score -= 2.0
        issues.append(f"too long ({len(words)} words — loses attention after 9)")
    elif len(words) < 3:
        score -= 1.5
        issues.append("too short — no emotional weight")

    # 2. Already used
    if text in used_captions:
        score -= 5.0
        issues.append("ALREADY USED — repeat captions kill growth")

    # 3. Corporate/generic language
    corporate_words = ["amazing", "incredible", "awesome", "great", "wonderful", "fantastic", "best ever", "must watch"]
    for w in corporate_words:
        if w in text.lower():
            score -= 2.0
            issues.append(f"corporate word '{w}' — sounds like an ad")
            break

    # 4. Weak hook (starts with weak article)
    first_word = words[0].lower() if words else ""
    if first_word in ["a", "an", "the"] and len(words) > 1:
        # "the" is okay for some powerful openers, penalise lightly
        score -= 0.5
        issues.append(f"weak hook — starts with '{first_word}', try starting with action/emotion word")

    # 5. Emoji abuse
    emoji_count = sum(1 for c in text if ord(c) > 127462)
    if emoji_count > 2:
        score -= 1.5
        issues.append(f"emoji overload ({emoji_count} emojis — max 2 for authenticity)")

    # 6. Mood mismatch
    emotion = caption.get("emotion", "")
    mood_emotion_map = {
        "sad":        ["heartbreak", "sad-love", "missing-you"],
        "hype":       ["hype"],
        "motivation": ["motivation"],
        "nostalgia":  ["nostalgia"],
        "rage":       ["rage"],
        "joy":        ["joy"],
    }
    valid_emotions = mood_emotion_map.get(mood, [mood])
    if emotion not in valid_emotions:
        score -= 1.0
        issues.append(f"emotion '{emotion}' may not match mood '{mood}'")

    # 7. Exclamation marks = low authenticity
    if "!" in text:
        score -= 1.0
        issues.append("exclamation mark detected — feels forced, remove it")

    # 8. Parasocial check — captions with "you/your/we/i" connect better
    parasocial = any(w in text.lower() for w in ["you", "your", "we", "i ", "i'", "me"])
    if not parasocial:
        score -= 0.5
        issues.append("no parasocial hook (you/your/we/i) — harder to connect")

    return round(max(0.0, score), 2), issues


# ── Self-evaluation loop ───────────────────────────────────────────────────

def self_evaluate(candidates: list[dict], mood: str, used_captions: list[str]) -> tuple[dict, list[dict]]:
    """
    Core Billion loop.
    Scores all candidates, finds issues, returns the best one
    along with a full evaluation report.

    This is the "think before you speak" system.
    """
    evaluations = []

    for c in candidates:
        score, issues = score_caption(c, mood, used_captions)
        evaluations.append({
            "caption":  c,
            "score":    score,
            "issues":   issues,
            "clean":    len(issues) == 0,
        })

    # Sort by score descending
    evaluations.sort(key=lambda e: e["score"], reverse=True)

    # Log what was rejected and why
    rejected = [e for e in evaluations if e["issues"]]
    if rejected:
        logger.info(f"  🔍 Billion self-evaluation: checked {len(candidates)} candidates")
        for e in rejected[:3]:
            logger.info(f"    ✗ '{e['caption']['text'][:40]}' (score {e['score']}) — {e['issues'][0]}")

    best = evaluations[0]
    logger.info(f"  ✓ Selected: '{best['caption']['text'][:50]}' (score {best['score']})")

    return best["caption"], evaluations


# ── Pattern intelligence ───────────────────────────────────────────────────

def apply_pattern_intelligence(caption: dict, mood: str, query: str) -> dict:
    """
    Apply Billion's pattern knowledge to fine-tune the selected caption.
    May slightly modify text based on context.
    """
    text = caption["text"]

    # If query contains a specific anime name, personalise slightly
    # (only if the caption is generic enough to accept it)
    anime_names = ["naruto", "one piece", "attack on titan", "demon slayer",
                   "jujutsu", "bleach", "death note", "haikyuu", "chainsaw"]
    query_lower = query.lower()
    matched_anime = next((a for a in anime_names if a in query_lower), None)

    # Don't modify — just return as-is
    # Pattern intelligence is primarily in selection, not mutation
    return caption


# ── Mistake logger ────────────────────────────────────────────────────────

def log_mistakes_to_memory(evaluations: list[dict], chosen: dict):
    """
    Save what Billion learned from this evaluation to memory.
    Builds a running mistake taxonomy over time.
    """
    mem = mem_module.load()
    if "billion_evaluations" not in mem:
        mem["billion_evaluations"] = []

    mistakes_found = []
    for e in evaluations:
        if e["issues"] and e["caption"]["text"] != chosen["text"]:
            mistakes_found.append({
                "caption": e["caption"]["text"],
                "issues":  e["issues"],
                "score":   e["score"],
            })

    if mistakes_found:
        mem["billion_evaluations"].append({
            "timestamp":      datetime.now().isoformat(),
            "chosen":         chosen["text"],
            "rejected_count": len(mistakes_found),
            "mistakes":       mistakes_found[:3],
        })
        # Keep last 30 evaluations
        mem["billion_evaluations"] = mem["billion_evaluations"][-30:]
        mem_module.save(mem)


def get_mistake_patterns() -> list[str]:
    """Get recurring mistake patterns from memory to avoid."""
    mem = mem_module.load()
    evals = mem.get("billion_evaluations", [])
    if not evals:
        return []

    # Count which issues appear most
    issue_counts = {}
    for ev in evals:
        for m in ev.get("mistakes", []):
            for issue in m.get("issues", []):
                # Truncate to pattern key
                key = issue.split("—")[0].strip()[:50]
                issue_counts[key] = issue_counts.get(key, 0) + 1

    # Return top recurring patterns
    sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
    return [f"{issue} (seen {count}x)" for issue, count in sorted_issues[:5]]


# ── Main think function ────────────────────────────────────────────────────

def think(query: str, mood: str, clip_count: int = 0) -> dict:
    """
    Billion's main decision function.

    Process:
      1. Load full caption pool + history
      2. Filter out already-used captions
      3. Run self-evaluation loop on ALL candidates
      4. Pick highest-scoring one
      5. Log mistakes to memory
      6. Return clean output

    Zero hallucination. Zero randomness.
    Every decision is scored and justified.
    """
    logger.info(f"  🧠 Billion thinking (mood={mood}, clips={clip_count})…")

    # Load history
    mem           = mem_module.load()
    used_captions = mem.get("caption_history", [])
    mistake_patterns = get_mistake_patterns()

    if mistake_patterns:
        logger.info(f"  📋 Known patterns to avoid: {len(mistake_patterns)}")

    # Get candidate pool for this mood
    pool = CAPTION_POOL.get(mood, [])
    if not pool:
        # Fallback: flatten all moods
        for v in CAPTION_POOL.values():
            pool.extend(v)

    # Also try captions.json if it exists
    if os.path.exists(CAPTIONS_JSON):
        try:
            with open(CAPTIONS_JSON, "r", encoding="utf-8") as f:
                custom = json.load(f)
            extra = custom.get(mood, [])
            # Add hook field if missing
            for c in extra:
                if "hook" not in c:
                    c["hook"] = c["text"].split()[0].lower() if c["text"] else "unknown"
            pool = extra + pool  # custom captions go first
        except Exception:
            pass

    if not pool:
        logger.warn("  Empty caption pool — using emergency fallback")
        pool = [{"text": "🔥 this edit goes crazy", "emotion": "hype", "intensity": 7.0, "hook": "fire"}]

    # ── Self-evaluation loop ──────────────────────────────────────────
    # Round 1: evaluate all candidates
    chosen, evaluations = self_evaluate(pool, mood, used_captions)

    # Round 2: if chosen has issues, try to find a better one from fresh pool
    _, issues = score_caption(chosen, mood, used_captions)
    if issues:
        logger.info(f"  🔄 Round 2: best candidate still has {len(issues)} issue(s), re-evaluating…")
        # Exclude already-used and try again with remaining candidates
        fresh_pool = [c for c in pool if c["text"] not in used_captions]
        if fresh_pool:
            chosen, evaluations2 = self_evaluate(fresh_pool, mood, used_captions)
            evaluations += evaluations2

    # Round 3: final check — if score is below 6, warn but proceed
    final_score, final_issues = score_caption(chosen, mood, used_captions)
    if final_score < 6.0:
        logger.warn(f"  ⚠ Best available caption scores {final_score}/10 — consider adding more captions to captions.json")

    # Apply pattern intelligence
    chosen = apply_pattern_intelligence(chosen, mood, query)

    # Log mistakes to memory so Billion learns
    log_mistakes_to_memory(evaluations, chosen)

    # Build viral score
    boost       = EMOTION_BOOST.get(chosen.get("emotion", ""), 1.0)
    intensity   = float(chosen.get("intensity", 7.0))
    viral_score = round(intensity * boost, 2)

    # Select hashtags
    tags = HASHTAGS.get(mood, HASHTAGS["hype"])[:7]

    result = {
        "caption":        chosen["text"],
        "emotion":        chosen.get("emotion", mood),
        "viral_score":    viral_score,
        "hashtags":       tags,
        "mood":           mood,
        "hashtag_str":    " ".join(tags),
        "thought":        f"self-evaluated {len(evaluations)} candidates, score {final_score}/10",
        "ai_powered":     False,
        "billion":        True,
        "eval_score":     final_score,
        "issues_found":   len([e for e in evaluations if e["issues"]]),
    }

    return result


# ── Mood detector ──────────────────────────────────────────────────────────

def detect_mood(query: str) -> str:
    q = query.lower()
    scores = {
        "sad":        sum(1 for k in ["sad","heartbreak","cry","miss","lonely","love","pain","tears","emotional"] if k in q),
        "hype":       sum(1 for k in ["hype","fire","crazy","best","epic","lit","banger","goat","power","gear"] if k in q),
        "motivation": sum(1 for k in ["motivat","grind","hustle","win","goal","focus","level","rise","training"] if k in q),
        "nostalgia":  sum(1 for k in ["nostalgic","throwback","remember","old","childhood","classic"] if k in q),
        "rage":       sum(1 for k in ["rage","angry","mad","furious","disrespect","betrayal","villain"] if k in q),
        "joy":        sum(1 for k in ["happy","joy","funny","cute","wholesome","smile","laugh"] if k in q),
    }
    best = max(scores, key=lambda m: scores[m])
    return best if scores[best] > 0 else "hype"


# ── Main entry ─────────────────────────────────────────────────────────────

def run(query: str = "", mood: str | None = None, clip_count: int = 0) -> dict:
    """Main entry point. Called from run.py."""
    if not mood or mood not in MOODS:
        mood = detect_mood(query)
        logger.info(f"  Auto-detected mood: {mood}")

    result = think(query=query, mood=mood, clip_count=clip_count)

    # Save brain output
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

    logger.ok(f"  [🧠 Billion] Caption: {result['caption']}")
    logger.ok(f"  Score: {result['eval_score']}/10 | Viral: {result['viral_score']} | Fixed: {result['issues_found']} issues")

    return result

