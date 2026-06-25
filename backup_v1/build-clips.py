import os
from moviepy.editor import ImageClip, concatenate_videoclips

folder = "clips"

if not os.path.exists("chosen.txt"):
    print("ERROR: chosen.txt missing")
    exit(1)

with open("chosen.txt") as f:
    scenes = [x.strip() for x in f.readlines() if x.strip()]

clips = []

durations = [0.8, 0.7, 0.6, 0.5, 0.45, 0.4, 0.35, 0.3, 0.25, 0.25, 0.2]

for i, scene in enumerate(scenes):

    path = os.path.join(folder, scene)

    if not os.path.exists(path):
        print(f"SKIP missing: {path}")
        continue

    d = durations[i] if i < len(durations) else 0.2

    clip = (
        ImageClip(path)
        .with_duration(d)
        .resized(height=1280)
    )

    clips.append(clip)

if not clips:
    print("ERROR: no clips found")
    exit(1)

final = concatenate_videoclips(clips, method="compose")

final.write_videofile(
    "preview.mp4",
    fps=30,
    codec="libx264",
    audio=False
)

print("DONE: preview.mp4")
