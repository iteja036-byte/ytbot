import json
import os
import sys
import subprocess
import glob

DIR = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(DIR, 'lines.json')

# Ensure JSON exists or mock it for safety
if os.path.exists(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
else:
    data = {}

# 1. Fixed truncated fallback query string
query = data.get('search') or data.get('query') or data.get('searchQuery') or "Trending Anime Scene"
print(f"🔍 Searching YouTube for: '{query}'")

# Clean up previous runs safely
for f in glob.glob(os.path.join(DIR, 'source_video*')):
    try:
        os.unlink(f)
    except OSError:
        pass

out_base = os.path.join(DIR, 'source_video')

# 2. Fixed truncated format string to cleanly grab 720p MP4 combinations
cmd = [
    'yt-dlp',
    '--js-runtimes', 'node',
    f'ytsearch1:{query}',
    '-f', 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]',
    '--merge-output-format', 'mp4',
    '--write-auto-subs', '--sub-lang', 'en', '--convert-subs', 'srt',
    '-o', f'{out_base}.%(ext)s',
    '--no-playlist', '--quiet', '--progress',
    '--sleep-requests', '3'
]

print("⏳ Downloading via yt-dlp...")
subprocess.run(cmd, cwd=DIR)

# 3. Cleaned up exact file checking instead of using glob for static names
expected_video = os.path.join(DIR, 'source_video.mp4')

if not os.path.exists(expected_video):
    print("❌ ERROR: Download failed or file was not merged to MP4.")
    sys.exit(1)

size_mb = os.path.getsize(expected_video) // (1024 * 1024)
print(f"✅ Video Downloaded: {size_mb}MB")

# Locate downloaded subtitles
subs = glob.glob(os.path.join(DIR, 'source_video*.srt'))
if subs:
    print(f"✅ Subtitles Saved: {os.path.basename(subs[0])

