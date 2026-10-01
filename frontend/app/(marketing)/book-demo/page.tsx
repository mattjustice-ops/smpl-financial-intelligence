import type { Metadata } from "next";

import { BookDemoContent } from "./BookDemoContent";

import { DEFAULT_OG_IMAGE, sitePageUrl } from "@/lib/site";

const title = "Book a Demo | SMPL.ai SaaS FP&A Platform";
const description =
  "See SMPL.ai live: SaaS FP&A, ARR waterfalls, close reporting, and board decks. Book a demo with our team.";
const url = sitePageUrl("/book-demo");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  openGraph: { title, description, url, images: [DEFAULT_OG_IMAGE] },
  twitter: { card: "summary_large_image", title, description },
};

export default function BookDemoPage({
  searchParams,
}: {
  searchParams?: { plan?: string };
}) {
  return <BookDemoContent preferredPlan={searchParams?.plan} />;
}
