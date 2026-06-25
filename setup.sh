#!/bin/bash
echo "Installing dependencies..."
pip install edge-tts groq requests --break-system-packages
cd ~/ytbot
npm install groq
pkg install cronie -y
echo "✅ Done! Now edit ~/ytbot/.env"
