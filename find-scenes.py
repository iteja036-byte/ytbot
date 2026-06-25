import os
import re
import subprocess

video_input = "source_video.mp4"

if not os.path.exists(video_input):
    print(f"❌ Error: '{video_input}' not found in the current directory.")
    exit(1)

print("🎬 Analyzing video for scene changes...")

# Upgrade: Use subprocess to run FFmpeg and capture logs directly in memory
# We use 'showinfo' inside filter_complex because it reliably prints 'pts_time'
cmd = [
    "ffmpeg", "-i", video_input,
    "-filter_complex", "select='gt(scene,0.4)',showinfo",
    "-f", "null", "-"
]

# Run command and pipe stderr (where FFmpeg prints its packet information)
result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

# Fixed Regex: Using a raw string r'' and matching 'pts_time:XX.XX' accurately
matches = re.findall(r"pts_time:(\d+\.\d+)", result.stderr)

# Convert string timestamps to unique, sorted float numbers
# (Using set() removes any duplicate frame logs from the same scene boundary)
times = sorted(list(set([float(m) for m in matches])))

print("\n🚀 SCENES DETECTED:")
if not times:
    print("No drastic scene cuts found. Try lowering the threshold (e.g., to 0.3)")
else:
    # Limit to the first 12 scene cuts as requested
    for i, t in enumerate(times[:12]):
        print(f"Scene {i:02d} => {round(t, 2)} sec")

