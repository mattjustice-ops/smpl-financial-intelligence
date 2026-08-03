/**
 * Brand icon helper.
 *
 * IMPORTANT: Checked-in PNGs under public/brand/ (and apple-touch / app icons)
 * are the source of truth for what Google already crawled successfully. Do not
 * blindly regenerate them from smpl-logo.svg — the SVG and production rasters
 * have diverged, and a full regenerate previously broke non-SERP Google icons.
 *
 * This script only rebuilds multi-size favicon.ico (16/32/48) from the existing
 * favicon-48.png, and refreshes copies under public/ and app/.
 *
 * Run: npm run generate:brand-icons
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.join(__dirname, "..");
const brandDir = path.join(rootDir, "public", "brand");
const publicDir = path.join(rootDir, "public");
const appDir = path.join(rootDir, "app");

const favicon48 = path.join(brandDir, "favicon-48.png");
const appleTouch = path.join(brandDir, "apple-touch-icon.png");
const smplLogo = path.join(brandDir, "smpl-logo.png");
const icon512 = path.join(brandDir, "icon-512.png");

for (const required of [favicon48, appleTouch, smplLogo]) {
  if (!fs.existsSync(required)) {
    throw new Error(`Missing required brand asset: ${required}`);
  }
}

// Keep Organization JSON-LD path in sync with the restored square logo.
fs.copyFileSync(smplLogo, icon512);
console.log("wrote public/brand/icon-512.png (copy of smpl-logo.png)");

fs.copyFileSync(appleTouch, path.join(publicDir, "apple-touch-icon.png"));
fs.copyFileSync(favicon48, path.join(appDir, "icon.png"));
fs.copyFileSync(appleTouch, path.join(appDir, "apple-icon.png"));
console.log("synced public/apple-touch-icon.png, app/icon.png, app/apple-icon.png");

const py = `
from io import BytesIO
import struct
from pathlib import Path
from PIL import Image

src = Image.open(${JSON.stringify(favicon48)}).convert("RGBA")
sizes = [16, 32, 48]

def png_bytes(im):
    buf = BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()

images = [(s, png_bytes(src.resize((s, s), Image.Resampling.LANCZOS))) for s in sizes]
count = len(images)
header = struct.pack("<HHH", 0, 1, count)
entries = []
offset = 6 + 16 * count
blobs = []
for s, data in images:
    entries.append(struct.pack("<BBBBHHII", s, s, 0, 0, 1, 32, len(data), offset))
    blobs.append(data)
    offset += len(data)
ico = header + b"".join(entries) + b"".join(blobs)
for dest in [
    ${JSON.stringify(path.join(brandDir, "favicon.ico"))},
    ${JSON.stringify(path.join(publicDir, "favicon.ico"))},
]:
    Path(dest).write_bytes(ico)
    print(f"wrote {dest} ({len(ico)} bytes, frames={sizes})")
`.trim();

const result = spawnSync("python", ["-c", py], { encoding: "utf8" });
if (result.status !== 0) {
  throw new Error(
    `Failed to write favicon.ico. Install Pillow (pip install pillow).\n${result.stderr || result.stdout}`,
  );
}
process.stdout.write(result.stdout || "");
