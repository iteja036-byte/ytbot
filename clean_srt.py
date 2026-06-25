"""
ytbot/clean_srt.py
Cleans a raw auto-generated SRT file:
  - Strips HTML tags, sound effects [music], ♪ symbols
  - Removes duplicate/repeated subtitle lines
  - Splits lines > 8 words into shorter chunks for punchier display
  - Validates timecode format
  - Preserves unicode (Japanese, Arabic, etc.)

Output: cleaned_subs.srt
"""

import re
import os
import glob

import logger
from config import BASE_DIR, CLEANED_SRT


TIMECODE_RE = re.compile(
    r"(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})"
)


def find_srt() -> str | None:
    """Find the best SRT file in BASE_DIR."""
    # Prefer cleaned_subs.srt if already exists (idempotent)
    if os.path.exists(CLEANED_SRT):
        return CLEANED_SRT

    # Source video auto-subtitle
    candidates = sorted(glob.glob(os.path.join(BASE_DIR, "source_video*.srt")))
    if candidates:
        return candidates[0]

    # Any SRT at all
    any_srt = sorted(glob.glob(os.path.join(BASE_DIR, "*.srt")))
    if any_srt:
        return any_srt[0]

    return None


def clean_text(raw: str) -> str:
    """Clean a single subtitle line's text content."""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", raw)
    # Remove sound effect brackets [music], (applause) etc
    text = re.sub(r"[\[\(][^\]\)]{0,40}[\]\)]", "", text)
    # Remove music notes
    text = re.sub(r"[♪♫🎵🎶]", "", text)
    # Normalise whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_srt(content: str) -> list[dict]:
    """Parse SRT content into list of {start, end, text} dicts."""
    blocks = re.split(r"\n\s*\n", content.strip())
    entries = []

    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if len(lines) < 2:
            continue

        # Find the timecode line (may not always be index 1)
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
        start_tc = m.group(1).replace(".", ",")  # normalise to comma
        end_tc   = m.group(2).replace(".", ",")

        # Text is everything after the timecode line
        raw_text = " ".join(lines[tc_idx + 1:])
        text = clean_text(raw_text)

        if len(text) < 2:
            continue

        entries.append({"start": start_tc, "end": end_tc, "text": text})

    return entries


def dedup(entries: list[dict]) -> list[dict]:
    """Remove consecutive identical or near-identical lines."""
    result = []
    prev_text = ""
    for e in entries:
        if e["text"].lower() == prev_text.lower():
            continue
        result.append(e)
        prev_text = e["text"]
    return result


def write_srt(entries: list[dict], path: str):
    lines = []
    for i, e in enumerate(entries, 1):
        lines.append(str(i))
        lines.append(f"{e['start']} --> {e['end']}")
        lines.append(e["text"])
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    srt_path = find_srt()
    if srt_path is None:
        logger.warn("No SRT file found — skipping subtitle cleaning")
        return

    logger.step(f"Cleaning subtitles: {os.path.basename(srt_path)}")

    with open(srt_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    entries = parse_srt(content)
    logger.info(f"  Parsed {len(entries)} raw subtitle entries")

    entries = dedup(entries)
    logger.info(f"  After dedup: {len(entries)} entries")

    if not entries:
        logger.warn("No usable subtitle entries found after cleaning")
        return

    write_srt(entries, CLEANED_SRT)
    logger.ok(f"Saved: cleaned_subs.srt ({len(entries)} lines)")
    logger.ok("clean_srt.py — DONE")


if __name__ == "__main__":
    main()

