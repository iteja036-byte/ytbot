import fs from "fs";
import Groq from "groq-sdk";
import glob from "glob";

const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY
});

const inputFile = glob.sync("cleaned_subs_v7_viral.srt")[0];

if (!inputFile) {
  console.log("❌ Missing input file");
  process.exit(1);
}

const content = fs.readFileSync(inputFile, "utf8");
const blocks = content.split(/\n\s*\n/);

let idx = 1;

// ---------------- AI DIRECTOR ----------------
async function analyzeScene(text, position) {
  try {
    const res = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      messages: [
        {
          role: "system",
          content: `
You are a viral video director AI.

Analyze subtitle scene and return ONLY JSON:

{
  "emotion": "love|sad|anger|neutral",
  "role": "hook|build|climax|end",
  "viral_score": 1-10,
  "intensity": 1-10
}

Rules:
- Hook = first attention grabbing line
- Climax = emotional peak
- Build = story development
- End = closure
`
        },
        {
          role: "user",
          content: text
        }
      ],
      temperature: 0.5
    });

    return JSON.parse(res.choices[0].message.content);

  } catch (e) {
    // fallback system (important)
    return {
      emotion: "neutral",
      role: position < 2 ? "hook" : "build",
      viral_score: 5,
      intensity: 5
    };
  }
}

// ---------------- MAIN ----------------
async function run() {
  let output = [];
  let position = 0;

  for (const block of blocks) {
    const lines = block.trim().split("\n");
    if (lines.length < 3) continue;

    const timecode = lines[1];
    const text = lines.slice(2).join(" ").trim();

    if (!text) continue;

    const ai = await analyzeScene(text, position);

    let boost = 1;

    if (ai.role === "hook") boost = 2.0;
    if (ai.role === "climax") boost = 1.8;

    const finalScore = (ai.viral_score + ai.intensity) * boost;

    output.push(
      `${idx}\n${timecode}\n${text} [${ai.role}|${ai.emotion}|${finalScore.toFixed(1)}]\n`
    );

    idx++;
    position++;
  }

  fs.writeFileSync("cleaned_subs_v8_director.srt", output.join("\n"));

  console.log("✅ Brain v8 AI Director created");
  console.log(`Segments: ${idx - 1}`);
}

run();
