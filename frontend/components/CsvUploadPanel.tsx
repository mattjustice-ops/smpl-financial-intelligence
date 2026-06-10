"use client";

import { useEffect, useState } from "react";
import type { CSSProperties } from "react";

import { getNextApiBase } from "@/lib/apiBase";
import { useActiveOrganization } from "@/hooks/useActiveOrganization";

type Org = { id: string; name: string };

type UploadResponse = {
  csv_kind: string;
  rows_upserted: number;
  validation_errors: unknown[];
};

type SeedResponse = {
  organization_id: string;
  demo_data_dir: string;
  files: {
    filename: string;
    expected_kind: string;
    csv_kind: string | null;
    rows_upserted: number;
    validation_errors: unknown[];
  }[];
};

export function CsvUploadPanel() {
  const apiBase = getNextApiBase();
  const { organizationId, organizations, isLoading: sessionLoading } = useActiveOrganization();
  const [orgId, setOrgId] = useState("");
  const [newOrgName, setNewOrgName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [panelError, setPanelError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [seedResult, setSeedResult] = useState<SeedResponse | null>(null);

  useEffect(() => {
    if (organizationId) {
      setOrgId(organizationId);
    }
  }, [organizationId]);

  const orgs = organizations;

  const onCreateOrg = async () => {
    setPanelError(null);
    if (!newOrgName.trim()) return;
    setBusy("org");
    try {
      const res = await fetch(`${apiBase}/api/v1/organizations/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newOrgName.trim() }),
      });
      if (!res.ok) throw new Error(await res.text());
      const created = (await res.json()) as Org;
      setNewOrgName("");
      setOrgId(created.id);
    } catch (e) {
      setPanelError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const onUpload = async () => {
    setPanelError(null);
    setUploadResult(null);
    setSeedResult(null);
    if (!file || !orgId) {
      setPanelError("Select an organization and a CSV file.");
      return;
    }
    setBusy("upload");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("organization_id", orgId);
      const res = await fetch(`${apiBase}/api/v1/demo-csv/upload`, { method: "POST", body: fd });
      const text = await res.text();
      if (!res.ok) {
        try {
          const j = JSON.parse(text) as { detail?: unknown };
          setPanelError(JSON.stringify(j.detail ?? text, null, 2));
        } catch {
          setPanelError(text || `Upload failed (${res.status})`);
        }
        return;
      }
      setUploadResult(JSON.parse(text) as UploadResponse);
    } catch (e) {
      setPanelError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const onSeedAll = async () => {
    setPanelError(null);
    setUploadResult(null);
    setSeedResult(null);
    if (!orgId) {
      setPanelError("Select an organization.");
      return;
    }
    setBusy("seed");
    try {
      const res = await fetch(
        `${apiBase}/api/v1/demo-csv/seed?organization_id=${encodeURIComponent(orgId)}`,
        { method: "POST" }
      );
      const text = await res.text();
      if (!res.ok) {
        try {
          const j = JSON.parse(text) as { detail?: unknown };
          setPanelError(JSON.stringify(j.detail ?? text, null, 2));
        } catch {
          setPanelError(text || `Seed failed (${res.status})`);
        }
        return;
      }
      setSeedResult(JSON.parse(text) as SeedResponse);
    } catch (e) {
      setPanelError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const card: CSSProperties = {
    border: "1px solid var(--border)",
    borderRadius: 10,
    padding: 14,
    marginTop: 12,
  };

  return (
    <div style={card}>
      <h2 style={{ margin: "0 0 12px", fontSize: 18 }}>Demo CSV upload</h2>
      <p style={{ margin: "0 0 12px", color: "var(--muted)", fontSize: 14, lineHeight: 1.5 }}>
        Files are accepted only when the header row matches a known demo profile exactly (same column names, any
        order). There is no column mapping step. Use <strong>Seed all demo CSVs</strong> to load the bundled
        <code>backend/demo_data/*.csv</code> in the documented order.
      </p>

      {panelError && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ color: "#b91c1c", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
            Upload error (this is not a header mismatch unless the message says headers_do_not_match):
          </div>
          <pre
            style={{
              color: "#b91c1c",
              margin: 0,
              fontSize: 12,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {panelError}
          </pre>
        </div>
      )}

      <div style={{ display: "grid", gap: 10 }}>
        <label style={{ fontSize: 13 }}>
          Organization
          <select
            style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
            value={orgId}
            onChange={(e) => setOrgId(e.target.value)}
          >
            <option value="">— select —</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </label>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
          <label style={{ flex: 1, minWidth: 160, fontSize: 13 }}>
            New organization
            <input
              style={{ display: "block", width: "100%", marginTop: 4, padding: 8 }}
              value={newOrgName}
              onChange={(e) => setNewOrgName(e.target.value)}
              placeholder="Acme Inc."
            />
          </label>
          <button type="button" onClick={onCreateOrg} disabled={busy !== null}>
            Create
          </button>
        </div>

        <label style={{ fontSize: 13 }}>
          CSV file
          <input
            type="file"
            accept=".csv,text/csv"
            style={{ display: "block", marginTop: 4 }}
            onChange={(e) => {
              setUploadResult(null);
              setSeedResult(null);
              setFile(e.target.files?.[0] ?? null);
            }}
          />
        </label>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button type="button" onClick={onUpload} disabled={busy !== null || !file || !orgId}>
            {busy === "upload" ? "Uploading…" : "Upload CSV"}
          </button>
          <button type="button" onClick={onSeedAll} disabled={busy !== null || !orgId}>
            {busy === "seed" ? "Seeding…" : "Seed all demo CSVs"}
          </button>
        </div>

        {uploadResult && (
          <div style={{ fontSize: 14 }}>
            <strong>Uploaded</strong> profile <code>{uploadResult.csv_kind}</code> — rows upserted:{" "}
            {uploadResult.rows_upserted}
            {uploadResult.validation_errors.length > 0 && (
              <div style={{ marginTop: 8, color: "#b45309", fontSize: 13 }}>
                Row validation issues (skipped rows):{" "}
                <pre style={{ fontSize: 11, overflow: "auto", maxHeight: 200 }}>
                  {JSON.stringify(uploadResult.validation_errors, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {seedResult && (
          <div style={{ fontSize: 14 }}>
            <strong>Seed complete</strong> from <code>{seedResult.demo_data_dir}</code>
            <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 13 }}>
              {seedResult.files.map((f) => (
                <li key={f.filename}>
                  {f.filename}: {f.rows_upserted} row(s)
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
