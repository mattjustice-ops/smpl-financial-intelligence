const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const frontend = path.join(__dirname, "..", "frontend");
const out = path.join(__dirname, "..", "typecheck-log.txt");

try {
  const result = execSync("npm run build", {
    cwd: frontend,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    maxBuffer: 10 * 1024 * 1024,
  });
  fs.writeFileSync(out, result, "utf8");
} catch (error) {
  const text = `${error.stdout || ""}\n${error.stderr || ""}\nEXIT: ${error.status}`;
  fs.writeFileSync(out, text, "utf8");
}
