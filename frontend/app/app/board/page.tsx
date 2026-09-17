"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import {
  EmbeddedModuleChrome,
} from "@/components/app/EmbeddedModuleChrome";
import { PlatformModuleNavLinks } from "@/components/app/PlatformModuleNavLinks";
import { useActiveOrganization } from "@/hooks/useActiveOrganization";
import { useEntitlements } from "@/hooks/useEntitlements";

function BoardPlatformInner() {
  const { isLoading: orgLoading } = useActiveOrganization();
  const { hasModule, planLabel } = useEntitlements();
  const searchParams = useSearchParams();
  const canView = hasModule("board_export");
  const view = searchParams.get("view");

  if (orgLoading) {
    return <div className="embedded-module__gate">Loading session…</div>;
  }

  if (!canView) {
    return (
      <div className="embedded-module__gate">
        <h1>Board Platform</h1>
        <p>
          Board Platform requires the board_export entitlement ({planLabel} plan).{" "}
          <Link href="/app">Back to operating system</Link>
        </p>
      </div>
    );
  }

  const qs = new URLSearchParams({ embedded: "1", v: "14" });
  if (view) qs.set("view", view);
  const src = `/board/index.html?${qs.toString()}`;
  const title = view === "validation" ? "Validation Engine" : "Board Platform";

  return (
    <EmbeddedModuleChrome
      moduleTitle={title}
      links={<PlatformModuleNavLinks />}
    >
      <iframe title={title} src={src} />
    </EmbeddedModuleChrome>
  );
}

export default function BoardPlatformPage() {
  return (
    <Suspense fallback={<div className="embedded-module__gate">Loading Board Platform…</div>}>
      <BoardPlatformInner />
    </Suspense>
  );
}
