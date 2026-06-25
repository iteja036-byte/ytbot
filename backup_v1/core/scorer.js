export const scorer = {
  score(caption, input) {
    let base = caption.intensity || 5;

    const boost = {
      "heartbreak": 2.2,
      "sad-love": 1.6,
      "missing-you": 1.3
    };

    return base * (boost[caption.emotion] || 1);
  }
};
