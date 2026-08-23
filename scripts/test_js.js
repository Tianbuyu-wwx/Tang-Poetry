const fs = require("fs");
const path = require("path");
const target = path.resolve(__dirname, "..", "website", "assets", "js", "poets-data.js");
const code = fs.readFileSync(target, "utf8");
try {
  new Function(code);
  console.log(`JS OK: ${target}`);
} catch (e) {
  console.error("JS ERROR:", e.message);
  process.exitCode = 1;
}
