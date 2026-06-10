"use client";

import { useSession } from "next-auth/react";
import { useMemo } from "react";

export type SessionOrganization = {
  id: string;
  name: string;
  role: string;
  plan: string;
};

export function useActiveOrganization() {
  const { data: session, status } = useSession();

  const organizations = useMemo<SessionOrganization[]>(() => {
    return (session?.user?.organizations ?? []).map((org) => ({
      id: org.organizationId,
      name: org.organizationName,
      role: org.role,
      plan: org.plan,
    }));
  }, [session?.user?.organizations]);

  const organizationId = session?.user?.activeOrganizationId ?? "";

  return {
    organizationId,
    organizations,
    email: session?.user?.email ?? "",
    isLoading: status === "loading",
    isAuthenticated: status === "authenticated",
  };
}
