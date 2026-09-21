"""Patch Budget Engine Plan Assurance to consume /assess + /simulate + WHTT UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "frontend" / "public" / "budget-engine" / "index.html"

HELPERS = r'''
// ─── Plan Assurance platform engine (Python SoT via /assess) ───────────────
/** Cached assessment from POST /api/v1/predictive-planning/assess — live SoT for risks/WHTT. */
STATE._assureAssessment = STATE._assureAssessment || null;
STATE._assureAssessmentAt = STATE._assureAssessmentAt || null;
STATE._assureMethodCard = STATE._assureMethodCard || null;
STATE._warehouseBudgetVersionId = STATE._warehouseBudgetVersionId || null;
STATE._assureMcSeed = STATE._assureMcSeed || 42;
STATE._assureServerMc = STATE._assureServerMc || null;

const BUDGET_PERSIST_SKIP_EXTRA = new Set([
  '_assureAssessment',
  '_assureMethodCard',
  '_assureServerMc',
]);
for (const k of BUDGET_PERSIST_SKIP_EXTRA) BUDGET_PERSIST_SKIP.add(k);

function mapAssessmentResultsToRisks(assessment) {
  const results = (((assessment || {}).feasibility) || {}).results || [];
  return results
    .filter(r => r && r.status !== 'skipped')
    .map(r => ({
      id: r.id,
      severity: r.severity || 'ok',
      title: r.title || r.label || r.id,
      detail: r.detail || '',
      status: r.status,
      observed: r.observed,
      required: r.required,
      gap: r.gap,
    }));
}

function getAssuranceRisks(packet) {
  if (STATE._assureAssessment && STATE._assureAssessment.feasibility) {
    return mapAssessmentResultsToRisks(STATE._assureAssessment);
  }
  // Offline / first-paint fallback only — live SoT is /assess.
  return runBudgetRiskChecks(packet || buildBudgetAssurancePacket());
}

function buildSimulationSummaryFromSuite(suite) {
  if (!suite) return null;
  const breaks = [];
  const watches = [];
  (suite.cases || []).forEach(c => {
    (c.breaks || []).forEach(b => breaks.push(b));
    (c.watches || []).forEach(w => watches.push(w));
  });
  const mc = suite.mc || STATE._assureServerMc || null;
  const summary = {
    trials: mc && mc.n != null ? mc.n : null,
    breaks: Array.from(new Set(breaks)),
    watches: Array.from(new Set(watches)),
    p_arr_miss: mc && mc.arr ? mc.arr.pMiss : null,
    p_cash_below_floor: mc && mc.cash ? mc.cash.pBreak : null,
    p_ops_liquidity: mc ? mc.pOpsRisk : null,
    p_ae_short: mc ? mc.pAeShort : null,
    priors: mc && mc.sig ? { ...mc.sig, source: (mc.prior_source || 'client_or_server') } : null,
  };
  return summary;
}

function buildAssuranceHistoryForPriors(packet) {
  try {
    const hist = buildAssuranceHistoryPacket(packet || buildBudgetAssurancePacket());
    const ending = [];
    if (hist && hist.prior25 && hist.prior25.decArr != null) ending.push(hist.prior25.decArr);
    if (hist && hist.prior26 && hist.prior26.decArr != null) ending.push(hist.prior26.decArr);
    if (packet && packet.decArr != null) ending.push(packet.decArr);
    return {
      ending_arr: ending,
      ending_arr_yoy_pp: [],
      cpl_log_ratios: [],
      attrition_pp: [],
      pipeline_cover: [],
    };
  } catch (e) {
    return null;
  }
}

async function resolveBudgetOrgId() {
  if (!window.SMPLOutlook || typeof window.SMPLOutlook.resolveOrgId !== 'function') return null;
  try {
    return await window.SMPLOutlook.resolveOrgId({ waitForParent: true });
  } catch (e) {
    return null;
  }
}

async function fetchPlanAssessment(opts) {
  opts = opts || {};
  const packet = opts.packet || buildBudgetAssurancePacket();
  const orgId = opts.orgId || await resolveBudgetOrgId();
  if (!orgId) {
    console.warn('[plan-assurance] no org — keeping local risk fallback');
    return null;
  }
  const simulation = opts.simulation !== undefined
    ? opts.simulation
    : buildSimulationSummaryFromSuite(STATE._assureScenarioSuite);
  const body = {
    plan_ref: {
      organization_id: orgId,
      budget_version_id: STATE._warehouseBudgetVersionId || null,
      scenario: 'budget',
      period_label: packet.period_label,
      budget_year: packet.budget_year,
    },
    packet,
    simulation,
    include_passing_conditions: false,
    persist: !!(STATE._warehouseBudgetVersionId),
    history: buildAssuranceHistoryForPriors(packet),
    mc_seed: STATE._assureMcSeed || 42,
    prior_source: null,
  };
  const res = await fetch('/api/v1/predictive-planning/assess', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    console.warn('[plan-assurance] /assess failed', res.status, await res.text());
    return null;
  }
  const assessment = await res.json();
  STATE._assureAssessment = assessment;
  STATE._assureAssessmentAt = Date.now();
  STATE._assureMethodCard = assessment.method_card || null;
  try { persistBudgetState(); } catch (e) { /* ignore */ }
  return assessment;
}

async function fetchServerMonteCarlo(opts) {
  opts = opts || {};
  const packet = opts.packet || buildBudgetAssurancePacket();
  const orgId = opts.orgId || await resolveBudgetOrgId();
  if (!orgId) return null;
  const n = opts.n || 1000;
  const seed = opts.seed != null ? opts.seed : (STATE._assureMcSeed || 42);
  const suite = STATE._assureScenarioSuite;
  const breaks = [];
  const watches = [];
  if (suite && suite.cases) {
    suite.cases.forEach(c => {
      (c.breaks || []).forEach(b => breaks.push(b));
      (c.watches || []).forEach(w => watches.push(w));
    });
  }
  const res = await fetch('/api/v1/predictive-planning/simulate', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      plan_ref: {
        organization_id: orgId,
        budget_version_id: STATE._warehouseBudgetVersionId || null,
        scenario: 'budget',
        period_label: packet.period_label,
        budget_year: packet.budget_year,
      },
      packet,
      n_trials: n,
      seed,
      history: buildAssuranceHistoryForPriors(packet),
      breaks: Array.from(new Set(breaks)),
      watches: Array.from(new Set(watches)),
    }),
  });
  if (!res.ok) {
    console.warn('[plan-assurance] /simulate failed — browser MC fallback', res.status);
    return null;
  }
  const data = await res.json();
  STATE._assureMcSeed = seed;
  STATE._assureServerMc = data.result;
  STATE._assureMethodCard = data.method_card || STATE._assureMethodCard;
  return data;
}

function renderWhttHtml(assessment, mode) {
  const conditions = (assessment && assessment.what_has_to_be_true) || [];
  if (!conditions.length) {
    return '<div style="color:var(--text3);font-size:12px">No What-Has-To-Be-True conditions — plan clears feasibility (or assessment pending).</div>';
  }
  const order = { must_close: 0, must_confirm: 1, must_hold: 2 };
  const sorted = conditions.slice().sort((a, b) => (order[a.verdict] ?? 9) - (order[b.verdict] ?? 9));
  const groups = { must_close: [], must_confirm: [], must_hold: [] };
  sorted.forEach(c => {
    if (groups[c.verdict]) groups[c.verdict].push(c);
  });
  const labels = {
    must_close: 'Must close',
    must_confirm: 'Must confirm',
    must_hold: 'Must hold',
  };
  const sevClass = { must_close: 'high', must_confirm: 'med', must_hold: 'ok' };
  let html = '<div class="pa-whtt">';
  for (const key of ['must_close', 'must_confirm', 'must_hold']) {
    const rows = groups[key];
    if (!rows.length) continue;
    html += `<div class="pa-whtt-group"><div class="pa-whtt-lbl">${labels[key]} · ${rows.length}</div>`;
    rows.forEach(c => {
      const levers = (c.levers || []).slice(0, 4).join(', ');
      const extra = mode === 'tech'
        ? `<div class="assure-cite">${String(c.rationale || '').replace(/</g, '&lt;')}${levers ? ' · Levers: ' + levers.replace(/</g, '&lt;') : ''}</div>`
        : (levers ? `<div class="assure-cite">Levers: ${levers.replace(/</g, '&lt;')}</div>` : '');
      html += `<div class="assure-risk"><span class="assure-sev ${sevClass[key]}">${labels[key]}</span><div><strong>${String(c.statement || '').replace(/</g, '&lt;')}</strong>${extra}</div></div>`;
    });
    html += '</div>';
  }
  html += '</div>';
  return html;
}

function renderMethodCardHtml(card) {
  card = card || STATE._assureMethodCard;
  if (!card) return '';
  const priors = card.priors || {};
  const priorBits = Object.keys(priors).map(k => `${k}=${priors[k]}`).join(' · ');
  const notClaimed = (card.not_claimed || []).slice(0, 3).join('; ');
  return `<div class="pa-method-card"><div class="pa-card-lbl" style="margin-bottom:6px">Method & limits</div>
    <div style="font-size:12px;color:var(--text2)">${String(card.source || '').replace(/</g, '&lt;')} — ${(card.notes && card.notes[0] || '').replace(/</g, '&lt;')}</div>
    <div style="font-size:11px;color:var(--text3);margin-top:4px">Priors: ${priorBits.replace(/</g, '&lt;') || '—'}</div>
    <div style="font-size:11px;color:var(--text3);margin-top:2px">Not claimed: ${notClaimed.replace(/</g, '&lt;') || 'PoA / AutoML forecasting'}</div>
  </div>`;
}

async function ensurePlanAssessment(force) {
  if (!force && STATE._assureAssessment && STATE._assureAssessmentAt && (Date.now() - STATE._assureAssessmentAt) < 15000) {
    return STATE._assureAssessment;
  }
  return fetchPlanAssessment({});
}

'''

CSS = """
.pa-whtt { display:flex; flex-direction:column; gap:10px; margin-top:10px; }
.pa-whtt-group { display:flex; flex-direction:column; gap:6px; }
.pa-whtt-lbl { font-size:11px; font-weight:600; letter-spacing:0.04em; text-transform:uppercase; color:var(--text3); }
.pa-method-card { margin-top:12px; padding:10px 12px; border:1px solid var(--border, rgba(255,255,255,0.08)); border-radius:8px; background:rgba(0,0,0,0.12); }
"""


def main() -> None:
    text = PATH.read_text(encoding="utf-8")
    if "fetchPlanAssessment" in text:
        print("Already patched — skipping helper inject")
    else:
        # CSS
        anchor_css = "/* Analytics tab — full-width Plan Assurance (mockup vocabulary, live packets) */"
        if anchor_css in text and ".pa-whtt" not in text:
            text = text.replace(anchor_css, CSS + "\n" + anchor_css, 1)

        # Helpers before buildBudgetAssurancePacket
        marker = "function buildBudgetAssurancePacket() {"
        if marker not in text:
            raise SystemExit("buildBudgetAssurancePacket not found")
        text = text.replace(marker, HELPERS + "\n" + marker, 1)

    # Overview: use getAssuranceRisks
    text = text.replace(
        "  const packet = buildBudgetAssurancePacket();\n"
        "  const risks = runBudgetRiskChecks(packet);\n"
        "  const riskHtml = renderAssureFindingRows(risks);\n"
        "  const highN = risks.filter(r => r.severity === 'high').length;\n"
        "  const medN = risks.filter(r => r.severity === 'medium').length;\n"
        "  return `\n"
        "    <div class=\"slide-title\">Overview · FY${BUDGET_YEAR}</div>",
        "  const packet = buildBudgetAssurancePacket();\n"
        "  const risks = getAssuranceRisks(packet);\n"
        "  const riskHtml = renderAssureFindingRows(risks);\n"
        "  const highN = risks.filter(r => r.severity === 'high').length;\n"
        "  const medN = risks.filter(r => r.severity === 'medium').length;\n"
        "  return `\n"
        "    <div class=\"slide-title\">Overview · FY${BUDGET_YEAR}</div>",
        1,
    )

    # Overview banner honesty
    text = text.replace(
        "Plan Assurance lanes moved to <strong>Analytics</strong> (full-width). This page keeps formula-graph <strong>risk checks</strong> and the YoY operating visuals.",
        "Plan Assurance lanes live on <strong>Analytics</strong>. Risk checks here mirror the platform <code>/assess</code> SoT (local fallback only if API unavailable).",
        1,
    )
    text = text.replace(
        '<div class="assure-lane-lbl">Risk checks · formula-graph validations</div>',
        '<div class="assure-lane-lbl">Risk checks · Plan Assurance /assess SoT</div>',
        1,
    )

    # Analytics status: inject WHTT + method card after status body
    old_status = """          <div class="pa-body" id="assureStatusBody">${statusHtml}</div>
        </div>

        <div class="pa-card">
          <div class="pa-card-hd">
            <div class="pa-card-lbl">3 · Predictive / lever review</div>"""

    new_status = """          <div class="pa-body" id="assureStatusBody">${statusHtml}</div>
          <div id="assureWhttBody" style="padding:0 14px 12px">${whttHtml}</div>
          <div id="assureMethodBody" style="padding:0 14px 14px">${methodHtml}</div>
        </div>

        <div class="pa-card">
          <div class="pa-card-hd">
            <div class="pa-card-lbl">3 · Predictive / lever review</div>"""

    if old_status in text and "assureWhttBody" not in text:
        text = text.replace(old_status, new_status, 1)

    # renderAnalytics: compute whtt/method + use assessment narrative risks
    old_ra = """function renderAnalytics() {
  const packet = buildBudgetAssurancePacket();
  const hist = buildAssuranceHistoryPacket(packet);
  const suiteInfo = getAssureScenarioSuite(packet);
  const suite = suiteInfo.suite;
  const suiteStale = suiteInfo.stale;
  const statusHtml = (STATE._assureNarrative || buildDeterministicAssuranceNarrative(packet, runBudgetRiskChecks(packet)))
    .replace(/</g, '&lt;').replace(/\\n/g, '<br>');"""

    new_ra = """function renderAnalytics() {
  const packet = buildBudgetAssurancePacket();
  const hist = buildAssuranceHistoryPacket(packet);
  const suiteInfo = getAssureScenarioSuite(packet);
  const suite = suiteInfo.suite;
  const suiteStale = suiteInfo.stale;
  const risks = getAssuranceRisks(packet);
  const whttHtml = renderWhttHtml(STATE._assureAssessment, modePref());
  const methodHtml = renderMethodCardHtml(STATE._assureMethodCard);
  const statusHtml = (STATE._assureNarrative || buildDeterministicAssuranceNarrative(packet, risks))
    .replace(/</g, '&lt;').replace(/\\n/g, '<br>');"""

    # modePref may not exist — use STATE.paMode inline instead
    new_ra = new_ra.replace("modePref()", "(STATE.paMode === 'tech' ? 'tech' : 'plain')")

    if "const whttHtml = renderWhttHtml" not in text:
        if old_ra not in text:
            # try without escaped newline
            old_ra2 = old_ra.replace("\\n", "\n")
            new_ra2 = new_ra.replace("\\n", "\n")
            if old_ra2 in text:
                text = text.replace(old_ra2, new_ra2, 1)
            else:
                print("WARNING: renderAnalytics block not found exactly")
        else:
            text = text.replace(old_ra, new_ra, 1)

    # Fix if we inserted whttHtml vars but renderAnalytics still uses runBudgetRiskChecks for narrative
    text = text.replace(
        "buildDeterministicAssuranceNarrative(packet, runBudgetRiskChecks(packet))",
        "buildDeterministicAssuranceNarrative(packet, getAssuranceRisks(packet))",
    )
    text = text.replace(
        "const risks = runBudgetRiskChecks(packet);\n  const soT = buildDeterministicAssuranceNarrative(p, risks);",
        "const risks = getAssuranceRisks(packet);\n  const soT = buildDeterministicAssuranceNarrative(p, risks);",
    )
    text = text.replace(
        "  const risks = runBudgetRiskChecks(packet);\n  const soT = buildDeterministicAssuranceNarrative(packet, risks);",
        "  const risks = getAssuranceRisks(packet);\n  const soT = buildDeterministicAssuranceNarrative(packet, risks);",
    )

    # refreshAssuranceNarrative — call /assess first
    old_refresh = """window.refreshAssuranceNarrative = async function(useLlm) {
  const packet = buildBudgetAssurancePacket();
  const risks = getAssuranceRisks(packet);
  const soT = buildDeterministicAssuranceNarrative(packet, risks);
  let text = soT;
  const body = document.getElementById('assureStatusBody');
  if (body) body.innerHTML = '<span style="color:var(--text3)">Generating…</span>';

  if (useLlm) {
    const allow = buildAssuranceEvidenceAllowlist({ soT, packet, lane: 'status' });
    text = await resolveAssuranceGenerate(soT, allow, `FY${BUDGET_YEAR} Budget status`);
  }

  STATE._assureNarrative = text;
  STATE._assureNarrativeAt = Date.now();
  try { persistBudgetState(); } catch (e) { /* ignore */ }
  refresh();
};"""

    new_refresh = """window.refreshAssuranceNarrative = async function(useLlm) {
  const packet = buildBudgetAssurancePacket();
  const body = document.getElementById('assureStatusBody');
  if (body) body.innerHTML = '<span style="color:var(--text3)">Assessing plan…</span>';
  try {
    await fetchPlanAssessment({ packet, simulation: buildSimulationSummaryFromSuite(STATE._assureScenarioSuite) });
  } catch (e) {
    console.warn('[plan-assurance] assess refresh failed', e);
  }
  const risks = getAssuranceRisks(packet);
  const soT = buildDeterministicAssuranceNarrative(packet, risks);
  let text = soT;
  if (body) body.innerHTML = '<span style="color:var(--text3)">Generating…</span>';

  if (useLlm) {
    const allow = buildAssuranceEvidenceAllowlist({ soT, packet, lane: 'status' });
    text = await resolveAssuranceGenerate(soT, allow, `FY${BUDGET_YEAR} Budget status`);
  }

  STATE._assureNarrative = text;
  STATE._assureNarrativeAt = Date.now();
  try { persistBudgetState(); } catch (e) { /* ignore */ }
  refresh();
};

/** Kick /assess when Analytics opens so WHTT + risk SoT are fresh. */
window.ensureAnalyticsAssessment = async function() {
  try { await ensurePlanAssessment(false); refresh(); } catch (e) { /* ignore */ }
};
"""

    # May still have runBudgetRiskChecks in refresh if earlier replace didn't catch
    if "window.refreshAssuranceNarrative = async function(useLlm) {" in text:
        import re
        text, n = re.subn(
            r"window\.refreshAssuranceNarrative = async function\(useLlm\) \{.*?\n\};",
            new_refresh.rstrip() + "\n",
            text,
            count=1,
            flags=re.S,
        )
        print("refreshAssuranceNarrative replaced", n)

    # Track warehouse version id on promote success
    if "STATE._warehouseBudgetVersionId = draft.id" not in text:
        text = text.replace(
            "if (status !== 'final') return { ok: true, draft: true, id: draft.id };",
            "STATE._warehouseBudgetVersionId = draft.id;\n"
            "  if (status !== 'final') return { ok: true, draft: true, id: draft.id };",
            1,
        )
        text = text.replace(
            "return { ok: true, promoted: true, id: draft.id };",
            "STATE._warehouseBudgetVersionId = draft.id;\n"
            "  try { await fetchPlanAssessment({ persist: true }); } catch (e) { /* ignore */ }\n"
            "  return { ok: true, promoted: true, id: draft.id };",
            1,
        )

    # After scenario suite saved, try server MC then re-assess
    hook = "STATE._assureScenarioSuite = suite;\n    STATE._assureScenarioNarrative = suite.narrative;"
    hook_new = (
        "STATE._assureScenarioSuite = suite;\n"
        "    STATE._assureScenarioNarrative = suite.narrative;\n"
        "    try {\n"
        "      const sim = await fetchServerMonteCarlo({ packet: buildBudgetAssurancePacket(), n: (suite.mc && suite.mc.n) || 1000 });\n"
        "      if (sim && suite) {\n"
        "        suite.serverMc = sim.result;\n"
        "        suite.method_card = sim.method_card;\n"
        "        if (!suite.mc) suite.mc = sim.result;\n"
        "      }\n"
        "      await fetchPlanAssessment({ packet: buildBudgetAssurancePacket(), simulation: buildSimulationSummaryFromSuite(suite) });\n"
        "    } catch (e) { console.warn('[plan-assurance] post-scenario assess/simulate', e); }\n"
    )
    if "fetchServerMonteCarlo({ packet: buildBudgetAssurancePacket()" not in text:
        # Only replace first occurrence carefully
        idx = text.find(hook)
        if idx >= 0:
            text = text[:idx] + hook_new + text[idx + len(hook) :]
            print("scenario hook injected")
        else:
            print("WARNING: scenario suite hook not found")

    # showTab analytics kick
    if "ensureAnalyticsAssessment" not in text or text.count("ensureAnalyticsAssessment") < 2:
        # find showTab function and add kick — soft
        if "function showTab(tab)" in text and "if (tab === 'analytics')" not in text:
            text = text.replace(
                "function showTab(tab) {",
                "function showTab(tab) {\n"
                "  if (tab === 'analytics') { setTimeout(() => { if (window.ensureAnalyticsAssessment) window.ensureAnalyticsAssessment(); }, 0); }\n",
                1,
            )

    # Comment on runBudgetRiskChecks
    text = text.replace(
        "function runBudgetRiskChecks(packet) {\n  const p = packet || buildBudgetAssurancePacket();\n  const out = [];",
        "/** Offline/parity fallback only. Live UI must prefer getAssuranceRisks() → /assess. */\n"
        "function runBudgetRiskChecks(packet) {\n  const p = packet || buildBudgetAssurancePacket();\n  const out = [];",
        1,
    )

    PATH.write_text(text, encoding="utf-8")
    print("Wrote", PATH)
    print("fetchPlanAssessment in file:", "fetchPlanAssessment" in text)
    print("renderWhttHtml in file:", "renderWhttHtml" in text)
    print("assureWhttBody in file:", "assureWhttBody" in text)


if __name__ == "__main__":
    main()
