import json

REQUIRED_FIELDS = {"text", "emotion", "intensity"}

def load_json_safe(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print("❌ JSON load failed:", e)
        return None


def validate_captions(data):
    if not data or "captions" not in data:
        return False, "Missing captions key"

    clean = []

    for i, c in enumerate(data["captions"]):
        if not isinstance(c, dict):
            print(f"⚠️ Skipping invalid item {i}")
            continue

        if not REQUIRED_FIELDS.issubset(c.keys()):
            print(f"⚠️ Fixing missing fields in item {i}")

            c.setdefault("text", "default text")
            c.setdefault("emotion", "neutral")
            c.setdefault("intensity", 5)

        if not isinstance(c["text"], str):
            c["text"] = str(c["text"])

        if not isinstance(c["emotion"], str):
            c["emotion"] = "neutral"

        try:
            c["intensity"] = int(c["intensity"])
        except:
            c["intensity"] = 5

        clean.append(c)

    if not clean:
        return False, "No valid captions"

    return True, {"captions": clean}


def validate_and_fix(path):
    data = load_json_safe(path)

    ok, result = validate_captions(data)

    if not ok:
        print("❌ Validation failed:", result)
        return None

    print("✅ Validation passed + auto-fixed")
    return result
