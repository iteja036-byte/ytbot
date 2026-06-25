#!/bin/bash

cd ~/ytbot

SRC=$(ls source_video.* 2>/dev/null | head -1)

if [ -z "$SRC" ]; then
  echo "ERROR: No source video found"
  exit 1
fi

echo "Cutting: $SRC"

DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$SRC")
DURATION=${DURATION%.*}

echo "Duration: ${DURATION}s"

mkdir -p myclips
rm -f myclips/*.mp4

COUNT=0

# Skip first 5 seconds, cut every 3 seconds
for ((START=5; START<=DURATION-3; START+=3)); do

  OUT="myclips/clip_$(printf '%03d' $COUNT).mp4"

  ffmpeg -y -ss $START -i "$SRC" -t 3 \
    -vf "scale=1080:1380:force_original_aspect_ratio=increase,crop=1080:1380" \
    -c:v libx264 -preset ultrafast -crf 28 -an "$OUT"

  COUNT=$((COUNT+1))

  echo -ne "Clips: $COUNT\r"

done

echo ""
echo "DONE → $COUNT clips created"
