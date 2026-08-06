import Script from "next/script";

/** Default Google Ads conversion ID (Matt / Ads account). Override via NEXT_PUBLIC_GOOGLE_ADS_ID. */
export const DEFAULT_GOOGLE_ADS_ID = "AW-18374910076";

/**
 * Resolve the public Google Ads ID.
 * - unset → default AW id (tag loads on marketing pages)
 * - empty / "off" / "false" → disabled (no scripts)
 * - any other value → that Ads ID
 */
export function resolveGoogleAdsId(): string | null {
  const raw = process.env.NEXT_PUBLIC_GOOGLE_ADS_ID;
  if (raw === undefined) return DEFAULT_GOOGLE_ADS_ID;
  const trimmed = raw.trim();
  if (!trimmed || trimmed === "off" || trimmed === "false") return null;
  return trimmed;
}

/**
 * Google Ads gtag base tag for App Router.
 * Mount only from the marketing layout so /app routes stay clean.
 * Conversion events: call gtag('event', 'conversion', { send_to: 'AW-…/label' })
 * from a dedicated success route or after form success — not wired yet
 * (request-quote success is inline UI, not a separate URL).
 */
export function GoogleAdsTag() {
  const adsId = resolveGoogleAdsId();
  if (!adsId) return null;

  return (
    <>
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${adsId}`}
        strategy="afterInteractive"
      />
      <Script id="google-ads-gtag" strategy="afterInteractive">
        {`
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', '${adsId}');
`}
      </Script>
    </>
  );
}
