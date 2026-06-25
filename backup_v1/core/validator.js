export const validator = {
  clean(input) {
    if (!input) return "sad";
    return String(input)
      .toLowerCase()
      .replace(/[^a-z ]/g, "")
      .trim();
  }
};
