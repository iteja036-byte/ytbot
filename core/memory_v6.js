const memory = [];

const defaultCandidates = [
  { text: "Some love stories end before they begin", emotion: "heartbreak", intensity: 9 },
  { text: "I still feel you in empty silence", emotion: "missing-you", intensity: 7 },
  { text: "Heart beats louder when you're gone", emotion: "sad-love", intensity: 8 },
  { text: "We were never meant to last forever", emotion: "sad-love", intensity: 8 }
];

export const memoryV6 = {
  store(entry) {
    memory.push({
      ...entry,
      timestamp: Date.now()
    });
  },

  getAll() {
    return memory;
  },

  // ✅ FIX: this was missing
  async getCandidates(input) {
    // later we can make this dynamic learning
    return defaultCandidates;
  },

  getEmotionTrend() {
    const trend = {};

    for (const m of memory) {
      const e = m.output?.emotion;
      const s = m.output?.score || 0;

      if (!e) continue;

      if (!trend[e]) trend[e] = { count: 0, score: 0 };

      trend[e].count += 1;
      trend[e].score += s;
    }

    return trend;
  }
};
