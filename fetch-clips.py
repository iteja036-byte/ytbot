import os
import shutil

# Using expanduser guarantees it handles the home directory (~) across Unix/Linux systems
SRC = os.path.expanduser("~/ytbot/myclips")
DST = os.path.expanduser("~/ytbot/clips")

# Step 1: Clean or create the destination directory safely
if os.path.exists(DST):
    # Deletes the entire directory tree (files AND folders) to guarantee a 100% clean slate
    shutil.rmtree(DST)
os.makedirs(DST, exist_ok=True)

# Step 2: Gather and sort the generated mp4 files
if not os.path.exists(SRC):
    print(f"❌ Error: Source directory {SRC} does not exist!")
    exit(1)

videos = sorted([
    x for x in os.listdir(SRC)
    if x.lower().endswith(".mp4")  # .lower() catches .MP4 edge cases
])

# Step 3: Select the top 8 clips
selected = videos[:8]

if not selected:
    print("⚠ No .mp4 files found in the source directory.")
    exit()

print(f"Staging {len(selected)} clips for final export...\n")

# Step 4: Copy and rename files sequentially
for i, v in enumerate(selected):
    src_path = os.path.join(SRC, v)
    dst_path = os.path.join(DST, f"clip_{i:02d}.mp4")

    # shutil.copy2 preserves original file metadata (creation/modification time)
    shutil.copy2(src_path, dst_path)
    print(f"✅ Staged: {v} -> clip_{i:02d}.mp4")

print("\n🔥 BATCH READY FOR PRODUCTION")

