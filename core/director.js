import { aiSelectCaption, viralScore } from "./ai.js";
import { logResult, getEmotionWeights } from "./memory.js";

export async function runDirector(data, mood = "sad") {

  const weights = getEmotionWeights();

  const decision = await aiSelectCaption(data.captions, mood);

  const selected = data.captions[decision.index];

  let score = viralScore(selected);

  // 🧠 MEMORY BOOST (LEARNING EFFECT)
  const memoryBoost = weights[selected.emotion] || 1;

  score = score * memoryBoost;

  const output = {
    caption: selected.text,
    emotion: selected.emotion,
    viral_score: score,
    reason: decision.reason,
    memory_boost: memoryBoost
  };

  logResult(output);

  return output;
}
