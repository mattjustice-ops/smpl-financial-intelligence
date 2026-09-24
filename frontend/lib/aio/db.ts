import googleGenaiBaseline from "@/lib/aio/data/google_genai_baseline.json";
import pulseQueries from "@/lib/aio/data/pulse_queries.json";
import sacredBaseline from "@/lib/aio/data/sacred_baseline.json";
import seedContent from "@/lib/aio/data/seed_content.json";
import seedQueries from "@/lib/aio/data/seed_queries.json";
import { getAuthPgPool } from "@/lib/auth/db";
import {
  DEFAULT_COMPETITORS,
  EVALUATOR_VERSION,
  evaluateManualAudit,
  type AioEvaluation,
} from "@/lib/aio/evaluate";
import { ensureAioSchema } from "@/lib/aio/schema";

export type AioQueryRow = {
  id: string;
  query_text: string;
  category: string;
  intent: string;
  priority: number;
  baseline_enabled: boolean;
  pulse_enabled: boolean;
  target_topic: string | null;
  target_page_hint: string | null;
  notes: string | null;
  version: number;
  active: boolean;
};

export type AioContentRow = {
  id: string;
  url: string;
  title: string;
  content_type: string;
  status: string;
  published_at: string | null;
  hypothesis: string | null;
  active: boolean;
  primary_query_ids: string[];
  query_ids: string[];
};

type SeedContent = {
  id: string;
  url: string;
  title: string;
  content_type: string;
  status: string;
  published_at: string | null;
  hypothesis: string;
  primary_query_ids: string[];
  query_ids: string[];
};

export type ManualAuditRow = {
  id: string;
  batch_id: string | null;
  query_id: string | null;
  query_text: string;
  observed_at: string;
  product_note: string | null;
  raw_response: string;
  citations_json: string[];
  clean_session_confirmed: boolean;
  notes: string | null;
  evaluation_json: AioEvaluation;
  evaluator_version: string;
  created_by: string | null;
  created_at: string;
};

type SeedQuery = {
  id: string;
  query: string;
  category: string;
  intent: string;
  priority: number;
  baseline_enabled: boolean;
  target_topic: string;
  target_page_hint: string;
  notes: string;
};

function loadSeedQueries(): SeedQuery[] {
  return seedQueries as SeedQuery[];
}

export async function seedAioConfig(): Promise<{
  queries: number;
  competitors: number;
  content: number;
  content_maps: number;
  pulse_queries: number;
}> {
  await ensureAioSchema();
  const pool = getAuthPgPool();
  const seeds = loadSeedQueries();
  let q = 0;
  for (const s of seeds) {
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

  const pulseIds = (pulseQueries as { query_ids: string[] }).query_ids || [];
  await pool.query(`UPDATE aio_queries SET pulse_enabled = FALSE`);
  if (pulseIds.length) {
    await pool.query(
      `UPDATE aio_queries SET pulse_enabled = TRUE WHERE id = ANY($1::text[])`,
      [pulseIds],
    );
  }

  let c = 0;
  for (const name of DEFAULT_COMPETITORS) {
    const id = name.toLowerCase().replace(/\s+/g, "-");
    await pool.query(
      `INSERT INTO aio_competitors (id, name, aliases_json, active)
       VALUES ($1,$2,'[]'::jsonb,TRUE)
       ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, active = TRUE`,
      [id, name],
    );
    c += 1;
  }

  const contentSeed = await seedAioContent();

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
  await pool.query(
    `INSERT INTO aio_settings (key, value_json, updated_at)
     VALUES ('google_genai_baseline', $1::jsonb, now())
     ON CONFLICT (key) DO UPDATE SET value_json = EXCLUDED.value_json, updated_at = now()`,
    [JSON.stringify(googleGenaiBaseline)],
  );

  return {
    queries: q,
    competitors: c,
    content: contentSeed.content,
    content_maps: contentSeed.maps,
    pulse_queries: pulseIds.length,
  };
}

export async function seedAioContent(): Promise<{ content: number; maps: number }> {
  await ensureAioSchema();
  const pool = getAuthPgPool();
  const items = seedContent as SeedContent[];
  let content = 0;
  let maps = 0;

  for (const item of items) {
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
      const exists = await pool.query(
        `SELECT 1 FROM aio_queries WHERE id = $1`,
        [queryId],
      );
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

  return { content, maps };
}

export async function listAioContent(): Promise<AioContentRow[]> {
  await ensureAioSchema();
  const pool = getAuthPgPool();
  const { rows } = await pool.query(
    `SELECT c.id, c.url, c.title, c.content_type, c.status, c.published_at,
            c.hypothesis, c.active,
            COALESCE(
              (SELECT array_agg(m.query_id ORDER BY m.query_id)
               FROM aio_content_query_map m
               WHERE m.content_id = c.id AND m.is_primary),
              '{}'::text[]
            ) AS primary_query_ids,
            COALESCE(
              (SELECT array_agg(m.query_id ORDER BY m.query_id)
               FROM aio_content_query_map m
               WHERE m.content_id = c.id),
              '{}'::text[]
            ) AS query_ids
     FROM aio_content c
     WHERE c.active = TRUE
     ORDER BY c.content_type, c.title`,
  );
  return rows.map((r) => ({
    id: String(r.id),
    url: String(r.url),
    title: String(r.title),
    content_type: String(r.content_type),
    status: String(r.status),
    published_at: r.published_at
      ? new Date(String(r.published_at)).toISOString().slice(0, 10)
      : null,
    hypothesis: (r.hypothesis as string) || null,
    active: Boolean(r.active),
    primary_query_ids: (r.primary_query_ids as string[]) || [],
    query_ids: (r.query_ids as string[]) || [],
  }));
}

export async function getPulseOverview() {
  await ensureAioSchema();
  const pool = getAuthPgPool();
  const pulseIds = (pulseQueries as { query_ids: string[] }).query_ids || [];
  if (!pulseIds.length) {
    return {
      query_ids: [],
      scored: 0,
      mention_count: 0,
      mention_rate: 0,
      owned_citation_count: 0,
      rows: [] as Array<{
        query_id: string;
        query_text: string;
        smpl_mentioned: boolean;
        recommendation_strength: string;
        owned_cited: boolean;
      }>,
    };
  }

  const { rows } = await pool.query(
    `SELECT DISTINCT ON (a.query_id)
        a.query_id, a.query_text, a.evaluation_json, a.observed_at
     FROM aio_manual_audits a
     WHERE a.query_id = ANY($1::text[])
     ORDER BY a.query_id, a.observed_at DESC`,
    [pulseIds],
  );

  const byId = new Map(rows.map((r) => [String(r.query_id), r]));
  const { rows: qrows } = await pool.query(
    `SELECT id, query_text FROM aio_queries WHERE id = ANY($1::text[])`,
    [pulseIds],
  );
  const textById = new Map(qrows.map((r) => [String(r.id), String(r.query_text)]));

  let mention = 0;
  let owned = 0;
  const out = pulseIds.map((id) => {
    const row = byId.get(id);
    const e = (row?.evaluation_json || {}) as AioEvaluation;
    if (e.smpl_mentioned) mention += 1;
    if (e.smpl_owned_domain_cited) owned += 1;
    return {
      query_id: id,
      query_text: textById.get(id) || String(row?.query_text || id),
      smpl_mentioned: Boolean(e.smpl_mentioned),
      recommendation_strength: e.recommendation_strength || "none",
      owned_cited: Boolean(e.smpl_owned_domain_cited),
    };
  });

  return {
    query_ids: pulseIds,
    scored: rows.length,
    mention_count: mention,
    mention_rate: pulseIds.length
      ? Number((mention / pulseIds.length).toFixed(3))
      : 0,
    owned_citation_count: owned,
    rows: out,
    sacred_baseline: sacredBaseline,
    google_genai_baseline: googleGenaiBaseline,
  };
}

export async function listQueries(opts?: {
  priorityMin?: number;
  activeOnly?: boolean;
}): Promise<AioQueryRow[]> {
  await ensureAioSchema();
  const pool = getAuthPgPool();
  const params: unknown[] = [];
  const where: string[] = [];
  if (opts?.activeOnly !== false) {
    where.push("active = TRUE");
  }
  if (opts?.priorityMin != null) {
    params.push(opts.priorityMin);
    where.push(`priority >= $${params.length}`);
  }
  const sql = `
    SELECT id, query_text, category, intent, priority, baseline_enabled,
           COALESCE(pulse_enabled, FALSE) AS pulse_enabled,
           target_topic, target_page_hint, notes, version, active
    FROM aio_queries
    ${where.length ? `WHERE ${where.join(" AND ")}` : ""}
    ORDER BY priority DESC, category ASC, id ASC`;
  const { rows } = await pool.query(sql, params);
  return rows.map((r) => ({
    ...r,
    pulse_enabled: Boolean(r.pulse_enabled),
  })) as AioQueryRow[];
}

export async function createManualAudit(input: {
  queryId?: string | null;
  queryText: string;
  rawResponse: string;
  citationUrls?: string[];
  productNote?: string;
  notes?: string;
  cleanSessionConfirmed?: boolean;
  observedAt?: string;
  batchName?: string;
  createdBy?: string | null;
}): Promise<ManualAuditRow> {
  await ensureAioSchema();
  const pool = getAuthPgPool();

  const { rows: compRows } = await pool.query<{ name: string }>(
    `SELECT name FROM aio_competitors WHERE active = TRUE ORDER BY name`,
  );
  const competitors = compRows.map((r) => r.name);
  const evaluation = evaluateManualAudit({
    query: input.queryText,
    answer: input.rawResponse,
    citationUrls: input.citationUrls,
    competitors: competitors.length ? competitors : [...DEFAULT_COMPETITORS],
  });

  let batchId: string | null = null;
  if (input.batchName?.trim()) {
    const b = await pool.query<{ id: string }>(
      `INSERT INTO aio_batches (name, source_type, notes)
       VALUES ($1,'manual_chatgpt',$2) RETURNING id`,
      [input.batchName.trim(), "Manual ChatGPT Search audit"],
    );
    batchId = b.rows[0]?.id ?? null;
  }

  const { rows } = await pool.query(
    `INSERT INTO aio_manual_audits (
      batch_id, query_id, query_text, observed_at, product_note, raw_response,
      citations_json, clean_session_confirmed, notes, evaluation_json,
      evaluator_version, created_by
    ) VALUES (
      $1,$2,$3,COALESCE($4::timestamptz, now()),$5,$6,$7::jsonb,$8,$9,$10::jsonb,$11,$12
    )
    RETURNING *`,
    [
      batchId,
      input.queryId || null,
      input.queryText,
      input.observedAt || null,
      input.productNote || null,
      input.rawResponse,
      JSON.stringify(input.citationUrls || []),
      Boolean(input.cleanSessionConfirmed),
      input.notes || null,
      JSON.stringify(evaluation),
      EVALUATOR_VERSION,
      input.createdBy || null,
    ],
  );
  return mapAudit(rows[0]);
}

function mapAudit(row: Record<string, unknown>): ManualAuditRow {
  return {
    id: String(row.id),
    batch_id: (row.batch_id as string) || null,
    query_id: (row.query_id as string) || null,
    query_text: String(row.query_text),
    observed_at: new Date(String(row.observed_at)).toISOString(),
    product_note: (row.product_note as string) || null,
    raw_response: String(row.raw_response),
    citations_json: Array.isArray(row.citations_json)
      ? (row.citations_json as string[])
      : [],
    clean_session_confirmed: Boolean(row.clean_session_confirmed),
    notes: (row.notes as string) || null,
    evaluation_json: row.evaluation_json as AioEvaluation,
    evaluator_version: String(row.evaluator_version || EVALUATOR_VERSION),
    created_by: (row.created_by as string) || null,
    created_at: new Date(String(row.created_at)).toISOString(),
  };
}

export async function listManualAudits(limit = 50): Promise<ManualAuditRow[]> {
  await ensureAioSchema();
  const pool = getAuthPgPool();
  const { rows } = await pool.query(
    `SELECT * FROM aio_manual_audits ORDER BY observed_at DESC LIMIT $1`,
    [limit],
  );
  return rows.map(mapAudit);
}

export async function getOverview() {
  await ensureAioSchema();
  const pool = getAuthPgPool();
  const { rows: counts } = await pool.query<{
    query_count: string;
    audit_count: string;
  }>(
    `SELECT
      (SELECT COUNT(*)::text FROM aio_queries WHERE active) AS query_count,
      (SELECT COUNT(*)::text FROM aio_manual_audits) AS audit_count`,
  );

  const { rows: audits } = await pool.query(
    `SELECT evaluation_json, query_id, query_text, observed_at
     FROM aio_manual_audits
     ORDER BY observed_at DESC
     LIMIT 500`,
  );

  const total = audits.length;
  let mentioned = 0;
  let recommended = 0;
  let strong = 0;
  let cited = 0;
  let owned = 0;
  let positioningSum = 0;
  const competitorMentions: Record<string, number> = {};
  let smplVendorMentions = 0;
  let totalVendorMentions = 0;
  const gaps: Array<{ query_id: string | null; query_text: string }> = [];

  for (const row of audits) {
    const e = row.evaluation_json as AioEvaluation;
    if (e.smpl_mentioned) {
      mentioned += 1;
      smplVendorMentions += 1;
      totalVendorMentions += 1;
    }
    if (
      e.recommendation_strength === "shortlisted" ||
      e.recommendation_strength === "recommended" ||
      e.recommendation_strength === "top_pick"
    ) {
      recommended += 1;
    }
    if (
      e.recommendation_strength === "recommended" ||
      e.recommendation_strength === "top_pick"
    ) {
      strong += 1;
    }
    if (e.smpl_cited) cited += 1;
    if (e.smpl_owned_domain_cited) owned += 1;
    positioningSum += e.positioning_accuracy || 0;
    for (const c of e.competitors || []) {
      if (c.mentioned) {
        competitorMentions[c.name] = (competitorMentions[c.name] || 0) + 1;
        totalVendorMentions += 1;
      }
    }
    if (!e.smpl_mentioned) {
      gaps.push({
        query_id: row.query_id,
        query_text: row.query_text,
      });
    }
  }

  const rate = (n: number) => (total ? Number((n / total).toFixed(3)) : 0);

  // Parallel rules_v2 rescore of the latest named Full-46 batch (does not overwrite stored rows).
  const { rows: latestBatch } = await pool.query<{
    id: string;
    name: string;
  }>(
    `SELECT id, name FROM aio_batches
     WHERE name ILIKE 'Full 46%'
     ORDER BY created_at DESC
     LIMIT 1`,
  );
  let scoring_audit: Record<string, unknown> | null = null;
  if (latestBatch[0]) {
    const { rows: batchAudits } = await pool.query(
      `SELECT query_id, query_text, raw_response, citations_json, evaluation_json, evaluator_version
       FROM aio_manual_audits WHERE batch_id = $1`,
      [latestBatch[0].id],
    );
    const { rows: compRows } = await pool.query<{ name: string }>(
      `SELECT name FROM aio_competitors WHERE active = TRUE ORDER BY name`,
    );
    const competitors = compRows.length
      ? compRows.map((r) => r.name)
      : [...DEFAULT_COMPETITORS];

    let storedMentions = 0;
    let v2Mentions = 0;
    let storedShortlistPlus = 0;
    let v2ShortlistPlus = 0;
    let storedOwned = 0;
    let v2Owned = 0;
    const strength_changes: Array<{
      query_id: string | null;
      stored: string;
      rules_v2: string;
    }> = [];

    for (const row of batchAudits) {
      const stored = row.evaluation_json as AioEvaluation;
      const v2 = evaluateManualAudit({
        query: String(row.query_text),
        answer: String(row.raw_response),
        citationUrls: Array.isArray(row.citations_json)
          ? (row.citations_json as string[])
          : [],
        competitors,
      });
      if (stored.smpl_mentioned) storedMentions += 1;
      if (v2.smpl_mentioned) v2Mentions += 1;
      if (
        ["shortlisted", "recommended", "top_pick"].includes(
          stored.recommendation_strength,
        )
      ) {
        storedShortlistPlus += 1;
      }
      if (
        ["shortlisted", "recommended", "top_pick"].includes(
          v2.recommendation_strength,
        )
      ) {
        v2ShortlistPlus += 1;
      }
      if (stored.smpl_owned_domain_cited) storedOwned += 1;
      if (v2.smpl_owned_domain_cited) v2Owned += 1;
      if (
        stored.recommendation_strength !== v2.recommendation_strength ||
        stored.smpl_mentioned !== v2.smpl_mentioned
      ) {
        strength_changes.push({
          query_id: row.query_id as string | null,
          stored: stored.recommendation_strength,
          rules_v2: v2.recommendation_strength,
        });
      }
    }

    scoring_audit = {
      batch_name: latestBatch[0].name,
      batch_id: latestBatch[0].id,
      n: batchAudits.length,
      current_evaluator: EVALUATOR_VERSION,
      note: "rules_v2 is computed live from raw answers. Stored evaluation_json is preserved as historical.",
      stored: {
        mentions: storedMentions,
        shortlist_plus: storedShortlistPlus,
        owned_citations: storedOwned,
      },
      rules_v2: {
        mentions: v2Mentions,
        shortlist_plus: v2ShortlistPlus,
        owned_citations: v2Owned,
      },
      strength_changes,
    };
  }

  return {
    query_count: Number(counts[0]?.query_count || 0),
    audit_count: Number(counts[0]?.audit_count || 0),
    scored_audits: total,
    mention_rate: rate(mentioned),
    recommendation_rate: rate(recommended),
    strong_recommendation_rate: rate(strong),
    citation_rate: rate(cited),
    owned_domain_citation_rate: rate(owned),
    avg_positioning_accuracy: total
      ? Number((positioningSum / total).toFixed(3))
      : 0,
    share_of_voice: totalVendorMentions
      ? Number((smplVendorMentions / totalVendorMentions).toFixed(3))
      : 0,
    competitor_mentions: Object.entries(competitorMentions)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count),
    recent_gaps: gaps.slice(0, 15),
    chatgpt_search_baseline: sacredBaseline,
    google_genai_baseline: googleGenaiBaseline,
    scoring_audit,
    engine_diagnosis:
      "Google: becoming retrievable. ChatGPT: not yet reliably classifiable/shortlisted. Track engines separately.",
    disclosure:
      "Dual baselines: controlled ChatGPT Search audits + frozen Google Generative AI Search Console snapshot. New imports score with rules_v2; historical evaluation_json is preserved. Not an OpenAI ranking score.",
  };
}
