import "server-only";

import kbJson from "@/content/sales-kb/knowledge_base.json";

import { DEFLECT_PRODUCT_BEHAVIOR, pickDeflectScript } from "./deflect";
import type { SalesKbEntry, SalesKbFile } from "./types";

export function loadSalesKb(): SalesKbFile {
  const data = kbJson as SalesKbFile;
  return {
    version: data.version ?? 1,
    default_deflect_script: data.default_deflect_script ?? DEFLECT_PRODUCT_BEHAVIOR,
    entries: Array.isArray(data.entries) ? (data.entries as SalesKbEntry[]) : [],
  };
}

export function defaultDeflectScript(question?: string): string {
  if (question) return pickDeflectScript(question);
  return loadSalesKb().default_deflect_script ?? DEFLECT_PRODUCT_BEHAVIOR;
}

export { pickDeflectScript };
