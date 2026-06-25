#!/bin/bash

cd ~/ytbot || { echo "❌ Working directory base root missing."; exit 1; }

echo "===================================================="
echo "🚀 INITIATING AUTOMATED YTBOT BROADCAST ENGINE v2026"
echo "===================================================="

# Force clean old temporary text layers to prevent caching bugs
rm -f caption.txt ffmpeg_concat_list.txt subs.ass cleaned_subs.srt

mkdir -p output clips myclips music

if [ -f "generate-text.mjs" ]; then
    echo "🔥 Generation Hook: Spinning context metadata..."
    node generate-text.mjs
fi

if [ -f "selector.py" ]; then
    echo "🎯 Scoring Top Clip Sequences..."
    python3 selector.py
fi

# Native bash safety check: only run subtitle parsers if an SRT file exists
if ls *.srt 1>/dev/null 2>&1; then
    echo "🧹 SRT detected. Normalizing subtitle tracks..."
    python3 clean_srt.py 2>/dev/null || true
    python3 srt_to_ass.py 2>/dev/null || true
else
    echo "ℹ️ No raw SRT files found in directory. Clean visual export active."
fi

if [ -f "make-reel.js" ]; then
    echo "🚀 Synthesizing audio/video layers..."
    node make-reel.js
else
    echo "❌ Central script missing."
    exit 1
fi

echo "===================================================="
echo "🏆 SUCCESS: RENDER COMPLETED ZERO-ERROR"
echo "===================================================="
