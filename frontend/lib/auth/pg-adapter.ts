import "server-only";

import type { Adapter, AdapterAccount, AdapterUser } from "@auth/core/adapters";
import type { Pool } from "pg";

type AuthjsUserRow = {
  id: string;
  email: string;
  name: string | null;
  email_verified: Date | null;
  image: string | null;
};

function mapUser(row: AuthjsUserRow): AdapterUser {
  return {
    id: row.id,
    email: row.email,
    name: row.name,
    emailVerified: row.email_verified,
    image: row.image,
  };
}

function requireUserRow(row: AuthjsUserRow | undefined, context: string): AuthjsUserRow {
  if (!row) {
    throw new Error(`Auth adapter: missing user row after ${context}`);
  }
  return row;
}

export function AuthPgAdapter(pool: Pool): Adapter {
  return {
    async createUser(user) {
      const id = crypto.randomUUID();
      const result = await pool.query<AuthjsUserRow>(
        `INSERT INTO authjs_users (id, email, name, email_verified, image)
         VALUES ($1, $2, $3, $4, $5)
         RETURNING id, email, name, email_verified, image`,
        [id, user.email, user.name ?? null, user.emailVerified ?? null, user.image ?? null]
      );
      return mapUser(requireUserRow(result.rows[0], "createUser"));
    },

    async getUser(id) {
      const result = await pool.query<AuthjsUserRow>(
        `SELECT id, email, name, email_verified, image
         FROM authjs_users
         WHERE id = $1`,
        [id]
      );
      return result.rows[0] ? mapUser(result.rows[0]) : null;
    },

    async getUserByEmail(email) {
      const result = await pool.query<AuthjsUserRow>(
        `SELECT id, email, name, email_verified, image
         FROM authjs_users
         WHERE email = $1`,
        [email]
      );
      return result.rows[0] ? mapUser(result.rows[0]) : null;
    },

    async getUserByAccount(_providerAccountId: Pick<AdapterAccount, "provider" | "providerAccountId">) {
      return null;
    },

    async updateUser(user) {
      const result = await pool.query<AuthjsUserRow>(
        `UPDATE authjs_users
         SET email = COALESCE($2, email),
             name = COALESCE($3, name),
             email_verified = COALESCE($4, email_verified),
             image = COALESCE($5, image)
         WHERE id = $1
         RETURNING id, email, name, email_verified, image`,
        [user.id, user.email ?? null, user.name ?? null, user.emailVerified ?? null, user.image ?? null]
      );
      return mapUser(requireUserRow(result.rows[0], "updateUser"));
    },

    async deleteUser(userId) {
      await pool.query(`DELETE FROM authjs_users WHERE id = $1`, [userId]);
    },

    async linkAccount(_account: AdapterAccount) {
      return undefined;
    },

    async unlinkAccount(_providerAccountId: Pick<AdapterAccount, "provider" | "providerAccountId">) {
      return undefined;
    },

    async createSession(session) {
      return session;
    },

    async getSessionAndUser(_sessionToken: string) {
      return null;
    },

    async updateSession(_session) {
      return null;
    },

    async deleteSession(_sessionToken: string) {
      return null;
    },

    async createVerificationToken(verificationToken) {
      await pool.query(
        `INSERT INTO authjs_verification_token (identifier, token, expires)
         VALUES ($1, $2, $3)`,
        [verificationToken.identifier, verificationToken.token, verificationToken.expires]
      );
      return verificationToken;
    },

    async useVerificationToken({ identifier, token }) {
      const result = await pool.query<{ identifier: string; token: string; expires: Date }>(
        `DELETE FROM authjs_verification_token
         WHERE identifier = $1 AND token = $2
         RETURNING identifier, token, expires`,
        [identifier, token]
      );
      return result.rows[0] ?? null;
    },
  };
}

