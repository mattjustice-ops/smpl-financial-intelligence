import { createClient, type QueryParams } from "next-sanity";

export const projectId =
  process.env.NEXT_PUBLIC_SANITY_PROJECT_ID?.trim() || "";
export const dataset =
  process.env.NEXT_PUBLIC_SANITY_DATASET?.trim() || "production";
export const apiVersion = "2025-01-01";

/**
 * Server-only Viewer (or Editor) token. Required when the Sanity dataset is
 * private — unauthenticated CDN/API queries return empty results.
 * Never expose as NEXT_PUBLIC_*.
 */
const readToken = process.env.SANITY_API_READ_TOKEN?.trim() || "";

/** True when a project ID is configured (public marketing fetches can run). */
export function isSanityConfigured(): boolean {
  return Boolean(projectId);
}

export const sanityClient = createClient({
  projectId: projectId || "placeholder",
  dataset,
  apiVersion,
  useCdn: true,
  perspective: "published",
  // Token enables reads against private datasets from Server Components.
  ...(readToken ? { token: readToken } : {}),
  stega: { enabled: false },
});

/**
 * Fetch with graceful empty fallback when Sanity env is missing or the
 * request fails (e.g. schema not deployed yet).
 */
export async function sanityFetch<T>(
  query: string,
  params: QueryParams = {},
  fallback: T,
): Promise<T> {
  if (!isSanityConfigured()) {
    return fallback;
  }
  try {
    return await sanityClient.fetch<T>(query, params, {
      next: { revalidate: 60 },
    });
  } catch (error) {
    console.warn("[sanity] fetch failed:", error);
    return fallback;
  }
}
