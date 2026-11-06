import { redirect } from "next/navigation";

import { auth } from "@/auth";

export const metadata = {
  title: "SMPL · Board",
};

export default async function WorkspacePage() {
  const session = await auth();
  if (!session?.user?.email) {
    redirect("/login?callbackUrl=/app/board");
  }
  redirect("/app/board");
}
