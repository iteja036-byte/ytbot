import re
import glob
from collections import defaultdict

input_file = "cleaned_subs_v6_flow.srt"
output_file = "cleaned_subs_v7_viral.srt"

files = glob.glob(input_file)

if not files:
    print("❌ Input file missing")
    exit(1)

with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

blocks = re.split(r"\n\s*\n", content)

# ---------------- CLEAN ----------------
def clean(text):
    return re.sub(r"\s+", " ", text).strip()

# ---------------- VIRAL SCORING ----------------
HOOK_WORDS = ["you", "love", "never", "cry", "alone", "hate", "miss", "gone"]

def viral_score(text, position):
    words = text.lower().split()

    hook_score = sum(2 for w in words if w in HOOK_WORDS)

    length_score = min(len(words) / 6, 2)

    # early position boost (first seconds matter most)
    position_boost = 2.0 if position < 3 else 1.0

    return hook_score + length_score + position_boost

# ---------------- GROUP BY TIMESTAMP ----------------
timeline = defaultdict(list)

for block in blocks:
    lines = block.strip().splitlines()
    if len(lines) < 3:
        continue

    timecode = lines[1].strip()
    text = clean(" ".join(lines[2:]))

    if len(text) < 2:
        continue

    timeline[timecode].append(text)

# ---------------- DIRECTOR BRAIN ----------------
cleaned = []
idx = 1
position = 0

emotion_arc = []

for timecode, texts in timeline.items():

    merged = " ".join(texts)
    words = merged.split()

    chunk = []
    for w in words:
        chunk.append(w)

        if len(chunk) >= 6 or w.endswith((".", "!", "?")):

            sentence = " ".join(chunk)

            score = viral_score(sentence, position)

            # emotional tagging (simple heuristic)
            emotion = "neutral"
            low = sentence.lower()

            if any(k in low for k in ["love", "miss", "heart"]):
                emotion = "love"
            elif any(k in low for k in ["cry", "gone", "alone"]):
                emotion = "sad"
            elif any(k in low for k in ["never", "hate"]):
                emotion = "anger"

            emotion_arc.append(emotion)

            cleaned.append(
                f"{idx}\n{timecode}\n{sentence} [{emotion}|{score:.1f}]\n"
            )

            idx += 1
            position += 1
            chunk = []

    if chunk:
        sentence = " ".join(chunk)
        score = viral_score(sentence, position)

        cleaned.append(
            f"{idx}\n{timecode}\n{sentence} [{emotion}|{score:.1f}]\n"
        )

        idx += 1
        position += 1

# ---------------- OUTPUT ----------------
with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(cleaned))

print(f"✅ Viral Director Brain v7 created: {output_file}")
print(f"Segments: {idx-1}")
print(f"Emotion arc: {emotion_arc[:10]}...")
