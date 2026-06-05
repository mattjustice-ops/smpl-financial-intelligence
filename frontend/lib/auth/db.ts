import "server-only";

import { Pool } from "pg";

const globalForPg = globalThis as typeof globalThis & { authPgPool?: Pool };

function resolveAuthDatabaseUrl(): string {
  if (process.env.AUTH_DATABASE_URL?.trim()) {
    return process.env.AUTH_DATABASE_URL.trim();
  }

  const databaseUrl = process.env.DATABASE_URL?.trim();
  if (databaseUrl) {
    return databaseUrl.replace(/^postgresql\+psycopg:\/\//, "postgresql://");
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
