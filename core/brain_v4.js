export class BrainV4 {
  constructor({ memory, scorer, validator }) {
    this.memory = memory;
    this.scorer = scorer;
    this.validator = validator;
  }

  async run(input) {
    const safeInput = this.validator.clean(input);

    const candidates = await this.memory.getCandidates(safeInput);

    const scored = candidates.map(c => ({
      ...c,
      score: this.scorer.score(c, safeInput)
    }));

    scored.sort((a, b) => b.score - a.score);

    const best = scored[0];

    if (!best) {
      return {
        status: "fail",
        reason: "no candidates"
      };
    }

    await this.memory.store({
      input: safeInput,
      output: best,
      timestamp: Date.now()
    });

    return {
      caption: best.text,
      emotion: best.emotion,
      score: best.score,
      memory_used: true
    };
  }
}
