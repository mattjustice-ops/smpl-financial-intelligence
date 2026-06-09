import "server-only";

import { Pool } from "pg";

const globalForPg = globalThis as typeof globalThis & { authPgPool?: Pool };

function isNextProductionBuild(): boolean {
  return process.env.NEXT_PHASE === "phase-production-build";
}

function resolveAuthDatabaseUrl(): string {
  if (process.env.AUTH_DATABASE_URL?.trim()) {
    return process.env.AUTH_DATABASE_URL.trim();
  }

  const databaseUrl = process.env.DATABASE_URL?.trim();
  if (databaseUrl) {
    return databaseUrl.replace(/^postgresql\+psycopg:\/\//, "postgresql://");
  }

  // `next build` loads auth routes to collect page data; no live DB is needed yet.
  if (isNextProductionBuild()) {
    return "postgresql://build:build@127.0.0.1:5432/build";
  }

  if (process.env.VERCEL === "1" || process.env.NODE_ENV === "production") {
    throw new Error(
      "AUTH_DATABASE_URL is not set. Add a Neon/Supabase Postgres URL in Vercel environment variables."
    );
  }

  return "postgresql://sfi:sfi_dev_password@localhost:5432/sfi";
}

export function getAuthPgPool(): Pool {
  if (!globalForPg.authPgPool) {
    globalForPg.authPgPool = new Pool({
      connectionString: resolveAuthDatabaseUrl(),
      max: 10,
    });
  }

  return globalForPg.authPgPool;
}
