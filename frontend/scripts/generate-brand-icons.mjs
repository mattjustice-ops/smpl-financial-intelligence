/**
 * Regenerate PNG favicons from public/brand/smpl-logo.svg
 * Run: node scripts/generate-brand-icons.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Resvg } from "@resvg/resvg-js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const brandDir = path.join(__dirname, "..", "public", "brand");
const appDir = path.join(__dirname, "..", "app");
const svg = fs.readFileSync(path.join(brandDir, "smpl-logo.svg"));

function writePng(size, filename) {
  const resvg = new Resvg(svg, { fitTo: { mode: "width", value: size } });
  const png = resvg.render().asPng();
  fs.writeFileSync(path.join(brandDir, filename), png);
  console.log(`wrote ${filename} (${png.length} bytes)`);
  return png;
}

writePng(48, "favicon-48.png");
writePng(192, "apple-touch-icon.png");
writePng(512, "smpl-logo.png");

fs.writeFileSync(path.join(appDir, "icon.png"), fs.readFileSync(path.join(brandDir, "favicon-48.png")));
fs.copyFileSync(path.join(brandDir, "smpl-logo.png"), path.join(appDir, "apple-icon.png"));
console.log("wrote app/icon.png and app/apple-icon.png");
