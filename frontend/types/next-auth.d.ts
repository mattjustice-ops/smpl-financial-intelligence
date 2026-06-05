import type { BackendOrganization } from "@/lib/auth/types";
import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    user: DefaultSession["user"] & {
      activeOrganizationId?: string;
      organizations?: BackendOrganization[];
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    userId?: string;
    activeOrganizationId?: string;
    organizations?: BackendOrganization[];
  }
}

declare module "@auth/core/jwt" {
  interface JWT {
    userId?: string;
    activeOrganizationId?: string;
    organizations?: BackendOrganization[];
  }
}

export {};
