import { redirect } from "next/navigation";

/** Legacy public URL — compliance scoreboard is ops-admin only at /app/compliance. */
export default function ComplianceRedirectPage() {
  redirect("/app/compliance");
}
