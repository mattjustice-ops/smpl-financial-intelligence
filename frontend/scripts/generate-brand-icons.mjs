/**
 * Regenerate PNG/ICO brand icons from public/brand/smpl-logo.svg
 * Run: npm run generate:brand-icons
 *
 * Google Search favicon guidelines: square PNG/ICO at a multiple of 48px
 * (48 / 96 / …). A lone 16×16 favicon.ico gets upscaled into the crunchy
 * SERP brand mark. Raster exports use full-bleed teal (no transparent
 * corners that read as black in Google/SERP UIs).
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Resvg } from "@resvg/resvg-js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.join(__dirname, "..");
const brandDir = path.join(rootDir, "public", "brand");
const publicDir = path.join(rootDir, "public");
const appDir = path.join(rootDir, "app");

/** Full-bleed teal square + mark (Google/SERP-safe; no transparent corners). */
function rasterSvg() {
  const source = fs.readFileSync(path.join(brandDir, "smpl-logo.svg"), "utf8");
  // Keep paths/groups; force an opaque full-bleed teal canvas for raster sizes.
  const body = source
    .replace(/<svg[^>]*>/i, "")
    .replace(/<\/svg>/i, "")
    .replace(/<rect\b[^>]*\/>/i, "");
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <rect width="512" height="512" fill="#2dd4bf"/>
  ${body}
</svg>`;
}

const svg = Buffer.from(rasterSvg(), "utf8");

function renderPng(size) {
  const resvg = new Resvg(svg, {
    fitTo: { mode: "width", value: size },
    font: { loadSystemFonts: false },
  });
  return resvg.render().asPng();
}

function writePng(size, destPath) {
  const png = renderPng(size);
  fs.writeFileSync(destPath, png);
  console.log(
    `wrote ${path.relative(rootDir, destPath)} (${size}×${size}, ${png.length} bytes)`,
  );
  return png;
}

function writeIco(destPath, sizes = [16, 32, 48]) {
  const tmpDir = path.join(brandDir, ".ico-tmp");
  fs.mkdirSync(tmpDir, { recursive: true });
  const tmpPngs = sizes.map((size) => {
    const p = path.join(tmpDir, `${size}.png`);
    fs.writeFileSync(p, renderPng(size));
    return p;
  });

  // Pillow: save each size as its own ICO entry (append_images alone is flaky).
  const py = `
from PIL import Image
sizes = ${JSON.stringify(sizes)}
paths = ${JSON.stringify(tmpPngs)}
dest = ${JSON.stringify(destPath)}
imgs = []
for s, p in zip(sizes, paths):
    im = Image.open(p).convert("RGBA")
    if im.size != (s, s):
        im = im.resize((s, s), Image.Resampling.LANCZOS)
    imgs.append(im)
# Write multi-size ICO by saving the largest and declaring all sizes;
# Pillow downscales from the largest when sizes= is provided.
imgs[-1].save(dest, format="ICO", sizes=[(s, s) for s in sizes])
# Verify frames
v = Image.open(dest)
frames = []
idx = 0
while True:
    try:
        v.seek(idx)
        frames.append(v.size)
        idx += 1
    except EOFError:
        break
print("frames=" + ",".join(f"{w}x{h}" for w, h in frames))
if (48, 48) not in frames and max(s for s, _ in frames) < 48:
    raise SystemExit("ICO missing a >=48px frame")
`.trim();

  const result = spawnSync("python", ["-c", py], { encoding: "utf8" });
  fs.rmSync(tmpDir, { recursive: true, force: true });
  if (result.status !== 0) {
    throw new Error(
      `Failed to write ICO (${destPath}). Install Pillow (pip install pillow).\n${result.stderr || result.stdout}`,
    );
  }
  console.log(
    `wrote ${path.relative(rootDir, destPath)} (ICO ${String(result.stdout).trim()}, ${fs.statSync(destPath).size} bytes)`,
  );
}

writePng(48, path.join(brandDir, "favicon-48.png"));
writePng(96, path.join(brandDir, "favicon-96.png"));
writePng(180, path.join(brandDir, "apple-touch-icon.png"));
writePng(512, path.join(brandDir, "smpl-logo.png"));
writePng(512, path.join(brandDir, "icon-512.png"));

fs.copyFileSync(
  path.join(brandDir, "apple-touch-icon.png"),
  path.join(publicDir, "apple-touch-icon.png"),
);
console.log("wrote public/apple-touch-icon.png");

fs.copyFileSync(path.join(brandDir, "favicon-48.png"), path.join(appDir, "icon.png"));
fs.copyFileSync(
  path.join(brandDir, "apple-touch-icon.png"),
  path.join(appDir, "apple-icon.png"),
);
console.log("wrote app/icon.png and app/apple-icon.png");

writeIco(path.join(brandDir, "favicon.ico"), [16, 32, 48]);
fs.copyFileSync(path.join(brandDir, "favicon.ico"), path.join(publicDir, "favicon.ico"));
console.log("wrote public/favicon.ico");
