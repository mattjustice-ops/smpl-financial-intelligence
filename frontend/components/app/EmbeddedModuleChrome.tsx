"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { useActiveOrganization } from "@/hooks/useActiveOrganization";
import { useEntitlements } from "@/hooks/useEntitlements";

type EmbeddedModuleChromeProps = {
  moduleTitle: string;
  children: ReactNode;
  links?: ReactNode;
};

export function EmbeddedModuleChrome({ moduleTitle, children, links }: EmbeddedModuleChromeProps) {
  const { organizationId, organizations, isLoading: orgLoading } = useActiveOrganization();
  const { planLabel, isLoading: entLoading } = useEntitlements();

  const activeOrg = organizations.find((org) => org.id === organizationId);
  const orgName = activeOrg?.name ?? "—";
  const loading = orgLoading || entLoading;

  return (
    <div className="embedded-module">
      <header className="embedded-module__bar">
        <span className="embedded-module__title">
          {moduleTitle}
          {!loading ? (
            <>
              {" "}
              · <strong>{orgName}</strong> · <strong>{planLabel}</strong>
            </>
          ) : (
            " · Loading…"
          )}
        </span>
        {links ? <div className="embedded-module__links">{links}</div> : null}
      </header>
      <div className="embedded-module__body">{children}</div>
    </div>
  );
}

export function EmbeddedModuleNavLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="embedded-module__link">
      {children}
    </Link>
  );
}
