import re, os, sys

DIR = os.path.dirname(os.path.abspath(__file__))
srt_files = ['cleaned_subs.srt'] if os.path.exists(os.path.join(DIR,'cleaned_subs.srt')) else [f for f in os.listdir(DIR) if f.startswith('source_video') and f.endswith('.srt')]
if not srt_files:
    print("No SRT found"); sys.exit(0)

srt_path = os.path.join(DIR, srt_files[0])
ass_path = os.path.join(DIR, 'subs.ass')

with open(srt_path, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# ASS header — small font, bottom center, fade-in effect
header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,16,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,20,20,25,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def srt_time_to_ass(t):
    t = t.replace(',', '.')
    h, m, s = t.split(':')
    s, ms = s.split('.')
    return f"{int(h)}:{m}:{s}.{ms[:2]}"

blocks = content.strip().split('\n\n')
events = []
for block in blocks:
    lines = block.strip().split('\n')
    if len(lines) < 3: continue
    time_line = lines[1]
    text_lines = ' '.join(lines[2:])
    # Remove sound effects
    text_lines = re.sub(r'\[[^\]]+\]', '', text_lines).strip()
    text_lines = text_lines.replace('♪','').replace('♫','').strip()
    if not text_lines: continue
    # Parse timestamps
    m = re.match(r'(\S+)\s+-->\s+(\S+)', time_line)
    if not m: continue
    start = srt_time_to_ass(m.group(1))
    end = srt_time_to_ass(m.group(2))
    # Add fade-in wave effect \fad(200,0) = fade in 200ms, no fade out
    text = text_lines.replace('\n', '\\N')
    events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\fad(200,0)}}{text}")

with open(ass_path, 'w', encoding='utf-8') as f:
    f.write(header + '\n'.join(events))

print(f"✅ ASS subtitles: {len(events)} lines → subs.ass")
