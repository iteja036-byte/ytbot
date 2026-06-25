import re
import glob
import json
import os
from groq import Groq

# ---------------- LOAD ENV ----------------
def load_env():
    try:
        with open(".env", "r") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    os.environ[k] = v
    except:
        print("❌ .env missing")


load_env()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ---------------- FILE ----------------
files = glob.glob("*.srt")

if not files:
    print("❌ No SRT file found")
    exit(1)

srt = files[0]

with open(srt, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

blocks = re.split(r"\n\s*\n", content)

cleaned = []
idx = 1


# ---------------- CLEAN ----------------
def clean_text(text):
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------- AI EMOTION ENGINE ----------------
def ai_analyze(text):
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """
You are a short-form video emotion analyzer.

Return ONLY JSON:
{
  "emotion": "love|sad|anger|neutral",
  "intensity": 1-10,
  "hook_score": 1-10
}

Rules:
- Based on emotional impact for reels
- Hook_score = viral opening strength
"""
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            temperature=0.4
        )

        return json.loads(res.choices[0].message.content)

    except:
        return {"emotion": "neutral", "intensity": 5, "hook_score": 5}


# ---------------- SMART SPLIT ----------------
def smart_split(words):
    chunks = []
    current = []

    for w in words:
        current.append(w)

        if len(current) >= 6 or any(p in w for p in [",", ".", "!", "?"]):
            chunks.append(" ".join(current))
            current = []

    if current:
        chunks.append(" ".join(current))

    return chunks


# ---------------- MAIN ----------------
for block in blocks:
    lines = block.strip().splitlines()

    if len(lines) < 3:
        continue

    timecode = lines[1]
    text = clean_text(" ".join(lines[2:]))

    if len(text) < 3:
        continue

    ai = ai_analyze(text)

    words = text.split()
    chunks = smart_split(words)

    for chunk in chunks:

        score = (ai["intensity"] * 1.5) + ai["hook_score"]

        cleaned.append(
            f"{idx}\n{timecode}\n{chunk} [{ai['emotion']}|{score:.1f}]\n"
        )

        idx += 1


output = "cleaned_subs_v4_ai.srt"

with open(output, "w", encoding="utf-8") as f:
    f.write("\n".join(cleaned))

print(f"✅ AI Subtitle Brain v4 created: {output}")
