import { NextResponse } from "next/server";

import { requireSmplOpsAdmin } from "@/lib/auth/require-ops-admin";
import { pickDeflectScript } from "@/lib/sales-talk/deflect";
import { loadSalesKb } from "@/lib/sales-talk/kb";
import { parseAnswerBullets, rephraseKbAnswer } from "@/lib/sales-talk/rephrase";
import { retrieveWithOptionalRouter } from "@/lib/sales-talk/router";
import type {
  SalesAudience,
  SalesTalkAnswerResponse,
} from "@/lib/sales-talk/types";

export const runtime = "nodejs";

const AUDIENCES = new Set<SalesAudience>([
  "cfo",
  "it",
  "fpa",
  "ceo",
  "engineer",
  "investor",
  "general",
]);

type Body = {
  question?: unknown;
  audience?: unknown;
  includeInternalDeep?: unknown;
  rephrase?: unknown;
};

function parseAudience(value: unknown): SalesAudience | null {
  if (typeof value !== "string" || !value.trim()) return null;
  const normalized = value.trim().toLowerCase() as SalesAudience;
  return AUDIENCES.has(normalized) ? normalized : null;
}

function kbBullets(entry: { answer_bullets?: string[]; answer: string }): string[] | null {
  if (Array.isArray(entry.answer_bullets) && entry.answer_bullets.length > 0) {
    return entry.answer_bullets.map((b) => b.trim()).filter(Boolean);
  }
  return parseAnswerBullets(entry.answer);
}

export async function POST(request: Request) {
  const access = await requireSmplOpsAdmin();
  if ("error" in access) {
    return access.error;
  }

  let body: Body;
  try {
    body = (await request.json()) as Body;
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body." }, { status: 400 });
  }

  const question = typeof body.question === "string" ? body.question.trim() : "";
  if (!question || question.length < 3) {
    return NextResponse.json({ detail: "question is required." }, { status: 400 });
  }
  if (question.length > 800) {
    return NextResponse.json({ detail: "question is too long." }, { status: 400 });
  }

  const audience = parseAudience(body.audience);
  const includeInternalDeep = body.includeInternalDeep === true;
  const wantRephrase = body.rephrase !== false;

  const kb = loadSalesKb();
  const deflectScript = pickDeflectScript(question);
  // Keyword shortlist (+ optional Claude ID router). Fail closed → deflect.
  const { matches } = await retrieveWithOptionalRouter({
    question,
    entries: kb.entries,
    audience,
    includeInternalDeep,
    limit: 3,
  });

  if (matches.length === 0) {
    const response: SalesTalkAnswerResponse = {
      status: "no_prepared_answer",
      question,
      entryId: null,
      title: null,
      answer: null,
      answerBullets: null,
      confidence: null,
      source: null,
      tone: null,
      deflectScript,
      score: null,
      rephrased: false,
      matches: [],
    };
    return NextResponse.json(response);
  }

  const top = matches[0]!;
  const entry = top.entry;

  if (entry.confidence === "do-not-answer") {
    const response: SalesTalkAnswerResponse = {
      status: "deflect",
      question,
      entryId: entry.id,
      title: entry.title,
      answer: null,
      answerBullets: null,
      confidence: entry.confidence,
      source: entry.source,
      tone: entry.tone ?? "external_safe",
      // Prefer entry script; else context-aware (figure language only for pricing/TAM/funding DNA)
      deflectScript: entry.deflect_script?.trim() || pickDeflectScript(question),
      score: top.score,
      rephrased: false,
      matches: matches.map((m) => ({
        id: m.entry.id,
        title: m.entry.title,
        score: Number(m.score.toFixed(2)),
        confidence: m.entry.confidence,
      })),
    };
    return NextResponse.json(response);
  }

  let answerText = entry.answer;
  let answerBullets = kbBullets(entry);
  let rephrased = false;
  if (wantRephrase) {
    const rewritten = await rephraseKbAnswer({ question, entry, audience });
    if (rewritten) {
      answerText = rewritten;
      rephrased = true;
      const parsed = parseAnswerBullets(rewritten);
      answerBullets = parsed ?? answerBullets;
    }
  }

  const response: SalesTalkAnswerResponse = {
    status: "matched",
    question,
    entryId: entry.id,
    title: entry.title,
    answer: answerText,
    answerBullets,
    confidence: entry.confidence,
    source: entry.source,
    tone: entry.tone ?? "external_safe",
    deflectScript,
    score: top.score,
    rephrased,
    matches: matches.map((m) => ({
      id: m.entry.id,
      title: m.entry.title,
      score: Number(m.score.toFixed(2)),
      confidence: m.entry.confidence,
    })),
  };
  return NextResponse.json(response);
}
