export class BrainV6 {
  constructor({ memory, scorer, validator }) {
    this.memory = memory;
    this.scorer = scorer;
    this.validator = validator;
  }

  analyze(input) {
    return {
      mood: input.includes("love") ? "romance" : "sad",
      intensity: input.length
    };
  }

  async run(input) {
    const clean = this.validator.clean(input);

    const analysis = this.analyze(clean);

    const candidates = await this.memory.getCandidates(clean);

    const trend = this.memory.getEmotionTrend();

    const scored = candidates.map(c => {
      let score = this.scorer.score(c, clean);

      // 🔥 director bias from history
      const past = trend[c.emotion]?.score || 0;
      const count = trend[c.emotion]?.count || 1;

      const memoryBoost = past / count;

      score += memoryBoost * 0.5;

      return {
        ...c,
        score,
        memoryBoost
      };
    });

    scored.sort((a, b) => b.score - a.score);

    const best = scored[0];

    const output = {
      caption: best.text,
      emotion: best.emotion,
      score: best.score,
      analysis,
      memoryBoost: best.memoryBoost
    };

    this.memory.store({
      input: clean,
      output
    });

    return output;
  }
}
