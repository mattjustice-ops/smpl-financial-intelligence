/**
 * Standalone Week 1 seed — avoids next/server-only.
 *   npx tsx scripts/aio-seed-week1-standalone.ts
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import pg from "pg";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pool = new pg.Pool({
  connectionString:
    process.env.AUTH_DATABASE_URL ||
    process.env.DATABASE_URL ||
    "postgresql://sfi:sfi_dev_password@localhost:5432/sfi",
});

const seedQueries = JSON.parse(
  fs.readFileSync(path.join(root, "lib/aio/data/seed_queries.json"), "utf8"),
);
const seedContent = JSON.parse(
  fs.readFileSync(path.join(root, "lib/aio/data/seed_content.json"), "utf8"),
);
const pulseQueries = JSON.parse(
  fs.readFileSync(path.join(root, "lib/aio/data/pulse_queries.json"), "utf8"),
);
const sacredBaseline = JSON.parse(
  fs.readFileSync(path.join(root, "lib/aio/data/sacred_baseline.json"), "utf8"),
);

const COMPETITORS = [
  "Abacum",
  "Aleph",
  "Anaplan",
  "Cube",
  "Datarails",
  "Drivetrain",
  "Mosaic",
  "Pigment",
  "Planful",
  "Prophix",
  "Runway",
  "Vena",
  "Workday Adaptive Planning",
];

async function main() {
  await pool.query(`CREATE EXTENSION IF NOT EXISTS pgcrypto`);
  // Schema is ensured by app; add Week-1 tables/columns here too for standalone.
  await pool.query(`
    ALTER TABLE aio_queries ADD COLUMN IF NOT EXISTS pulse_enabled BOOLEAN NOT NULL DEFAULT FALSE;
    CREATE TABLE IF NOT EXISTS aio_content (
      id TEXT PRIMARY KEY,
      url TEXT NOT NULL,
      title TEXT NOT NULL,
      content_type TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'live',
      published_at DATE,
      hypothesis TEXT,
      active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS aio_content_query_map (
      content_id TEXT NOT NULL REFERENCES aio_content(id) ON DELETE CASCADE,
      query_id TEXT NOT NULL REFERENCES aio_queries(id) ON DELETE CASCADE,
      is_primary BOOLEAN NOT NULL DEFAULT FALSE,
      PRIMARY KEY (content_id, query_id)
    );
    CREATE TABLE IF NOT EXISTS aio_settings (
      key TEXT PRIMARY KEY,
      value_json JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
  `);

  let q = 0;
  for (const s of seedQueries) {
    await pool.query(
      `INSERT INTO aio_queries (
        id, query_text, category, intent, priority, baseline_enabled,
        target_topic, target_page_hint, notes, version, active, updated_at
      ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,1,TRUE,now())
      ON CONFLICT (id) DO UPDATE SET
        query_text = EXCLUDED.query_text,
        category = EXCLUDED.category,
        intent = EXCLUDED.intent,
        priority = EXCLUDED.priority,
        baseline_enabled = EXCLUDED.baseline_enabled,
        target_topic = EXCLUDED.target_topic,
        target_page_hint = EXCLUDED.target_page_hint,
        notes = EXCLUDED.notes,
        updated_at = now()`,
      [
        s.id,
        s.query,
        s.category,
        s.intent,
        s.priority,
        s.baseline_enabled,
        s.target_topic || null,
        s.target_page_hint || null,
        s.notes || null,
      ],
    );
    q += 1;
  }

  const pulseIds: string[] = pulseQueries.query_ids || [];
  await pool.query(`UPDATE aio_queries SET pulse_enabled = FALSE`);
  if (pulseIds.length) {
    await pool.query(
      `UPDATE aio_queries SET pulse_enabled = TRUE WHERE id = ANY($1::text[])`,
      [pulseIds],
    );
  }

  let c = 0;
  for (const name of COMPETITORS) {
    const id = name.toLowerCase().replace(/\s+/g, "-");
    await pool.query(
      `INSERT INTO aio_competitors (id, name, aliases_json, active)
       VALUES ($1,$2,'[]'::jsonb,TRUE)
       ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, active = TRUE`,
      [id, name],
    );
    c += 1;
  }

  let content = 0;
  let maps = 0;
  for (const item of seedContent) {
    await pool.query(
      `INSERT INTO aio_content (
        id, url, title, content_type, status, published_at, hypothesis, active, updated_at
      ) VALUES ($1,$2,$3,$4,$5,$6::date,$7,TRUE,now())
      ON CONFLICT (id) DO UPDATE SET
        url = EXCLUDED.url,
        title = EXCLUDED.title,
        content_type = EXCLUDED.content_type,
        status = EXCLUDED.status,
        published_at = EXCLUDED.published_at,
        hypothesis = EXCLUDED.hypothesis,
        active = TRUE,
        updated_at = now()`,
      [
        item.id,
        item.url,
        item.title,
        item.content_type,
        item.status,
        item.published_at || null,
        item.hypothesis || null,
      ],
    );
    content += 1;
    await pool.query(`DELETE FROM aio_content_query_map WHERE content_id = $1`, [
      item.id,
    ]);
    const allIds = Array.from(
      new Set([...(item.query_ids || []), ...(item.primary_query_ids || [])]),
    );
    const primary = new Set(item.primary_query_ids || []);
    for (const queryId of allIds) {
      const exists = await pool.query(`SELECT 1 FROM aio_queries WHERE id = $1`, [
        queryId,
      ]);
      if (!exists.rowCount) continue;
      await pool.query(
        `INSERT INTO aio_content_query_map (content_id, query_id, is_primary)
         VALUES ($1,$2,$3)
         ON CONFLICT (content_id, query_id) DO UPDATE SET is_primary = EXCLUDED.is_primary`,
        [item.id, queryId, primary.has(queryId)],
      );
      maps += 1;
    }
  }

  await pool.query(
    `INSERT INTO aio_settings (key, value_json, updated_at)
     VALUES ('sacred_baseline', $1::jsonb, now())
     ON CONFLICT (key) DO UPDATE SET value_json = EXCLUDED.value_json, updated_at = now()`,
    [JSON.stringify(sacredBaseline)],
  );
  await pool.query(
    `INSERT INTO aio_settings (key, value_json, updated_at)
     VALUES ('pulse_queries', $1::jsonb, now())
     ON CONFLICT (key) DO UPDATE SET value_json = EXCLUDED.value_json, updated_at = now()`,
    [JSON.stringify(pulseQueries)],
  );

  const pulseHits = await pool.query(
    `SELECT COUNT(*)::int AS n FROM (
       SELECT DISTINCT ON (query_id) evaluation_json
       FROM aio_manual_audits
       WHERE query_id = ANY($1::text[])
       ORDER BY query_id, observed_at DESC
     ) x WHERE (evaluation_json->>'smpl_mentioned')::boolean`,
    [pulseIds],
  );

  console.log(
    JSON.stringify(
      {
        seeded: {
          queries: q,
          competitors: c,
          content,
          content_maps: maps,
          pulse_queries: pulseIds.length,
        },
        pulse_mention_count: pulseHits.rows[0]?.n ?? 0,
      },
      null,
      2,
    ),
  );
  await pool.end();
}

main().catch(async (e) => {
  console.error(e);
  await pool.end();
  process.exit(1);
});
