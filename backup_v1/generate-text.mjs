import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

// Fix for __dirname when using standard ES modules (import) in Node.js
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const characters = [
  "Goku", "Gojo", "Sukuna", "Levi", 
  "Eren", "Naruto", "Itachi", "Zoro", 
  "Luffy", "Thor", "Spider-Man", "Tony Stark"
];

const character = characters[Math.floor(Math.random() * characters.length)];

// Upgraded queries optimized for high-retention video tags
const queries = [
  `${character} vertical edit`,
  `${character} aura edit 4k`,
  `${character} badass moments high quality`,
  `${character} emotional fight scene`,
  `${character} cold moments`,
  `${character} raw power edit`
];

// Upgraded high-engagement TikTok/Shorts style captions
const captions = [
  `POV: You realized ${character} wasn't bluffing... 💀`,
  `${character} genuinely has unlimited aura.`,
  `The storyline belongs to ${character} now.`,
  `Bro decided to absolute menace to society 🥶`,
  `They really thought they could step to ${character} 😭`
];

const selected = {
  character,
  query: queries[Math.floor(Math.random() * queries.length)],
  caption: captions[Math.floor(Math.random() * captions.length)],
  timestamp: new Date().toISOString()
};

// Explicitly use path.join to ensure it writes to the correct automation directory
const outputPath = path.join(__dirname, "lines.json");

try {
  fs.writeFileSync(outputPath, JSON.stringify(selected, null, 2), "utf-8");
  console.log("🔥 METADATA GENERATED SUCCESSFULLY:");
  console.log(selected);
} catch (error) {
  console.error("❌ Failed to write lines.json:", error);
}

