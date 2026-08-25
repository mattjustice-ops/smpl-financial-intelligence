import { redirect } from "next/navigation";

/**
 * Legacy public URL — compliance scoreboard is ops-admin only at /app/compliance.
 * Do not bounce crawlers into /app (auth wall). Send humans to the homepage.
 */
export default function ComplianceRedirectPage() {
  redirect("/");
}
