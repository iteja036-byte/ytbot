"""
ytbot/validator.py
Validates and auto-fixes captions.json (and any other JSON data files).

Ensures every caption entry has required fields:
  - text  (non-empty string)
  - emotion (string, defaults to "hype")
  - intensity (float 0–10, defaults to 7.0)

Also validates brain_output.json structure before upload.
Returns cleaned data dict, or None if unrecoverable.
"""

import os
import json

import logger
from config import CAPTIONS_JSON, MOODS

REQUIRED_CAPTION_FIELDS = {
    "text":      (str,   ""),
    "emotion":   (str,   "hype"),
    "intensity": (float, 7.0),
}


def coerce(value, expected_type, default):
    """Try to cast value to expected_type, return default on failure."""
    try:
        if expected_type == float:
            return float(value)
        if expected_type == str:
            return str(value).strip()
        return expected_type(value)
    except (TypeError, ValueError):
        return default


def fix_caption(raw: dict) -> dict | None:
    """
    Ensure a caption entry has all required fields.
    Returns fixed dict, or None if text is completely missing.
    """
    fixed = {}
    for field, (ftype, default) in REQUIRED_CAPTION_FIELDS.items():
        raw_val = raw.get(field)
        if raw_val is None:
            fixed[field] = default
        else:
            fixed[field] = coerce(raw_val, ftype, default)

    # A caption without text is useless
    if not fixed["text"]:
        return None

    # Clamp intensity to [0, 10]
    fixed["intensity"] = max(0.0, min(10.0, fixed["intensity"]))

    # Normalise emotion to lowercase
    fixed["emotion"] = fixed["emotion"].lower().strip()

    return fixed


def validate_and_fix(path: str = CAPTIONS_JSON) -> dict | None:
    """
    Load and validate a captions JSON file.

    Expected format:
      {
        "sad": [ {text, emotion, intensity}, ... ],
        "hype": [ ... ],
        ...
      }

    OR a flat list:
      [ {text, emotion, intensity}, ... ]

    Returns a mood-keyed dict on success, None on unrecoverable failure.
    """
    if not os.path.exists(path):
        logger.warn(f"validator: {path} not found — returning None")
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        logger.err(f"validator: JSON parse error in {path}: {e}")
        return None

    # Normalise flat list → dict under "hype"
    if isinstance(raw, list):
        logger.warn("validator: flat list detected — wrapping under 'hype'")
        raw = {"hype": raw}

    if not isinstance(raw, dict):
        logger.err("validator: unexpected JSON structure")
        return None

    cleaned = {}
    total_in  = 0
    total_out = 0

    for mood_key, entries in raw.items():
        if not isinstance(entries, list):
            logger.warn(f"validator: skipping non-list value for mood '{mood_key}'")
            continue

        fixed_entries = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            total_in += 1
            fixed = fix_caption(entry)
            if fixed:
                fixed_entries.append(fixed)
                total_out += 1

        if fixed_entries:
            cleaned[mood_key.lower()] = fixed_entries

    if not cleaned:
        logger.err("validator: no valid captions after validation")
        return None

    logger.ok(f"validator: {total_out}/{total_in} captions valid across {len(cleaned)} moods")

    # Write fixed version back to disk
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.warn(f"validator: could not write fixed file: {e}")

    return cleaned


def validate_brain_output(data: dict) -> bool:
    """Validate brain_output.json before passing to upload."""
    required = ["caption", "hashtags", "mood", "viral_score"]
    for key in required:
        if key not in data:
            logger.err(f"brain_output missing field: {key}")
            return False
    if not isinstance(data["hashtags"], list):
        logger.err("brain_output: hashtags must be a list")
        return False
    if not data["caption"].strip():
        logger.err("brain_output: caption is empty")
        return False
    return True


if __name__ == "__main__":
    result = validate_and_fix(CAPTIONS_JSON)
    if result:
        logger.ok("Validation passed")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        logger.err("Validation failed")

