export class BrainV5 {
  constructor({ memory, scorer, validator }) {
    this.memory = memory;
    this.scorer = scorer;
    this.validator = validator;
  }

  async run(input) {
    const clean = this.validator.clean(input);

    const candidates = await this.memory.getCandidates(clean);

    const weights = this.memory.getEmotionWeights();

    const scored = candidates.map(c => {
      const baseScore = this.scorer.score(c, clean);

      // 🔥 learning boost
      const emotionWeight = weights[c.emotion] || 1;

      return {
        ...c,
        score: baseScore * (1 + emotionWeight * 0.1)
      };
    });

    scored.sort((a, b) => b.score - a.score);

    const best = scored[0];

    this.memory.store({
      input: clean,
      output: best
    });

    return {
      caption: best.text,
      emotion: best.emotion,
      score: best.score,
      learning_applied: true
    };
  }
}
