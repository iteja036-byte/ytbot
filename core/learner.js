import fs from "fs";

const PATH = "data/learning.json";

// ----------------------
// LOAD MEMORY
// ----------------------
export function loadMemory() {
  return JSON.parse(fs.readFileSync(PATH, "utf8"));
}

// ----------------------
// SAVE MEMORY
// ----------------------
export function saveMemory(data) {
  fs.writeFileSync(PATH, JSON.stringify(data, null, 2));
}

// ----------------------
// UPDATE WEIGHTS (REAL LEARNING)
// ----------------------
export function updateLearning(memory, result) {

  const emotion = result.emotion;
  const score = result.viral_score;

  memory.history.push({
    emotion,
    score,
    caption: result.caption,
    time: Date.now()
  });

  // limit memory size
  if (memory.history.length > 50) {
    memory.history.shift();
  }

  // adjust weights (simple reinforcement learning)
  if (!memory.emotion_weights[emotion]) {
    memory.emotion_weights[emotion] = 1.0;
  }

  if (score > 8) {
    memory.emotion_weights[emotion] += 0.1;
  } else if (score < 5) {
    memory.emotion_weights[emotion] -= 0.05;
  }

  // clamp values
  memory.emotion_weights[emotion] =
    Math.max(0.5, Math.min(3.0, memory.emotion_weights[emotion]));

  saveMemory(memory);
}
