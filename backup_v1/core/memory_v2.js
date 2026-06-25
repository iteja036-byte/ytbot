export const memory = {
  store: async (data) => {
    console.log("MEMORY STORED:", data.caption || data.output?.text);
  },

  getCandidates: async () => {
    return [
      { text: "Some love stories end before they begin", emotion: "heartbreak", intensity: 9 },
      { text: "I still feel you in empty silence", emotion: "missing-you", intensity: 7 },
      { text: "Heart beats louder when you're gone", emotion: "sad-love", intensity: 8 }
    ];
  }
};
