import { NextResponse } from "next/server";

import { boardSampleSetupMessage, loadBoardSampleHtml } from "@/lib/board-sample-html";

export async function GET() {
  const html = loadBoardSampleHtml();
  if (!html) {
    return new NextResponse(boardSampleSetupMessage(), {
      status: 503,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }

  return new NextResponse(html, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "public, max-age=0, must-revalidate",
    },
  });
}
