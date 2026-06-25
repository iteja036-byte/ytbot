import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Lock it to Gojo since your current media assets are Gojo-focused
const character = "Gojo";

const captions = [
  `POV: You realized ${character} wasn't bluffing... 💀`,
  `${character} genuinely has unlimited aura. 🥶`,
  `The storyline belongs to ${character} now.`,
  `Bro decided to be an absolute menace to society`
];

const selected = {
  character,
  query: `${character} vertical edit`,
  caption: captions[Math.floor(Math.random() * captions.length)],
  timestamp: new Date().toISOString()
};

const outputPath = path.join(__dirname, "lines.json");

try {
  fs.writeFileSync(outputPath, JSON.stringify(selected, null, 2), "utf-8");
  console.log("🔥 METADATA LOCKED GENERATED SUCCESSFULLY:");
  console.log(selected);
} catch (error) {
  console.error("❌ Failed to write lines.json:", error);
}
