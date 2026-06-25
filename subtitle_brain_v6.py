import re
import glob
from collections import defaultdict

input_file = "cleaned_subs_v5_fixed.srt"
output_file = "cleaned_subs_v6_flow.srt"

with open(input_file, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

blocks = re.split(r"\n\s*\n", content)

# ---------------- CLEAN TEXT ----------------
def clean(text):
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ---------------- GROUP BY TIME ----------------
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

# ---------------- FLOW BUILDER ----------------
def merge_flow(texts):
    """
    Brain v6:
    - merge fragments into natural speech
    - avoid word repetition
    """

    words = []
    seen = set()

    for t in texts:
        for w in t.split():

            lw = w.lower()

            if lw not in seen:
                words.append(w)
                seen.add(lw)

    return " ".join(words)

# ---------------- REBUILD OUTPUT ----------------
cleaned = []
idx = 1

prev_sentence = ""

for timecode, texts in timeline.items():

    merged = merge_flow(texts)

    # avoid near-duplicate sentences across timeline
    if merged.lower() == prev_sentence.lower():
        continue

    prev_sentence = merged

    # split long flow into readable chunks
    words = merged.split()
    chunk = []

    for w in words:
        chunk.append(w)

        if len(chunk) >= 7 or w.endswith((".", "!", "?")):
            cleaned.append(f"{idx}\n{timecode}\n{' '.join(chunk)}\n")
            idx += 1
            chunk = []

    if chunk:
        cleaned.append(f"{idx}\n{timecode}\n{' '.join(chunk)}\n")
        idx += 1

with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(cleaned))

print(f"✅ Flow subtitles created: {output_file}")
print(f"Total segments: {idx-1}")
