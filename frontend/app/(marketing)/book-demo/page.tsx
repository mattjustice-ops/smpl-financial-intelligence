import type { Metadata } from "next";

import { BookDemoContent } from "./BookDemoContent";

export const metadata: Metadata = {
  title: "Book a demo · SMPL.ai",
  description:
    "Share your contact details and priorities, then schedule a live SMPL demo with our team.",
};

export default function BookDemoPage({
  searchParams,
}: {
  searchParams?: { plan?: string };
}) {
  return <BookDemoContent preferredPlan={searchParams?.plan} />;
}
