import re
import glob

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


def clean_text(text):
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"<.*?>", "", text)
    text = re.sub(r"[^a-zA-Z0-9 ,.!?'’-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


for block in blocks:
    lines = block.strip().splitlines()

    if len(lines) < 3:
        continue

    timecode = lines[1]
    text = clean_text(" ".join(lines[2:]))

    if len(text) < 3:
        continue

    words = text.split()

    chunk_size = 4  # slightly better balance than 3

    start_idx = 0

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i+chunk_size])

        cleaned.append(f"{idx}\n{timecode}\n{chunk}\n")
        idx += 1

output = "cleaned_subs.srt"

with open(output, "w", encoding="utf-8") as f:
    f.write("\n".join(cleaned))

print(f"✅ Created {output} with {idx-1} segments")
