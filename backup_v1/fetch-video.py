import os
import sys
import subprocess
import glob

# Gather search query from command line args
query = " ".join(sys.argv[1:]).strip()
if not query:
    query = "anime edit"

print(f"🔍 SEARCHING YOUTUBE FOR: '{query}'")

# Clean up older source videos from previous runs to avoid false positives
for f in glob.glob("source_video*"):
    try:
        os.unlink(f)
    except OSError:
        pass

# Upgraded yt-dlp arguments
cmd = [
    "yt-dlp",
    f"ytsearch1:{query}",  # Download only the top single result to avoid filename collisions
    "--extractor-args", "youtube:player_client=android",
    # Download best video (up to 1080p) and best audio, then merge them into an MP4
    "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
    "--merge-output-format", "mp4",
    "--no-playlist",
    "-o", "source_video.%(ext)s"
]

try:
    # Run securely using subprocess instead of the outdated os.system
    subprocess.run(cmd, check=True)
except subprocess.CalledProcessError:
    print("❌ yt-dlp encountered an error during download.")

# Explicit check for the expected output file
if os.path.exists("source_video.mp4"):
    file_size = os.path.getsize("source_video.mp4") // (1024 * 1024)
    print(f"✅ DOWNLOADED SUCCESSFULLY ({file_size} MB)")
else:
    print("❌ FAILED: 'source_video.mp4' was not created.")

