/** Comma-separated SMPL team emails allowed to view /app/ops. */

export function smplOpsAdminEmails(): string[] {
  const raw = process.env.SMPL_OPS_ADMIN_EMAILS?.trim() ?? "";
  if (!raw) return [];
  return raw
    .split(",")
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean);
}

export function isSmplOpsAdminEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  const admins = smplOpsAdminEmails();
  if (admins.length === 0) {
    return process.env.NODE_ENV === "development";
  }
  return admins.includes(email.trim().toLowerCase());
}
