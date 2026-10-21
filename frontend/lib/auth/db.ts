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
    // Do not throw while the auth route is loading. A throw here becomes a
    // plain-text 500, and the board then fails trying to read that as JSON.
    // Sign-in still cannot persist until the database URL is set.
    console.error(
      "[auth] AUTH_DATABASE_URL is not set. Session reads continue; sign-in needs a Postgres URL.",
    );
    return "postgresql://missing:missing@127.0.0.1:5432/missing";
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
