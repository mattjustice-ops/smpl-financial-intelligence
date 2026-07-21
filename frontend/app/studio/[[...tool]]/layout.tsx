import type { Metadata, Viewport } from "next";
import { metadata as studioMetadata, viewport as studioViewport } from "next-sanity/studio";

export const metadata: Metadata = {
  ...studioMetadata,
  robots: { index: false, follow: false },
};

export const viewport: Viewport = studioViewport;

export default function StudioLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="sanity-studio min-h-screen bg-white text-black">{children}</div>
  );
}
