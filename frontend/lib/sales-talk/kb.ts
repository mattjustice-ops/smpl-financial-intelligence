import "server-only";

import kbJson from "@/content/sales-kb/knowledge_base.json";

import type { SalesKbEntry, SalesKbFile } from "./types";

const DEFAULT_DEFLECT =
  "Good question — I want to give you an exact figure rather than guess, so let me follow up right after this.";

export function loadSalesKb(): SalesKbFile {
  const data = kbJson as SalesKbFile;
  return {
    version: data.version ?? 1,
    default_deflect_script: data.default_deflect_script ?? DEFAULT_DEFLECT,
    entries: Array.isArray(data.entries) ? (data.entries as SalesKbEntry[]) : [],
  };
}

export function defaultDeflectScript(): string {
  return loadSalesKb().default_deflect_script ?? DEFAULT_DEFLECT;
}
