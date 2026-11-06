import { redirect } from "next/navigation";

/**
 * Default signed-in home is Board Platform (Executive Summary).
 */
export default function AppHomePage() {
  redirect("/app/board");
}
