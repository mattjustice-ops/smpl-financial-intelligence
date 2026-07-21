import { revalidatePath } from "next/cache";
import { NextResponse, type NextRequest } from "next/server";

/**
 * On-demand revalidation webhook for Sanity publish events.
 * Configure in Sanity → API → Webhooks:
 *   URL: https://www.smpl-ai.com/api/revalidate
 *   Secret header: x-sanity-webhook-secret = SANITY_REVALIDATE_SECRET
 *   Filter: _type in ["post", "glossaryTerm", "author", "category"]
 */
export async function POST(request: NextRequest) {
  const secret = process.env.SANITY_REVALIDATE_SECRET?.trim();
  const provided =
    request.headers.get("x-sanity-webhook-secret") ||
    request.nextUrl.searchParams.get("secret");

  if (!secret || provided !== secret) {
    return NextResponse.json({ ok: false, message: "Invalid secret" }, { status: 401 });
  }

  let body: { _type?: string; slug?: { current?: string } } = {};
  try {
    body = await request.json();
  } catch {
    // Sanity may send empty body depending on webhook config
  }

  revalidatePath("/blog");
  revalidatePath("/glossary");

  const type = body._type;
  const slug = body.slug?.current;
  if (type === "post" && slug) {
    revalidatePath(`/blog/${slug}`);
  }
  if (type === "glossaryTerm" && slug) {
    revalidatePath(`/glossary/${slug}`);
  }

  return NextResponse.json({
    ok: true,
    revalidated: true,
    type: type || null,
    slug: slug || null,
  });
}
