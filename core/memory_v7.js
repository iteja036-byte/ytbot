const memory = [];

const defaultCandidates = [
  { text: "Some love stories end before they begin", emotion: "heartbreak", intensity: 9 },
  { text: "I still feel you in empty silence", emotion: "missing-you", intensity: 7 },
  { text: "Heart beats louder when you're gone", emotion: "sad-love", intensity: 8 },
  { text: "We were never meant to last forever", emotion: "sad-love", intensity: 8 }
];

export const memoryV7 = {
  store(entry) {
    memory.push({
      ...entry,
      timestamp: Date.now()
    });
  },

  getAll() {
    return memory;
  },

  // ✅ REQUIRED FIX
  async getCandidates(input) {
    return defaultCandidates;
  },

  getEmotionStats() {
    const stats = {};

    for (const m of memory) {
      const e = m.output?.emotion;
      const score = m.output?.viralScore || 0;

      if (!e) continue;

      if (!stats[e]) stats[e] = { count: 0, score: 0 };

      stats[e].count += 1;
      stats[e].score += score;
    }

    return stats;
  }
};
