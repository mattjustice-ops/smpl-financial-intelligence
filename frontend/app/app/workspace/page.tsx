import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { WorkspaceShell } from "@/components/workspace/WorkspaceDashboard";

export const metadata = {
  title: "SMPL · Workspace",
};

export default async function WorkspacePage() {
  const session = await auth();
  if (!session?.user?.email) {
    redirect("/login?callbackUrl=/app/workspace");
  }

  return <WorkspaceShell />;
}
