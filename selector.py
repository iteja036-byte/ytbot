import os
import json

base_dir = os.path.dirname(os.path.abspath(__file__))
lines_path = os.path.join(base_dir, "lines.json")
clips_dir = os.path.join(base_dir, "myclips")

if not os.path.exists(clips_dir) or not os.listdir(clips_dir):
    clips_dir = os.path.join(base_dir, "clips")

print(f"🔍 Dynamic Scanner target: {clips_dir}")

valid_clips = sorted([
    f for f in os.listdir(clips_dir) 
    if f.lower().endswith(('.mp4', '.mkv', '.mov'))
])

if not valid_clips:
    print("⚠️ Warning: No clip segments found inside workspace targets.")
    with open(os.path.join(base_dir, "chosen.txt"), "w") as f:
        f.write("")
    exit(0)

selected_clips = valid_clips[:8]
output_txt_path = os.path.join(base_dir, "chosen.txt")

with open(output_txt_path, "w", encoding='utf-8') as f:
    for clip in selected_clips:
        f.write(os.path.join(clips_dir, clip) + "\n")

print(f"🔥 Matrix generated: {len(selected_clips)} clips mapped -> chosen.txt")
