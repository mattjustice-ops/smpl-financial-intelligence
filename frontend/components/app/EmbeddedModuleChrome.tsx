"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useRef } from "react";

import { applyPlatformSkin, hydratePlatformSkin } from "@/components/app/PlatformSkinSelect";
import { useActiveOrganization } from "@/hooks/useActiveOrganization";
import { useEntitlements } from "@/hooks/useEntitlements";

type EmbeddedModuleChromeProps = {
  moduleTitle: string;
  children: ReactNode;
  links?: ReactNode;
  /** Optional control in the chrome bar (e.g. design skin select). */
  trailing?: ReactNode;
};

export function EmbeddedModuleChrome({
  moduleTitle,
  children,
  links,
  trailing,
}: EmbeddedModuleChromeProps) {
  const { organizationId, organizations, isLoading: orgLoading } = useActiveOrganization();
  const { planLabel, isLoading: entLoading } = useEntitlements();
  const bodyRef = useRef<HTMLDivElement>(null);

  const activeOrg = organizations.find((org) => org.id === organizationId);
  const orgName = activeOrg?.name ?? "—";
  const loading = orgLoading || entLoading;

  const longRunningApiBase = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, "") ?? "";

  // Keep platform chrome on the Board/engine skin (not marketing :root light defaults).
  useEffect(() => {
    hydratePlatformSkin();

    function onSkinMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== "smpl:skin") return;
      const id = typeof event.data.skinId === "string" ? event.data.skinId : null;
      if (!id) return;
      applyPlatformSkin(id, { persist: false });
    }

    function onStorage(event: StorageEvent) {
      if (event.key !== "smpl-skin") return;
      hydratePlatformSkin();
    }

    window.addEventListener("message", onSkinMessage);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("message", onSkinMessage);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  useEffect(() => {
    if (!organizationId) return;

    function postToIframe(frame: HTMLIFrameElement) {
      frame.contentWindow?.postMessage(
        { type: "smpl:org", organizationId },
        window.location.origin,
      );
      if (longRunningApiBase) {
        frame.contentWindow?.postMessage(
          { type: "smpl:api-base", apiBase: longRunningApiBase },
          window.location.origin,
        );
      }
    }

    const body = bodyRef.current;
    if (!body) return;
    const iframe = body.querySelector("iframe");
    if (!iframe) return;

    function onIframeLoad() {
      postToIframe(iframe as HTMLIFrameElement);
    }

    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== "smpl:iframe-ready") return;
      postToIframe(iframe as HTMLIFrameElement);
    }

    iframe.addEventListener("load", onIframeLoad);
    window.addEventListener("message", onMessage);
    if (iframe.contentDocument?.readyState === "complete") {
      postToIframe(iframe as HTMLIFrameElement);
    }

    return () => {
      iframe.removeEventListener("load", onIframeLoad);
      window.removeEventListener("message", onMessage);
    };
  }, [organizationId, longRunningApiBase]);

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
        <div className="embedded-module__bar-right">
          {links ? <div className="embedded-module__links">{links}</div> : null}
          {trailing}
        </div>
      </header>
      <div className="embedded-module__body" ref={bodyRef}>
        {children}
      </div>
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
