import { execFileSync } from "child_process";
import fs from "fs";
import path from "path";

const base = process.cwd();
const linesPath = path.join(base, "lines.json");
if (!fs.existsSync(linesPath)) {
  throw new Error("❌ lines.json is missing.");
}
const data = JSON.parse(fs.readFileSync(linesPath, "utf8"));

const caption = String(data.caption ?? "").replace(/[\r\n]+/g, " ").trim();
const captionFile = path.join(base, "caption.txt");
fs.writeFileSync(captionFile, caption, "utf8");

const chosenPath = path.join(base, "chosen.txt");
const targetClips = fs.readFileSync(chosenPath, "utf8")
  .split("\n")
  .map(line => line.trim())
  .filter(line => line.length > 0);

let isConcatFlow = targetClips.length > 0;
let concatListFile = path.join(base, "ffmpeg_concat_list.txt");

if (isConcatFlow) {
  let concatContent = "";
  targetClips.forEach(clipPath => {
    concatContent += `file '${clipPath.replace(/'/g, "'\\''")}'\n`;
  });
  fs.writeFileSync(concatListFile, concatContent, "utf8");
}

const musicDir = path.join(base, "music");
const musicFiles = fs.readdirSync(musicDir).filter(f => f.toLowerCase().endsWith(".mp3"));
if (musicFiles.length === 0) {
  throw new Error("❌ No background music files found in music directory.");
}
const randomMusic = musicFiles[Math.floor(Math.random() * musicFiles.length)];
const musicPath = path.join(musicDir, randomMusic);

const finalVideoPath = path.join(base, "output", "final-video.mp4");

let ffArgs = ["-y"];
if (isConcatFlow) {
  ffArgs.push("-f", "concat", "-safe", "0", "-i", concatListFile);
} else {
  ffArgs.push("-i", "source_video.mp4");
}
ffArgs.push("-i", musicPath);

ffArgs.push("-filter_complex", [
  "[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,boxblur=25[bg_blurred]",
  "[0:v]scale=720:-1[fg_scaled]",
  "[bg_blurred][fg_scaled]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[base_video]",
  "[base_video]drawbox=x=0:y=0:w=720:h=160:color=black@0.65:t=fill[video_with_banner]",
  `[video_with_banner]drawtext=textfile=caption.txt:fontcolor=white:fontsize=28:fontfile=/system/fonts/Roboto-Bold.ttf:x=(w-text_w)/2:y=(160-text_h)/2[v]`,
  "[1:a]volume=0.85,afade=t=in:d=1[a]"
].join(";"));

ffArgs.push(
  "-map", "[v]",
  "-map", "[a]",
  "-t", "15",
  "-r", "30",
  "-c:v", "libx264",
  "-preset", "faster",
  "-crf", "20",
  "-c:a", "aac",
  "-b:a", "128k",
  finalVideoPath
);

try {
  console.log("🎬 Processing clean canvas rendering sequence via FFmpeg pipeline...");
  execFileSync("ffmpeg", ffArgs, { stdio: "inherit" });
  console.log(`🚀 MASTER VIDEO PRO-RENDER SUCCESSFUL -> ${finalVideoPath}`);
} catch (err) {
  console.error("❌ Process failure:", err.message);
} finally {
  if (fs.existsSync(concatListFile)) fs.unlinkSync(concatListFile);
}
