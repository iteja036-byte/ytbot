#!/bin/bash
cd ~/ytbot || exit 1
mkdir -p myclips
rm -f myclips/*.mp4

# 1. Fixed the truncated ffprobe command to get total duration cleanly
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 anime_raw.mp4)

# Round the duration down to an integer for the seq command
DURATION_INT=${DURATION%.*}
echo "Total Duration: ${DURATION_INT}s"

COUNT=0

# Loop in steps of 3 seconds
for START in $(seq 0 3 "$DURATION_INT"); do
  # Check if remaining time is too short to bother cutting
  if [ "$START" -ge "$DURATION_INT" ]; then
    break
  fi

  OUT="myclips/clip_$(printf '%03d' $COUNT).mp4"
  
  # 2. Fixed the truncated -vf string and added fps=30 for stability
  # 3. Placed -ss before -i for lightning-fast seeking
  ffmpeg -y -ss "$START" -i anime_raw.mp4 -t 3 \
    -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30" \
    -c:v libx264 -preset ultrafast -crf 28 -an "$OUT" 2>/dev/null
    
  echo "✅ Saved: $OUT (Start: ${START}s)"
  COUNT=$((COUNT+1))
done

echo "🔥 Process Finished: Created $COUNT vertical clips!"

