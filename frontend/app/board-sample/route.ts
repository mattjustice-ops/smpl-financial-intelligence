import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { NextResponse } from "next/server";

export async function GET() {
  const path = join(process.cwd(), "public", "board-sample", "index.html");
  if (!existsSync(path)) {
    const body = `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Board sample setup</title>
<style>body{font-family:system-ui,sans-serif;max-width:640px;margin:48px auto;padding:0 24px;line-height:1.6;color:#0f172a}
code{background:#f1f5f9;padding:2px 6px;border-radius:4px}</style></head>
<body>
<h1>Board sample not found</h1>
<p>Restore the static marketing sample from <code>frontend/</code>:</p>
<pre><code>npm run create:board-sample
npm run copy:board-exports</code></pre>
<p>Or set <code>SMPL_BOARD_SAMPLE_SRC</code> to the original HTML board template path, then commit <code>public/board-sample/index.html</code> and redeploy.</p>
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
