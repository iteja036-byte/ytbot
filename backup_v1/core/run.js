import dotenv from "dotenv";
import BrainV7 from "./brain_v7.js";
import { createMemory } from "./memory.js";

dotenv.config();

const withApp = async (input) => {
  const memory = createMemory();
  const brain = new BrainV7({ memory });

  return await brain.run(input);
};

const run = async () => {
  const input = process.argv.slice(2).join(" ") || "sad romance";

  console.log("ENV CHECK:", !!process.env.GROQ_API_KEY);
  console.log("\n🚀 INPUT:", input);

  try {
    const output = await withApp(input);

    console.log("\n🎬 VIRAL DIRECTOR OUTPUT:");
    console.log(JSON.stringify(output, null, 2));
  } catch (err) {
    console.error("\n❌ ERROR:", err.message);
  }
};

run();
