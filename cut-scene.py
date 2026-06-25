import os
import subprocess
import re

# Ensure output directory exists
output_dir = "clips"
os.makedirs(output_dir, exist_ok=True)

video_input = "source_video.mp4"
threshold = 0.45  # Match your original scene detection sensitivity

print("Analyzing video for scene changes... (This may take a moment)")

# Step 1: Run FFmpeg to find scene change timestamps
# We use ffprobe/ffmpeg to output log info without writing heavy files yet
cmd_detect = [
    "ffmpeg", "-i", video_input,
    "-filter_complex", f"select='gt(scene,{threshold})',showinfo",
    "-f", "null", "-"
]

# Capture the FFmpeg output text
result = subprocess.run(cmd_detect, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

# Step 2: Extract timestamps using regex from the 'showinfo' log
# Look for patterns like pts_time:12.345
timestamps = [0.0]  # Start at the beginning of the video
matches = re.findall(r"pts_time:(\d+\.\d+)", result.stderr)

for match in matches:
    timestamps.append(float(match))

# Remove duplicates and sort
timestamps = sorted(list(set(timestamps)))
print(f"Detected {len(timestamps) - 1} scene cuts at timestamps: {timestamps[1:]}")

# Step 3: Cut the video into individual .mp4 clips based on those timestamps
for i in range(len(timestamps)):
    start_time = timestamps[i]
    
    # If it's the last scene, let it run to the end of the video
    if i == len(timestamps) - 1:
        # Check if the last segment is too short to bother cutting
        break 
    else:
        end_time = timestamps[i + 1]
        duration = end_time - start_time
    
    # Format file name to match your JSON (e.g., clip_00.mp4, clip_01.mp4)
    output_file = os.path.join(output_dir, f"clip_{i:02d}.mp4")
    
    # Fast seek (-ss before -i) and stream copy (-c copy) for instant, lossless cutting
    cmd_cut = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", video_input,
        "-t", str(duration),
        "-c", "copy",  # Fast execution without re-encoding
        output_file
    ]
    
    subprocess.run(cmd_cut, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Generated: {output_file} ({start_time:.2f}s -> {end_time:.2f}s)")

print("\nDONE! All clips successfully generated.")

