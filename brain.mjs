import fs from "fs";
import Groq from "groq-sdk";

// -------------------- ENV LOADER --------------------
try {
  const env = fs.readFileSync(".env", "utf8");

  env.split("\n").forEach(line => {
    const [k, ...v] = line.split("=");
    if (k && v.length) {
      process.env[k.trim()] = v.join("=").trim();
    }
  });
} catch (err) {
  console.error("❌ .env file missing");
  process.exit(1);
}

// -------------------- GROQ INIT --------------------
const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY
});

// -------------------- INPUT --------------------
const userPrompt = process.argv[2] || "sad anime love story";

// -------------------- AI CALL --------------------
async function run() {
  try {
    const res = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      messages: [
        {
          role: "system",
          content: `
You generate VIRAL anime reel structure.

Return ONLY valid JSON.

Format:
{
  "caption1": "",
  "caption2": "",
  "tags": []
}

Rules:
- max 6 words per caption
- emotional + viral
- anime style
- no extra text
`
        },
        {
          role: "user",
          content: userPrompt
        }
      ],
      temperature: 1
    });

    const raw = res.choices[0].message.content;

    // -------------------- JSON SAFETY --------------------
    let parsed;

    try {
      parsed = JSON.parse(raw);
    } catch (e) {
      console.error("❌ AI returned invalid JSON");
      console.log(raw);
      process.exit(1);
    }

    fs.writeFileSync("brain.json", JSON.stringify(parsed, null, 2));

    console.log("✅ Brain generated:");
    console.log(parsed);

  } catch (err) {
    console.error("❌ Groq API failed:", err.message);
  }
}

run();
