#!/bin/bash

echo "🎬 YTBOT PIPELINE - MASTER RUNNER"
echo "================================="

# Clean old outputs
rm -rf output/*.mp4 2>/dev/null
rm -rf /sdcard/Download/reel_ready.mp4 2>/dev/null

# Run pipeline
echo "📹 Running video compilation..."
python3 main.py

# Copy video to output folder
if [ -f "/sdcard/Download/reel_ready.mp4" ]; then
    cp /sdcard/Download/reel_ready.mp4 output/final-video.mp4
    echo "✅ Video saved to: output/final-video.mp4"
fi

ls -lh output/
