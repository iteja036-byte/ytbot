import re
import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))

# Safely look for cleaned_subs.srt first, then fall back to any source_video srt file
srt_files = ['cleaned_subs.srt'] if os.path.exists(os.path.join(DIR, 'cleaned_subs.srt')) else [f for f in os.listdir(DIR) if f.startswith('source_video') and f.endswith('.srt')]

if not srt_files:
    print("⚠️ No SRT input subtitles found in workspace directory.")
    sys.exit(0)

srt_path = os.path.join(DIR, srt_files[0])
ass_path = os.path.join(DIR, 'subs.ass')

print(f"📖 Reading source subtitles from: {os.path.basename(srt_path)}")
with open(srt_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Completed V4+ Styles formatting row for exact alignment on 720x1280 canvas
header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,28,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,20,20,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# Fixed timestamp translator to isolate centiseconds flawlessly without splitting exceptions
def srt_time_to_ass(time_str):
    time_str = time_str.strip().replace(',', '.')
    if '.' not in time_str:
        time_str += '.000'
        
    parts = time_str.split(':')
    if len(parts) != 3:
        return "0:00:00.00"
        
    h = int(parts[0])
    m = parts[1]
    
    s_parts = parts[2].split('.')
    s = s_parts[0]
    ms = s_parts[1][:2] # ASS uses a 2-digit centisecond frame timing rule
    
    return f"{h}:{m}:{s}.{ms}"

# Explode blocks cleanly on double spacing newline breaks
blocks = re.split(r'\n\s*\n', content.strip())
events = []

for block in blocks:
    lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
    if len(lines) < 3:
        continue
        
    time_line = lines[1]
    text_lines = ' '.join(lines[2:])
    
    # Strip bracket/parentheses ambient noises descriptors
    text_lines = re.sub(r'\[[^\]]+\]', '', text_lines)
    text_lines = re.sub(r'\([^)]+\)', '', text_lines)
    text_lines = text_lines.replace('♪', '').replace('♫', '').strip()
    
    if not text_lines:
        continue
        
    # High-engagement uppercase clean styling
    text_lines = text_lines.upper()
    
    m = re.match(r'(\S+)\s+-->\s+(\S+)', time_line)
    if not m:
        continue
        
    try:
        start = srt_time_to_ass(m.group(1))
        end = srt_time_to_ass(m.group(2))
        
        # Inject an inline string token modifier for smooth text animations
        text = text_lines.replace('\n', '\\N')
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\fad(150,0)}}{text}")
    except Exception:
        continue

if events:
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(header + '\n'.join(events) + '\n')
    print(f"✅ ASS subtitles compiled successfully: {len(events)} lines → subs.ass")
else:
    print("❌ Processing Error: No subtitle tracks could be structured.")
