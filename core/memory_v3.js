let memory = [];

export const memoryV3 = {
  store(entry) {
    memory.push({
      ...entry,
      timestamp: Date.now()
    });
  },

  getAll() {
    return memory;
  },

  getWeighted() {
    // boost frequently successful emotions
    const weights = {};

    for (const m of memory) {
      const e = m.output?.emotion;
      const score = m.output?.score || 0;

      weights[e] = (weights[e] || 0) + score;
    }

    return weights;
  }
};
