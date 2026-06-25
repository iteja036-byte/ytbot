#!/bin/bash

# Navigate to working directory
cd ~/ytbot || { echo "❌ Directory ~/ytbot not found!"; exit 1; }

echo "========================================"
echo "🚀 STARTING AUTOMATED VIDEO PIPELINE"
echo "========================================"

# Step 1: Run your subtitle processing converter if needed
if [ -f "srt_to_ass.py" ]; then
    echo "📜 Step 1: Converting SRT subtitles to ASS format..."
    python3 srt_to_ass.py
else
    echo "⚠️ srt_to_ass.py not found, skipping subtitle preprocess..."
fi

# Step 2: Compile the vertical video sequence
if [ -f "make-reel.js" ]; then
    echo "🎬 Step 2: Compiling vertical video with FFmpeg..."
    node make-reel.js
else
    echo "❌ Error: make-reel.js is missing. Aborting."
    exit 1
fi

echo "========================================"
echo "🔥 PIPELINE RUN ATTEMPT COMPLETE!"
echo "========================================"
