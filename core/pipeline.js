import { execSync } from "child_process";

// ----------------------
// AUTO VIDEO ENGINE
// ----------------------
export function runPipeline() {
  console.log("🎬 Running autonomous pipeline...");

  try {
    execSync("bash run.sh", { stdio: "inherit" });
  } catch (err) {
    console.error("❌ Pipeline failed:", err.message);
  }
}
