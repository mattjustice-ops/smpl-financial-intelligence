/* Confirmed funding rounds. The forecast engine writes them; the board reads the same list.
   A round is cash in an open month. Equity is paid-in capital. Debt is a balance plus interest.
   Warrant coverage is the slice of a debt round that is equity. */
(function (root, factory) {
  var api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.SMPLFinancing = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  var STORAGE_KEY = "smpl.forecast.financingRounds.v1";

  function cents(n) {
    return Math.round((Number(n) || 0) * 100) / 100;
  }

  function monthOk(value) {
    return typeof value === "string" && /^\d{4}-\d{2}$/.test(value);
  }

  function numOrNull(value) {
    if (value == null || value === "") return null;
    var n = Number(value);
    return isFinite(n) ? n : null;
  }

  function normalizeRound(raw, closeMonth) {
    raw = raw || {};
    var month = String(raw.month || "");
    if (!monthOk(month)) return { ok: false, error: "Choose the month the cash is wired." };
    if (closeMonth && month <= closeMonth) return { ok: false, error: "The wire month has to be after the close." };
    var instrument = raw.instrument === "debt" ? "debt" : raw.instrument === "equity" ? "equity" : "";
    if (!instrument) return { ok: false, error: "Choose equity or debt." };
    var gross = numOrNull(raw.gross);
    var fees = numOrNull(raw.fees);
    if (fees == null) fees = 0;
    if (gross == null || gross <= 0) return { ok: false, error: "Enter the gross amount." };
    if (fees < 0 || fees >= gross) return { ok: false, error: "Fees have to be less than the gross amount." };
    var net = cents(gross - fees);
    var warrantPct = instrument === "debt" ? numOrNull(raw.warrantPct) || 0 : 0;
    if (warrantPct < 0 || warrantPct > 100) return { ok: false, error: "Warrant coverage is a percent from 0 to 100." };
    var ratePct = instrument === "debt" ? numOrNull(raw.ratePct) || 0 : 0;
    if (ratePct < 0) return { ok: false, error: "The interest rate cannot be negative." };
    var interestStart = instrument === "debt" ? String(raw.interestStart || month) : month;
    if (!monthOk(interestStart) || interestStart < month) return { ok: false, error: "Interest starts in the wire month or later." };
    var principal = instrument === "debt" ? numOrNull(raw.principalDue) || 0 : 0;
    var principalMonth = principal ? String(raw.principalMonth || "") : "";
    if (principal < 0) return { ok: false, error: "Principal repaid this year cannot be negative." };
    var debtProceeds = instrument === "debt" ? cents(net * (1 - warrantPct / 100)) : 0;
    var equityProceeds = cents(net - debtProceeds);
    if (principal > debtProceeds + 0.01) return { ok: false, error: "Principal repaid this year cannot exceed the debt." };
    if (principal && (!monthOk(principalMonth) || principalMonth < month)) {
      return { ok: false, error: "Choose the month principal is repaid." };
    }
    var maturity = raw.maturity ? String(raw.maturity) : "";
    if (maturity && !monthOk(maturity)) return { ok: false, error: "Maturity is a month, like 2028-08." };
    return {
      ok: true,
      round: {
        id: raw.id || "",
        month: month,
        instrument: instrument,
        gross: cents(gross),
        fees: cents(fees),
        net: net,
        security: String(raw.security || "").slice(0, 80),
        pricePerShare: numOrNull(raw.pricePerShare),
        shares: numOrNull(raw.shares),
        ratePct: ratePct,
        interestStart: interestStart,
        principalDue: cents(principal),
        principalMonth: principalMonth,
        maturity: maturity,
        warrantPct: warrantPct,
        debtProceeds: debtProceeds,
        equityProceeds: equityProceeds,
      },
    };
  }

  function blankEffect() {
    return { financing: 0, interest: 0, debtDelta: 0, equityDelta: 0, debtBalance: 0 };
  }

  /** Monthly cash, interest, and the debt or equity split. Closed months stay at zero. */
  function effects(rounds, periods, closeMonth) {
    var open = [];
    (rounds || []).forEach(function (raw) {
      var parsed = normalizeRound(raw, closeMonth);
      if (!parsed.ok) return;
      open.push({
        month: parsed.round.month,
        instrument: parsed.round.instrument,
        net: parsed.round.net,
        debtProceeds: parsed.round.debtProceeds,
        equityProceeds: parsed.round.equityProceeds,
        rate: parsed.round.ratePct / 100,
        interestStart: parsed.round.interestStart,
        principal: parsed.round.principalDue,
        principalMonth: parsed.round.principalMonth,
        outstanding: 0,
      });
    });
    var out = {};
    var balance = 0;
    (periods || []).forEach(function (p) {
      if (closeMonth && p <= closeMonth) {
        out[p] = blankEffect();
        return;
      }
      var financing = 0;
      var debtDelta = 0;
      var equityDelta = 0;
      open.forEach(function (r) {
        if (r.month !== p) return;
        financing += r.net;
        debtDelta += r.debtProceeds;
        equityDelta += r.equityProceeds;
        r.outstanding = cents(r.outstanding + r.debtProceeds);
        balance = cents(balance + r.debtProceeds);
      });
      var interest = 0;
      open.forEach(function (r) {
        if (r.instrument !== "debt" || r.interestStart > p || r.outstanding <= 0) return;
        interest += r.outstanding * r.rate / 12;
      });
      interest = cents(interest);
      open.forEach(function (r) {
        if (!r.principal || r.principalMonth !== p) return;
        var pay = Math.min(r.principal, r.outstanding);
        r.outstanding = cents(r.outstanding - pay);
        balance = cents(balance - pay);
        financing -= pay;
        debtDelta -= pay;
      });
      out[p] = {
        financing: cents(financing),
        interest: interest,
        debtDelta: cents(debtDelta),
        equityDelta: cents(equityDelta),
        debtBalance: balance,
      };
    });
    return out;
  }

  function line(row, keys) {
    if (!row) return 0;
    for (var i = 0; i < keys.length; i++) {
      if (row[keys[i]] != null && row[keys[i]] !== "") return Number(row[keys[i]]) || 0;
    }
    return 0;
  }

  var LINES = {
    collections: ["collections", "cash_collections", "cash_collections_from_invoices"],
    payroll: ["payroll", "payroll_cash_out"],
    commission: ["commission", "commission_cash_out"],
    vendor: ["vendor", "vendor_cash_out", "vendor_cash_out_n30"],
    tax: ["tax", "tax_cash_out"],
    interest: ["interest", "interest_cash_out"],
    other: ["other_operating", "other_operating_cash_out"],
    capex: ["capex"],
    financing: ["financing", "financing_to_maintain_cash_floor"],
    ending: ["ending_cash"],
    beginning: ["beginning_cash"],
    floor: ["cash_floor"],
  };

  function operatingNet(row) {
    return row.collections - row.payroll - row.commission - row.vendor - row.tax - row.interest - row.other - row.capex;
  }

  /**
   * Full-year sources and uses. Closed months keep the actual bridge.
   * Open months roll from the close, with the floor plug removed.
   * Funded months add the confirmed round. Runway uses operating burn and ignores the wire.
   */
  function directWalk(opts) {
    opts = opts || {};
    var periods = opts.periods || [];
    var close = opts.closeMonth || "";
    var actual = opts.actual || {};
    var forecast = opts.forecast || {};
    var floor = opts.floor != null ? Number(opts.floor) : null;
    var fundedFx = effects(opts.rounds || [], periods, close);

    function roll(useRound) {
      var months = [];
      var prevEnd = null;
      periods.forEach(function (p) {
        var closed = !!(close && p <= close);
        var src = closed ? actual[p] : forecast[p];
        var base = {
          period: p,
          closed: closed,
          collections: line(src, LINES.collections),
          payroll: line(src, LINES.payroll),
          commission: line(src, LINES.commission),
          vendor: line(src, LINES.vendor),
          tax: line(src, LINES.tax),
          interest: line(src, LINES.interest),
          other: line(src, LINES.other),
          capex: line(src, LINES.capex),
          financing: 0,
          beginning: null,
          ending: null,
          missing: !src,
        };
        if (floor == null && src && src.cash_floor != null) floor = Number(src.cash_floor);
        if (closed && src && src.ending_cash != null) {
          base.beginning = src.beginning_cash != null ? Number(src.beginning_cash) : prevEnd;
          base.financing = line(src, LINES.financing);
          base.ending = Number(src.ending_cash);
          months.push(base);
          prevEnd = base.ending;
          return;
        }
        var fx = useRound && fundedFx[p] ? fundedFx[p] : blankEffect();
        base.beginning = prevEnd;
        base.interest = cents(base.interest + fx.interest);
        base.financing = cents(fx.financing);
        if (base.beginning == null || !src) {
          months.push(base);
          prevEnd = null;
          return;
        }
        base.ending = cents(base.beginning + operatingNet(base) + base.financing);
        months.push(base);
        prevEnd = base.ending;
      });
      return months;
    }

    var unfunded = roll(false);
    var funded = roll(true);
    var june = null;
    unfunded.forEach(function (m) { if (m.period === close) june = m.ending; });
    var open = unfunded.filter(function (m) { return !m.closed && m.ending != null; });
    var burnSum = 0;
    var burnN = 0;
    open.forEach(function (m) {
      burnSum += -operatingNet(m);
      burnN += 1;
    });
    var burn = burnN ? burnSum / burnN : null;
    var runwayMonths = june != null && burn != null && burn > 1 ? june / burn : null;

    function breach(months) {
      for (var i = 0; i < months.length; i++) {
        var m = months[i];
        if (m.closed || m.ending == null) continue;
        if (floor != null && m.ending < floor) return m.period;
        if (floor == null && m.ending < 0) return m.period;
      }
      return null;
    }

    return {
      unfunded: unfunded,
      funded: funded,
      floor: floor,
      juneCash: june,
      monthlyBurn: burn,
      runwayMonths: runwayMonths,
      breach: breach(unfunded),
      fundedBreach: breach(funded),
    };
  }

  function loadRounds() {
    try {
      var raw = root.localStorage ? root.localStorage.getItem(STORAGE_KEY) : null;
      var parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  function saveRounds(rounds) {
    if (!root.localStorage) return;
    root.localStorage.setItem(STORAGE_KEY, JSON.stringify(rounds || []));
  }

  return {
    STORAGE_KEY: STORAGE_KEY,
    cents: cents,
    normalizeRound: normalizeRound,
    effects: effects,
    directWalk: directWalk,
    loadRounds: loadRounds,
    saveRounds: saveRounds,
  };
});
