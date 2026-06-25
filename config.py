"""
ytbot v2 — config.py
Single source of truth. All settings here.
"""

import os

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CLIPS_DIR   = os.path.join(BASE_DIR, "clips")
OUTPUT_DIR  = os.path.join(BASE_DIR, "output")
LOGS_DIR    = os.path.join(BASE_DIR, "logs")
MEMORY_DIR  = os.path.join(BASE_DIR, "memory")

SOURCE_VIDEO  = os.path.join(BASE_DIR, "source_video.mp4")
CLEANED_SRT   = os.path.join(BASE_DIR, "cleaned_subs.srt")
SUBS_ASS      = os.path.join(BASE_DIR, "subs.ass")
CHOSEN_TXT    = os.path.join(BASE_DIR, "chosen.txt")
LINES_JSON    = os.path.join(BASE_DIR, "lines.json")
CAPTIONS_JSON = os.path.join(BASE_DIR, "captions.json")
BRAIN_OUTPUT  = os.path.join(BASE_DIR, "brain_output.json")
FINAL_REEL    = os.path.join(OUTPUT_DIR, "final_reel.mp4")
MEMORY_FILE   = os.path.join(MEMORY_DIR, "editor_memory.json")

# ── Video output ──────────────────────────────────────────────
TARGET_W      = 1080
TARGET_H      = 1920
TARGET_FPS    = 30
VIDEO_BITRATE = "4M"
AUDIO_BITRATE = "192k"

# ── Scene detection ───────────────────────────────────────────
SCENE_THRESHOLD   = 0.35
MIN_CLIP_DURATION = 1.0
MAX_CLIP_DURATION = 8.0
MAX_CLIPS         = 15

# ── Reel build ────────────────────────────────────────────────
REEL_DURATIONS = [
    2.0, 1.6, 1.2, 1.0, 0.8,
    0.7, 0.6, 0.5, 0.45, 0.4,
    0.35, 0.3, 0.25, 0.25, 0.2
]
MAX_REEL_CLIPS = 12

# ── Subtitle style ────────────────────────────────────────────
FONT_NAME     = "Arial"
FONT_SIZE     = 14
FONT_BOLD     = True
PRIMARY_COLOR = "&H00FFFFFF"
OUTLINE_COLOR = "&H00000000"
BACK_COLOR    = "&H99000000"
OUTLINE_SIZE  = 3
SHADOW_SIZE   = 0
MARGIN_V      = 120

# ── Emotion scoring ───────────────────────────────────────────
EMOTION_BOOST = {
    "heartbreak":  2.0,
    "sad-love":    1.5,
    "missing-you": 1.2,
    "hype":        1.8,
    "motivation":  1.6,
    "nostalgia":   1.3,
    "rage":        1.7,
    "joy":         1.1,
}

MOODS = ["sad", "hype", "motivation", "nostalgia", "rage", "joy"]

# ── yt-dlp ────────────────────────────────────────────────────
YTDLP_FORMAT = (
    "bestvideo[height<=1080][ext=mp4]"
    "+bestaudio[ext=m4a]"
    "/best[height<=1080][ext=mp4]"
    "/best"
)
YTDLP_MERGE_FORMAT = "mp4"

# ── Upload credentials ────────────────────────────────────────
TIKTOK_SESSION_ID      = os.getenv("TIKTOK_SESSION_ID", "")
INSTAGRAM_USERNAME     = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD     = os.getenv("INSTAGRAM_PASSWORD", "")
YOUTUBE_CLIENT_SECRETS = os.path.join(BASE_DIR, "client_secrets.json")

# ── AI Soul (Claude API) ──────────────────────────────────────
# The brain uses Claude to think like a real content creator.
# API key is handled automatically inside claude.ai artifacts.
# When running standalone (Termux), set this env var:
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_MODEL          = "claude-sonnet-4-6"
AI_MAX_TOKENS     = 1000

# The editor's personality — injected into every AI prompt
EDITOR_PERSONA = """You are a viral short-form video editor with genuine taste and emotional intelligence.
You grew up on anime, feel music deeply, and understand what makes people stop scrolling.
You think like a 19-year-old creative director who has studied every trending edit on TikTok.
You have strong opinions. You pick captions that feel real, not generic.
You write like you mean it — lowercase, raw, no corporate energy.
You remember what worked before and build on it."""

