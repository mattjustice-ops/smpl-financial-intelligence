import "server-only";

import fs from "node:fs";

const DEFAULT_RESEND_TOKEN_FILE = "C:\\Users\\mattj\\OneDrive\\Documents\\Resend Token.txt";

let cachedResendApiKey: string | null | undefined;

function readResendTokenFile(): string | null {
  const tokenFile =
    process.env.RESEND_TOKEN_FILE?.trim() ||
    (fs.existsSync(DEFAULT_RESEND_TOKEN_FILE) ? DEFAULT_RESEND_TOKEN_FILE : "");

  if (!tokenFile || !fs.existsSync(tokenFile)) {
    return null;
  }

  try {
    const content = fs.readFileSync(tokenFile, "utf-8");
    const matches = content.match(/re_[a-zA-Z0-9_]+/g);
    if (!matches?.length) {
      return null;
    }
    // Prefer a key on its own line; fall back to the last match in the file.
    const ownLine = content
      .split(/\r?\n/)
      .map((line) => line.trim())
      .find((line) => /^re_[a-zA-Z0-9_]+$/.test(line));
    return ownLine ?? matches[matches.length - 1];
  } catch {
    return null;
  }
}

export function getResendApiKey(): string | null {
  if (process.env.NODE_ENV === "development") {
    cachedResendApiKey = undefined;
  } else if (cachedResendApiKey !== undefined) {
    return cachedResendApiKey;
  }

  const direct =
    process.env.AUTH_RESEND_KEY?.trim() ||
    process.env.RESEND_API_KEY?.trim() ||
    null;

  cachedResendApiKey = direct || readResendTokenFile();
  return cachedResendApiKey;
}

export function getAuthEmailProviderId(): "resend" | "nodemailer" {
  return getResendApiKey() ? "resend" : "nodemailer";
}
