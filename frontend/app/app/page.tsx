import { redirect } from "next/navigation";

/**
 * Default signed-in home is Board Platform (Executive Summary).
 * Legacy CFO OS / upload tools remain under /app/workspace and related routes.
 */
export default function AppHomePage() {
  redirect("/app/board");
}
