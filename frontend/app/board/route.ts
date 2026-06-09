import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { NextResponse } from "next/server";

const DEFAULT_DOWNLOADS_SRC =
  "C:\\Users\\mattj\\Downloads\\SMPL_Board_Platform_June2026 (6).html";

function resolveBoardHtmlPath(): string | null {
  const publicPath = join(process.cwd(), "public", "board", "index.html");
  if (existsSync(publicPath)) return publicPath;

  const envSrc = process.env.SMPL_BOARD_HTML_SRC?.trim();
  if (envSrc && existsSync(envSrc)) return envSrc;

  if (existsSync(DEFAULT_DOWNLOADS_SRC)) return DEFAULT_DOWNLOADS_SRC;

  return null;
}

export async function GET() {
  const path = resolveBoardHtmlPath();
  if (!path) {
    const body = `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Board demo setup</title>
<style>body{font-family:system-ui,sans-serif;max-width:640px;margin:48px auto;padding:0 24px;line-height:1.6;color:#0f172a}
code{background:#f1f5f9;padding:2px 6px;border-radius:4px}</style></head>
<body>
<h1>Board demo not found</h1>
<p>Copy the Claude board HTML into the repo, then refresh:</p>
<pre><code>npm run copy:board</code></pre>
<p>Or set <code>SMPL_BOARD_HTML_SRC</code> in <code>.env.local</code> to your Downloads file path.</p>
</body></html>`;
    return new NextResponse(body, {
      status: 503,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }

  const html = readFileSync(path, "utf-8");
  return new NextResponse(html, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "public, max-age=0, must-revalidate",
    },
  });
}
