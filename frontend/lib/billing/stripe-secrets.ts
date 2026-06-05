import "server-only";

import fs from "node:fs";

const DEFAULT_STRIPE_TOKEN_FILE = "C:\\Users\\mattj\\OneDrive\\Documents\\Stripe Token.txt";

type StripeSecretsFromFile = {
  secretKey?: string;
  publishableKey?: string;
  webhookSecret?: string;
};

let cachedFileSecrets: StripeSecretsFromFile | null | undefined;

function readStripeTokenFile(): StripeSecretsFromFile | null {
  if (cachedFileSecrets !== undefined) {
    return cachedFileSecrets;
  }

  const tokenFile =
    process.env.STRIPE_TOKEN_FILE?.trim() ||
    (fs.existsSync(DEFAULT_STRIPE_TOKEN_FILE) ? DEFAULT_STRIPE_TOKEN_FILE : "");

  if (!tokenFile || !fs.existsSync(tokenFile)) {
    cachedFileSecrets = null;
    return null;
  }

  try {
    const content = fs.readFileSync(tokenFile, "utf-8");
    cachedFileSecrets = {
      secretKey: content.match(/sk_(?:test|live)_[a-zA-Z0-9]+/)?.[0],
      publishableKey: content.match(/pk_(?:test|live)_[a-zA-Z0-9]+/)?.[0],
      webhookSecret: content.match(/whsec_[a-zA-Z0-9]+/)?.[0],
    };
    return cachedFileSecrets;
  } catch {
    cachedFileSecrets = null;
    return null;
  }
}

export function getStripeSecretKey(): string | null {
  const direct = process.env.STRIPE_SECRET_KEY?.trim();
  if (direct) return direct;
  return readStripeTokenFile()?.secretKey ?? null;
}

export function getStripePublishableKey(): string | null {
  const direct = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY?.trim();
  if (direct) return direct;
  return readStripeTokenFile()?.publishableKey ?? null;
}

export function getStripeWebhookSecret(): string | null {
  const direct = process.env.STRIPE_WEBHOOK_SECRET?.trim();
  if (direct) return direct;
  return readStripeTokenFile()?.webhookSecret ?? null;
}
