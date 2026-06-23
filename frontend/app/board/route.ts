import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { NextResponse } from "next/server";

export async function GET() {
  const path = join(process.cwd(), "public", "board", "index.html");
  if (!existsSync(path)) {
    const body = `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Board platform setup</title>
<style>body{font-family:system-ui,sans-serif;max-width:640px;margin:48px auto;padding:0 24px;line-height:1.6;color:#0f172a}
code{background:#f1f5f9;padding:2px 6px;border-radius:4px}</style></head>
<body>
<h1>Board platform not found</h1>
<p>Restore the committed baseline from <code>frontend/</code>:</p>
<pre><code>npm run reset:platform</code></pre>
<p>If the baseline is missing, check out <code>frontend/canonical/</code> from git and run reset again.</p>
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
