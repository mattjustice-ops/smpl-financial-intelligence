import "server-only";

import type { Session } from "next-auth";
import { NextResponse } from "next/server";

import { requireAuthenticatedSession } from "@/lib/auth/server-org-access";
import { isSmplOpsAdminEmail } from "@/lib/ops/smpl-ops-admin";

export async function requireSmplOpsAdmin():
  Promise<{ session: Session } | { error: NextResponse }> {
  const authResult = await requireAuthenticatedSession();
  if ("error" in authResult) {
    return authResult;
  }

  const email = authResult.session.user?.email;
  if (!isSmplOpsAdminEmail(email)) {
    return {
      error: NextResponse.json(
        {
          detail:
            "SMPL Ops is restricted to internal admins. Set SMPL_OPS_ADMIN_EMAILS on Vercel.",
        },
        { status: 403 },
      ),
    };
  }

  return { session: authResult.session };
}
