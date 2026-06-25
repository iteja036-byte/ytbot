import { execFileSync } from "child_process";
import fs from "fs";
import path from "path";

const base = process.cwd();
const data = JSON.parse(fs.readFileSync(path.join(base, "lines.json"), "utf8"));

// 1. Fixed regular expression string formatting
const caption = String(data.caption ?? "").replace(/[\r\n]+/g, " ").trim();
const captionFile = path.join(base, "caption.txt");
fs.writeFileSync(captionFile, caption, "utf8");

const musicDir = path.join(base, "music");
if (!fs.existsSync(musicDir)) fs.mkdirSync(musicDir, { recursive: true });

const musicFiles = fs.readdirSync(musicDir).filter(f => f.toLowerCase().endsWith(".mp3"));
if (!musicFiles.length) throw new Error("No music files found in ./music");

const randomMusic = musicFiles[Math.floor(Math.random() * musicFiles.length)];
const musicPath = path.join(musicDir, randomMusic);

// Check for target subtitle asset or default to empty fallback handling
const srtFile = "cleaned_subs.srt";
const subFilterString = fs.existsSync(path.join(base, srtFile)) 
  ? `[v2]subtitles=${srtFile}:force_style='FontName=Arial,FontSize=24,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=25'[v]`
  : `[v2]null[v]`;

const ffArgs = [
  "-y",
  "-i", "source_video.mp4",
  "-i", musicPath,
  "-filter_complex",
  [
    "[0:v]crop=in_w:in_h-80:0:80,scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280[bg]",
    "[0:v]crop=in_w:in_h-80:0:80,scale=720:900:force_original_aspect_ratio=decrease[fg]",
    "[bg]boxblur=18[blur]",
    "[blur][fg]overlay=(720-overlay_w)/2:180[v0]",
    "[v0]drawbox=x=0:y=0:w=720:h=150:color=black@1:t=fill[v1]",
    `[v1]drawtext=textfile=caption.txt:fontcolor=white:fontsize=32:fontfile=/system/fonts/Roboto-Bold.ttf:x=(w-text_w)/2:y=55[v2]`,
    subFilterString, // 2. Connected [v2] down to the final mapped video output label [v]
    "[1:a]volume=0.35,afade=t=in:d=1[music]",
    // 3. Sidechain compresses the music track down based on track 0 dialogue, then mixes them
    "[music][0:a]sidechaincompress=threshold=0.015:ratio=6:attack=50:release=350[ducked]",
    "[0:a]volume=1.0[dialogue]",
    "[dialogue][ducked]amix=inputs=2:duration=first:weights=1 1[a]"
  ].join(";"),
  "-map", "[v]",
  "-map", "[a]",
  "-t", "20",
  "-r", "30",
  "-c:v", "libx264",
  "-preset", "ultrafast",
  "-crf", "22",
  "-c:a", "aac",
  "-b:a", "128k",
  "video.mp4"
];

console.log("⚡ Compiling with execution array parameters...");
try {
  execFileSync("ffmpeg", ffArgs, { stdio: "inherit" });
  
  if (fs.existsSync("/sdcard/Download")) {
    execFileSync("cp", ["video.mp4", "/sdcard/Download/reel_ready.mp4"], { stdio: "inherit" });
    console.log("✅ DONE: Successfully exported to /sdcard/Download/reel_ready.mp4");
  } else {
    console.log("✅ DONE: Output generated cleanly in project directory space as video.mp4");
  }
} catch (err) {
  console.error("❌ FFmpeg operational failure encountered:", err.message);
  process.exit(1);
}
