import fs from "fs";

const FILE = "core/memory.json";

export function loadMemory() {
  return JSON.parse(fs.readFileSync(FILE, "utf8"));
}

export function saveMemory(data) {
  fs.writeFileSync(FILE, JSON.stringify(data, null, 2));
}

export function logResult(entry) {
  const mem = loadMemory();

  mem.history.push({ ...entry, time: Date.now() });

  if (mem.history.length > 100) {
    mem.history = mem.history.slice(-100);
  }

  saveMemory(mem);
}

// 🧠 REAL LEARNING ENGINE
export function getEmotionWeights() {
  const mem = loadMemory();

  const stats = {};

  for (const h of mem.history) {
    const e = h.emotion;
    if (!stats[e]) stats[e] = { count: 0, score: 0 };

    stats[e].count += 1;
    stats[e].score += h.viral_score || 0;
  }

  const weights = {};

  for (const [emotion, v] of Object.entries(stats)) {
    const avg = v.score / v.count;

    // normalize learning signal
    weights[emotion] = avg * Math.log(v.count + 1);
  }

  return weights;
}
