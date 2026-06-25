"""
ytbot/make_subs.py
Converts cleaned_subs.srt → subs.ass with mobile-optimised styling.

Style choices (for 1080×1920 9:16 vertical video):
  - Bold white text, 14pt (ASS units scale well at this res)
  - Thick black outline (3px) — readable on any background
  - Semi-transparent black box behind text
  - Centred bottom-of-screen position
  - 150ms fade-in, no fade-out (snappy feel)
  - No karaoke gimmicks — clean and readable first
"""

import re
import os
import sys

import logger
from config import (
    BASE_DIR, CLEANED_SRT, SUBS_ASS,
    TARGET_W, TARGET_H,
    FONT_NAME, FONT_SIZE, FONT_BOLD,
    PRIMARY_COLOR, OUTLINE_COLOR, BACK_COLOR,
    OUTLINE_SIZE, SHADOW_SIZE, MARGIN_V
)


ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {TARGET_W}
PlayResY: {TARGET_H}
WrapStyle: 1
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{FONT_NAME},{FONT_SIZE},{PRIMARY_COLOR},&H000000FF,{OUTLINE_COLOR},{BACK_COLOR},{1 if FONT_BOLD else 0},0,0,0,100,100,0.5,0,1,{OUTLINE_SIZE},{SHADOW_SIZE},2,40,40,{MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

TIMECODE_RE = re.compile(
    r"(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})"
)


def srt_tc_to_ass(tc: str) -> str:
    """
    Convert SRT timecode (HH:MM:SS,mmm) to ASS timecode (H:MM:SS.cc).
    ASS only uses centiseconds (2 decimal places).
    """
    tc = tc.strip().replace(",", ".")
    # Ensure milliseconds present
    if "." not in tc:
        tc += ".000"

    parts = tc.split(":")
    if len(parts) != 3:
        return "0:00:00.00"

    h = int(parts[0])
    m = parts[1].zfill(2)
    s_parts = parts[2].split(".")
    s  = s_parts[0].zfill(2)
    ms = (s_parts[1] if len(s_parts) > 1 else "000").ljust(3, "0")
    cc = ms[:2]  # centiseconds

    return f"{h}:{m}:{s}.{cc}"


def parse_srt(content: str) -> list[dict]:
    blocks = re.split(r"\n\s*\n", content.strip())
    entries = []
    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if len(lines) < 2:
            continue

        tc_line = None
        tc_idx  = -1
        for idx, line in enumerate(lines):
            if TIMECODE_RE.search(line):
                tc_line = line
                tc_idx  = idx
                break

        if tc_line is None:
            continue

        m = TIMECODE_RE.search(tc_line)
        start = m.group(1)
        end   = m.group(2)
        text  = " ".join(lines[tc_idx + 1:]).strip()

        if not text:
            continue

        entries.append({"start": start, "end": end, "text": text})
    return entries


def build_ass_events(entries: list[dict]) -> list[str]:
    events = []
    for e in entries:
        start = srt_tc_to_ass(e["start"])
        end   = srt_tc_to_ass(e["end"])

        # Escape backslashes, then convert newlines to ASS \N
        text = e["text"].replace("\\", "\\\\").replace("\n", "\\N")

        # Fade-in 150ms effect
        text = r"{\fad(150,0)}" + text

        events.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
        )
    return events


def main():
    # Find input SRT
    srt_path = CLEANED_SRT
    if not os.path.exists(srt_path):
        # Try raw source video SRT as fallback
        import glob
        candidates = sorted(glob.glob(os.path.join(BASE_DIR, "source_video*.srt")))
        if candidates:
            srt_path = candidates[0]
            logger.warn(f"cleaned_subs.srt missing — using {os.path.basename(srt_path)}")
        else:
            logger.warn("No subtitle file found — skipping ASS generation")
            return

    logger.step(f"Building ASS subtitles from {os.path.basename(srt_path)}")

    with open(srt_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    entries = parse_srt(content)
    if not entries:
        logger.warn("No subtitle entries parsed — subs.ass not written")
        return

    logger.info(f"  {len(entries)} subtitle entries")

    events = build_ass_events(entries)

    with open(SUBS_ASS, "w", encoding="utf-8") as f:
        f.write(ASS_HEADER)
        f.write("\n".join(events) + "\n")

    logger.ok(f"Saved: subs.ass ({len(events)} dialogue lines)")
    logger.ok("make_subs.py — DONE")


if __name__ == "__main__":
    main()

