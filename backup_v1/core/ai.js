import Groq from "groq-sdk";

const groq = new Groq({
  apiKey: process.env.GROQ_API_KEY
});

export async function aiSelectCaption(captions, mood = "sad") {

  const res = await groq.chat.completions.create({
    model: "llama-3.3-70b-versatile",
    messages: [
      {
        role: "system",
        content: `
You are a STRICT JSON generator.

RULES:
- Output ONLY valid JSON
- No text before or after
- No explanations
- No markdown

FORMAT:
{
  "index": 0,
  "reason": "short reason"
}
`
      },
      {
        role: "user",
        content: `
Pick best caption index for mood: ${mood}

CAPTIONS:
${JSON.stringify(captions, null, 2)}
`
      }
    ],
    temperature: 0.3
  });

  const text = res.choices[0].message.content.trim();

  // SAFE PARSE (prevents crash)
  try {
    return JSON.parse(text);
  } catch (e) {
    console.log("⚠️ RAW MODEL OUTPUT:", text);

    // fallback system
    return {
      index: 0,
      reason: "fallback due to invalid JSON"
    };
  }
}

export function viralScore(caption) {
  const base = caption.intensity || 5;

  const boost = {
    "heartbreak": 2,
    "sad-love": 1.5,
    "missing-you": 1.2
  };

  return base * (boost[caption.emotion] || 1);
}
