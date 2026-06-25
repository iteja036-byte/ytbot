import os

# Ensure the clips directory exists
if not os.path.exists("clips"):
    print("Error: 'clips' directory not found.")
    exit()

# Get all files starting with "raw_"
raws = sorted([x for x in os.listdir("clips") if x.startswith("raw_")])

for i, f in enumerate(raws):
    print(f"PROCESS_CLIP [{i:02d}]: {f}")

    # -ss before -i for faster, accurate seeking when re-encoding
    # Added fps=30 (or change to 60 if you prefer) and fixed formatting quotes
    cmd = f'''ffmpeg -y \
-ss 5 \
-i "clips/{f}" \
-t 3 \
-vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30" \
-an \
"clips/clip_{i:02d}.mp4"'''

    os.system(cmd)

print("🔥 SCENES CUT & FORMATTED TO 9:16")

