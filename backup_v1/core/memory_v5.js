const memory = [];

export const memoryV5 = {
  store(entry) {
    memory.push({
      ...entry,
      timestamp: Date.now()
    });
  },

  getAll() {
    return memory;
  },

  getEmotionWeights() {
    const weights = {};

    for (const m of memory) {
      const emotion = m.output?.emotion;
      const score = m.output?.score || 0;

      if (!emotion) continue;

      weights[emotion] = (weights[emotion] || 0) + score;
    }

    return weights;
  },

  getBias(emotion) {
    const weights = this.getEmotionWeights();
    const total = Object.values(weights).reduce((a, b) => a + b, 0) || 1;

    return (weights[emotion] || 0) / total;
  }
};
