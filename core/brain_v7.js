export class BrainV7 {
  constructor({ memory, scorer, validator }) {
    this.memory = memory;
    this.scorer = scorer;
    this.validator = validator;
  }

  detectHook(text) {
    const hooks = ["you", "when", "why", "i", "she", "he", "we"];

    const words = text.toLowerCase().split(" ");
    const first = words.slice(0, 3).join(" ");

    let hookScore = 0;

    for (const h of hooks) {
      if (first.includes(h)) hookScore += 1;
    }

    return hookScore;
  }

  simulateRetention(caption) {
    const len = caption.text.length;

    let retention = 10;

    if (len < 30) retention += 5;
    if (len > 60) retention -= 3;

    if (caption.emotion === "heartbreak") retention += 4;
    if (caption.emotion === "missing-you") retention += 3;

    return retention;
  }

  async run(input) {
    const clean = this.validator.clean(input);

    const candidates = await this.memory.getCandidates(clean);

    const stats = this.memory.getEmotionStats();

    const scored = candidates.map(c => {
      let base = this.scorer.score(c, clean);

      const hook = this.detectHook(c.text);
      const retention = this.simulateRetention(c);

      const past = stats[c.emotion]?.score || 0;

      const viralScore =
        base +
        hook * 2 +
        retention +
        past * 0.3;

      return {
        ...c,
        hookScore: hook,
        retentionScore: retention,
        viralScore
      };
    });

    scored.sort((a, b) => b.viralScore - a.viralScore);

    const best = scored[0];

    this.memory.store({
      input: clean,
      output: best
    });

    return {
      caption: best.text,
      emotion: best.emotion,
      viralScore: best.viralScore,
      hookScore: best.hookScore,
      retentionScore: best.retentionScore,
      reason: "viral director selection"
    };
  }
}
