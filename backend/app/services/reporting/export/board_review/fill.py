"""Fill the Board Operating Review (version 7) for one close, then run the deck check.

The filler only (1) writes text into named boxes, keeping each box's formatting (a commentary box
gets one paragraph per point, each copied from the box's own paragraph style), (2) replaces chart
data, (3) shows or hides a slide or an unused channel row, and (4) colours a variance figure green
(ahead of plan) or red (behind). It never moves, resizes, regroups or restyles a shape, and it never
searches the deck for words: every write is by slot name.

Commentary: accepted notes from the close come first, then paragraphs built from the figures on the
slide. Each paragraph is kept only if every dollar in it is already in a shape on that slide, and only
while the box has room. The slide title is the slide's message, held to the same rule; if it cannot
meet it, the title falls back to the section name.

usage: python bor7_fill.py deck_in.pptx template.pptx slots.json input.json deck_out.pptx check_out.json
"""
import copy
import datetime as dt
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from lxml import etree

MINUS, WJ, DASH = '−', '⁠', '—'
GREEN, RED, SOFT = RGBColor(0x22, 0xC5, 0x5E), RGBColor(0xEF, 0x44, 0x44), RGBColor(0xB4, 0xC6, 0xD6)
MON = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
MON3 = [m[:3] for m in MON]


# ------------------------------------------------------------------ formats
def D(x):
    return Decimal(repr(float(x)))


def usd(v, sign=False):
    if v is None:
        return DASH
    a = abs(D(v))
    m = (a / Decimal(1000000)).quantize(Decimal('0.01'), ROUND_HALF_UP)
    k = (a / Decimal(1000)).quantize(Decimal('0.1'), ROUND_HALF_UP)
    if m >= 1:
        body = f'${m:,.2f}M'
    elif k >= 1:
        body = f'${k:,.1f}K'
    else:
        body = f'${a.quantize(Decimal("1"), ROUND_HALF_UP):,.0f}'
    if body == '$0':
        return body
    if v < 0:
        return MINUS + body
    return ('+' + body) if sign else body


def pct(r, sign=True):
    if r is None:
        return DASH
    p = (D(r) * 100).quantize(Decimal('0.1'), ROUND_HALF_UP)
    if p == 0:
        return '0.0%'
    if p < 0:
        return f'{MINUS}{abs(p)}%'
    return f'+{p}%' if sign else f'{p}%'


def pabs(r):
    return pct(abs(r), False)


def margin(r):
    return DASH if r is None else f'{(D(r) * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)}%'


def pts(d):
    if d is None:
        return DASH
    p = (D(d) * 100).quantize(Decimal('0.1'), ROUND_HALF_UP)
    if p == 0:
        return '0.0 pts'
    return f'{MINUS}{abs(p)} pts' if p < 0 else f'+{p} pts'


def count(v):
    return DASH if v is None else f'{int(round(v)):,}'


def ratio(a, p):
    if a is None or p is None or p == 0:
        return None
    return (a - p) / abs(p)


def share(a, p):
    if a is None or p is None or p == 0:
        return DASH
    return margin(a / p)


def tone(effect):
    if effect is None:
        return None
    return 'fav' if effect > 1e-9 else ('unf' if effect < -1e-9 else 'neu')


def joined(items):
    items = [i for i in items if i]
    if len(items) <= 1:
        return ''.join(items)
    return ', '.join(items[:-1]) + ' and ' + items[-1]


def cap(s):
    return s[:1].upper() + s[1:]


def nb(s):
    return re.sub(r'([+−])\$', '\\1' + WJ + '$', s)


def chart_amount(s):
    """Amounts drawn inside a chart. No word joiner and no special minus: PowerPoint substitutes another face for those."""
    return s.replace(WJ, '').replace(MINUS, '-').replace('—', '-')


TOKEN = re.compile(r'\$[\d,]+(?:\.\d+)?[KM]?')


def dollars(s):
    return TOKEN.findall(s.replace(WJ, ''))


# ------------------------------------------------------------------ labels from the close date
def labels(close, fy_start, plan):
    y, m = close.year, close.month
    k = (m - fy_start) % 12 + 1
    fy_end = y if (fy_start == 1 or m < fy_start) else y + 1
    fy = str(y) if fy_start == 1 else f'FY{fy_end}'
    fy_ly = str(y - 1) if fy_start == 1 else f'FY{fy_end - 1}'

    def span(first, n):
        last = (first + n - 2) % 12 + 1
        return MON3[first - 1] if n == 1 else f'{MON3[first - 1]}–{MON3[last - 1]}'

    pm, py = (m - 2) % 12 + 1, y if m > 1 else y - 1
    end_m = (fy_start - 2) % 12 + 1
    rest = span(m % 12 + 1, 12 - k) if k < 12 else None
    q = (k - 1) // 3 + 1
    inq = (k - 1) % 3 + 1
    # the periods a reader expects at this close: the month, the quarter (or quarter to date) and the year to date,
    # leaving out any that would repeat another (January has only the month; February's quarter is its year to date)
    periods = [('month', MON[m - 1], list(range(k, k + 1)))]
    if inq > 1 and inq != k:
        periods.append(('quarter', f'Q{q}' if inq == 3 else f'Q{q} to date', list(range(k - inq + 1, k + 1))))
    ytd_name = {3: 'Q1', 6: 'H1', 12: 'Full year'}.get(k)
    if k > 1:
        periods.append(('ytd', ytd_name or f'{span(fy_start, k)}', list(range(1, k + 1))))
    yn = {3: 'Q1', 6: 'H1', 12: 'FY'}.get(k)
    ymonths = []
    yy, mm = y, m
    for _ in range(k):
        ymonths.insert(0, f'{yy}-{mm:02d}')
        mm -= 1
        if mm == 0:
            yy, mm = yy - 1, 12
    return {
        'periods': periods, 'fiscal_months': ymonths, 'prior_quarter': f'Q{q - 1}' if q > 1 else f'Q4 {fy_ly}',
        'rest_name': ('H2' if k == 6 else rest) if rest else None,
        'cover': (f'Q{q} and {"first half" if k == 6 else "full year"} {y} · {MON[m - 1]} close' if k in (6, 12) else
                  f'Q{q} {y} · {MON[m - 1]} close' if k in (3, 9) else f'{MON[m - 1]} {y} close · Q{q} {y}'),
        'month': f'{MON[m - 1]} {y}', 'month_name': MON[m - 1], 'month_short': f'{MON3[m - 1]} {y}', 'prev_short': f'{MON3[pm - 1]} {py}',
        'fy_end_short': f'{MON3[end_m - 1]} {fy_end}', 'fy_end_mon': MON3[end_m - 1],
        'quarter': f'Q{q} {y}' if fy_start == 1 else f'Q{q} FY{fy_end}',
        'fy': fy, 'fy_name': f'FY {fy_end}' if fy_start != 1 else f'FY {y}', 'months_closed': k,
        'ytd': f'{yn} {fy}' if yn else f'{fy} YTD · {span(fy_start, k)}', 'ytd_short': f'{yn} {fy}' if yn else f'{fy} YTD',
        'ly_month': f'{MON[m - 1]} {y - 1}', 'ly_ytd': f'{yn} {fy_ly}' if yn else f'{fy_ly} YTD', 'ly_year': fy_ly,
        'closed_span': span(fy_start, k), 'rest_span': rest,
        'prev_name': MON[pm - 1], 'next_name': MON[m % 12], 'next_short': MON3[m % 12], 'fy_end_name': MON[end_m - 1],
        'h1': f'{span(fy_start, k)} actual', 'h2': f'{rest} outlook' if rest else 'No months open',
        'plan': plan, 'Plan': cap(plan), 'vs': f'vs {plan}',
    }


# ------------------------------------------------------------------ deck access
class Deck:
    def __init__(self, path, reg):
        self.prs = Presentation(path)
        self.reg = {s['name']: s for s in reg['slots']}
        self.sections = {s['key']: s['title'] for s in reg['slides']}
        self.shape, self.slide = {}, {}
        for sl in self.prs.slides:
            for sh in sl.shapes:
                self.shape[sh.name] = sh
            for sh in sl.shapes:
                if sh.name.endswith('.title') and sh.name[:-6] in self.sections:
                    self.slide[sh.name[:-6]] = sl
        self.written = {}

    def text(self, name, s, value=None, kind=None, tone_=None):
        assert name in self.reg, f'not a slot: {name}'
        tf = self.shape[name].text_frame
        p0 = tf.paragraphs[0]
        for p in tf.paragraphs[1:]:
            p._p.getparent().remove(p._p)
        runs = p0.runs
        for r in runs[1:]:
            r._r.getparent().remove(r._r)
        runs[0].text = s
        if self.reg[name]['tone']:
            runs[0].font.color.rgb = {'fav': GREEN, 'unf': RED}.get(tone_, SOFT)
        self.written[name] = {'text': s, 'value': value, 'kind': kind or self.reg[name]['kind']}

    def paras(self, name, items):
        """One paragraph per (lead, body), each a copy of the box's first paragraph (bold lead run, body run)."""
        assert self.reg[name]['kind'] == 'commentary'
        body = self.shape[name].text_frame._txBody
        ps = body.findall(qn('a:p'))
        proto = copy.deepcopy(ps[0])
        for p in ps:
            body.remove(p)
        for lead, text_ in (items or [('', '')]):
            p = copy.deepcopy(proto)
            rs = p.findall(qn('a:r'))
            rs[0].find(qn('a:t')).text = lead
            rs[1].find(qn('a:t')).text = text_
            body.append(p)
        self.written[name] = {'text': '\n'.join(a + b for a, b in (items or [('', '')])), 'value': None, 'kind': 'commentary'}

    def chart(self, name, cats, series):
        assert name in self.reg, f'not a slot: {name}'
        cd = CategoryChartData()
        cd.categories = cats
        for nm, vals in series:
            cd.add_series(nm, vals)
        ch = self.shape[name].chart
        pa = ch._chartSpace.find('.//' + qn('c:plotArea'))
        sc = pa.find(qn('c:scatterChart'))      # waterfall connectors: written by connectors(), not from the chart data
        if sc is not None:
            pa.remove(sc)
        ch.replace_data(cd)
        if sc is not None:
            pa.find(qn('c:barChart')).addnext(sc)
        self.written[name] = {'text': None, 'categories': cats, 'series': series, 'kind': 'chart'}

    def waterfall(self, name, cats, start, deltas, end, texts):
        """A bridge: boxes from start through each delta to end, the amount in bold above each box, connectors across the gaps.
        Both value axes get the same scale (boxes on the hidden one, connectors and labels on the visible one), from 0 to a round
        number above the tallest column."""
        series, levels = waterfall_series(start, deltas, end)
        self.chart(name, cats, series)
        self.waterfall_labels(name, texts)
        top = max(sum(vals[i] or 0 for _, vals in series) for i in range(len(cats)))
        mx, step = nice_scale(top)
        va = box_axis(self.shape[name].chart)
        va.minimum_scale, va.maximum_scale = 0, mx
        va.major_unit = step
        dec = 0 if step >= 1 else (1 if step * 10 >= 1 - 1e-9 and abs(step * 10 - round(step * 10)) < 1e-9 else 2)
        va.tick_labels.number_format = '"$"#,##0' + ('.' + '0' * dec if dec else '') + '"M"'   # $0.5M steps need a decimal
        va.tick_labels.number_format_is_linked = False
        self.connectors(name, levels, mx)
        self.written[name]['scale'] = (0, mx, step)

    def connectors(self, name, levels, top=1.0):
        """One line per gap, from the right edge of a box to the left edge of the next, at the level where the first ends.
        Box k (from 1) is centred at x = k on the connectors' hidden horizontal axis (0.5 to boxes + 0.5); a box is
        1 / (1 + gap width) of its slot wide. levels=None blanks them. The hidden vertical axis takes the visible one's scale."""
        ch = self.shape[name].chart
        pa = ch._chartSpace.find('.//' + qn('c:plotArea'))
        sc = pa.find(qn('c:scatterChart'))
        style = sc.find(qn('c:scatterStyle'))
        if style is not None:
            style.set('val', 'line')
        n = len(list(ch.plots[0].categories))
        half = 0.5 / (1 + bar_plot(ch).gap_width / 100)
        id_x, id_y = [a.get('val') for a in sc.findall(qn('c:axId'))]
        for ax in pa.findall(qn('c:valAx')):
            own = ax.find(qn('c:axId')).get('val')
            if own in (id_x, id_y):
                scl = ax.find(qn('c:scaling'))
                lo, hi = (0.5, n + 0.5) if own == id_x else (0.0, top)
                scl.find(qn('c:max')).set('val', repr(float(hi)))
                scl.find(qn('c:min')).set('val', repr(float(lo)))
        pts = []
        for k, ser in enumerate(sc.findall(qn('c:ser'))):
            lv = levels[k] if levels else None
            xy = ([k + 1 + half, k + 2 - half], [lv, lv]) if lv is not None else ([], [])
            for tag, vals in zip(('c:xVal', 'c:yVal'), xy):
                lit = ser.find(qn(tag)).find(qn('c:numLit'))
                for p in lit.findall(qn('c:pt')):
                    lit.remove(p)
                for i, v in enumerate(vals):
                    pt = etree.SubElement(lit, qn('c:pt'))
                    pt.set('idx', str(i))
                    etree.SubElement(pt, qn('c:v')).text = repr(float(v))
            pts.append(xy)
            ln = ser.find(qn('c:spPr'))
            ln = None if ln is None else ln.find(qn('a:ln'))
            if ln is not None:
                ln.set('w', '6350')
        self.written[name]['connectors'] = pts

    def waterfall_labels(self, name, texts):
        from pptx.util import Pt
        ser = bar_plot(self.shape[name].chart).series[4]
        clean = [chart_amount(t) for t in texts]
        for i, t in enumerate(clean):
            run = ser.points[i].data_label.text_frame.paragraphs[0].runs[0]
            run.text = t
            run.font.name = 'Calibri'
            run.font.size = Pt(9)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            rpr = run._r.find(qn('a:rPr'))
            if rpr is not None:
                rpr.set('sz', '900')
                for tag in ('a:latin', 'a:ea', 'a:cs'):
                    el = rpr.find(qn(tag))
                    if el is None:
                        el = etree.SubElement(rpr, qn(tag))
                    el.set('typeface', 'Calibri')
        self.written[name]['labels'] = clean

    def show_slide(self, key, on):
        el = self.slide[key]._element
        if on:
            el.attrib.pop('show', None)
        else:
            el.set('show', '0')

    def show_shape(self, name, on):
        c = self.shape[name]._element.find('.//' + qn('p:cNvPr'))
        if on:
            c.attrib.pop('hidden', None)
        else:
            c.set('hidden', '1')

    def blank_slide(self, key):
        for name, s in self.reg.items():
            if s['slide'] != key or name in self.written:
                continue
            if s['kind'] == 'chart':
                ch = self.shape[name].chart
                cats = [str(c) for c in ch.plots[0].categories]
                self.chart(name, cats, [(sr.name, [None] * len(cats)) for p_ in cat_plots(ch) for sr in p_.series])
                if len(bar_plot(ch).series) > 4 and bar_plot(ch).series[4].name == 'Label':
                    self.waterfall_labels(name, [''] * len(cats))
                if ch._chartSpace.find('.//' + qn('c:scatterChart')) is not None:
                    self.connectors(name, None)
            elif s['kind'] == 'commentary':
                self.paras(name, [])
            else:
                self.text(name, DASH)


def nice_scale(top):
    """A round axis maximum above the top value, with five to eight gridlines."""
    import math
    if top <= 0:
        return 1.0, 0.2
    raw = top / 6
    mag = 10 ** math.floor(math.log10(raw))
    step = next(f * mag for f in (1, 2, 2.5, 5, 10) if f * mag >= raw)
    return math.ceil(top / step - 1e-9) * step, step


def bar_plot(chart):
    return [p for p in chart.plots if type(p).__name__ == 'BarPlot'][0]


def box_axis(chart):
    """The visible value axis the boxes are drawn on (python-pptx's chart.value_axis picks the second value axis when a chart
    has several, which here is the connectors' hidden one)."""
    from pptx.chart.axis import ValueAxis
    pa = chart._chartSpace.find('.//' + qn('c:plotArea'))
    vid = pa.find(qn('c:barChart')).findall(qn('c:axId'))[1].get('val')
    return ValueAxis([a for a in pa.findall(qn('c:valAx')) if a.find(qn('c:axId')).get('val') == vid][0])


def cat_plots(chart):
    """The plots that carry the chart data (everything but a waterfall's connector lines)."""
    return [p for p in chart.plots if type(p).__name__ != 'XyPlot']


def chart_tokens(chart):
    """Text a reader sees in a chart: categories, series names, and labelled values (formatted as the chart shows them)."""
    out = []
    cs = chart._chartSpace
    for sc in cs.iter(qn('c:strCache')):
        for v in sc.iter(qn('c:v')):
            out.append(v.text or '')
    for dlbl in cs.iter(qn('c:dLbl')):
        out.append(''.join(t.text or '' for t in dlbl.iter(qn('a:t'))))
    for ser in cs.iter(qn('c:ser')):
        dl = ser.find(qn('c:dLbls'))
        sv = dl.find(qn('c:showVal')) if dl is not None else None
        if sv is None or sv.get('val') not in ('1', 'true'):
            continue
        nf = dl.find(qn('c:numFmt'))
        for v in ser.find(qn('c:val')).iter(qn('c:v')):
            x = float(v.text)
            if nf is not None and '"M"' in nf.get('formatCode', ''):
                out.append(f'${abs(x):,.2f}M')
    return out


def visible_text(sl, exclude):
    out = []
    for sh in sl.shapes:
        c = sh._element.find('.//' + qn('p:cNvPr'))
        if (c is not None and c.get('hidden') == '1') or sh.name in exclude:
            continue
        if sh.has_text_frame:
            out.append(sh.text_frame.text)
        if getattr(sh, 'has_chart', False) and sh.has_chart:
            out.extend(chart_tokens(sh.chart))
    return '\n'.join(out)


def box_fit(shape, limit):
    """Estimate how much a commentary box holds: Calibri averages a little under half an em per character;
    each paragraph adds its spacing after."""
    p = shape.text_frame.paragraphs[0]
    size = (p.runs[0].font.size or 1400 * 127).pt if p.runs else 11
    width_in, height_pt = shape.width / 914400, shape.height / 12700
    per_line = max(10, int(width_in * 72 / (size * 0.44)))
    line_h = size * 1.2

    def height(t):
        return -(-len(t.replace(WJ, '')) // per_line) * line_h + 7
    return {'height': height, 'capacity': height_pt + 7, 'limit': limit}


def waterfall_series(start, deltas, end):
    """Series for the standard bridge, in $ millions: Base (invisible), Increase, Decrease, Total, Label (an invisible sliver on
    top of each column, a tenth of the tallest column, that carries the amount above the box). Also returns the connector
    levels: where each box ends and the next begins."""
    base, up, down, total = [0.0], [0.0], [0.0], [start]
    run = start
    levels = [start]
    for d in deltas:
        if d >= 0:
            base.append(run); up.append(d); down.append(0.0); total.append(0.0)
        else:
            base.append(run + d); up.append(0.0); down.append(-d); total.append(0.0)
        run += d
        levels.append(run)
    base.append(0.0); up.append(0.0); down.append(0.0); total.append(end)
    n = len(base)
    m = 1e6
    top = max(b + u + d_ + t for b, u, d_, t in zip(base, up, down, total))
    series = [('Base', [v / m for v in base]), ('Increase', [v / m for v in up]), ('Decrease', [v / m for v in down]),
              ('Total', [v / m for v in total]), ('Label', [top * 0.1 / m] * n)]
    return series, [v / m for v in levels[:n - 1]]


# ------------------------------------------------------------------ fill
def fill(deck, inp):
    close = dt.date.fromisoformat(inp['close'])
    lab = labels(close, inp.get('fiscal_year_start_month', 1), inp.get('plan_label', 'budget'))
    plan, Plan, vs = lab['plan'], lab['Plan'], lab['vs']
    draft = inp.get('status', 'draft') != 'approved'
    built, titles, shown = {}, {}, {}
    no_plan = f'No {plan} loaded'
    under = lambda v: 'under' if v < 0 else 'above'

    for key, sec in deck.sections.items():
        if key == 'cover':
            continue
        deck.text(f'{key}.kicker', f'{("APPENDIX" if key in ("cf", "pnlx") else sec.upper())} · {lab["month"].upper()}')
        deck.text(f'{key}.footer', f'{inp["company"]} · Board Operating Review · {lab["month"]}' + (' · Draft' if draft else ''))
    deck.text('cover.period', lab['cover'])
    deck.text('cover.company', inp['company'])
    deck.text('cover.status', 'Draft' if draft else 'Approved')

    def heads(key, tkey, cols):
        for c in cols:
            if c.endswith('plan'):
                deck.text(f'{key}.{tkey}.h.{c}', Plan)
            elif c.endswith('var'):
                deck.text(f'{key}.{tkey}.h.{c}', vs)
            elif c.endswith('share'):
                deck.text(f'{key}.{tkey}.h.{c}', f'% of {plan}')

    def tile(key, m, value_s, value, kind, plan_v, plan_s, var_s, var_v, tone_, loaded=True, no_plan_text=None):
        deck.text(f'{key}.{m}.value', value_s, value, kind)
        if loaded and plan_v is not None:
            deck.text(f'{key}.{m}.plan', f'{Plan} {plan_s}', plan_v, 'label+' + kind)
            deck.text(f'{key}.{m}.var', var_s, var_v, None, tone_)
        else:
            deck.text(f'{key}.{m}.plan', no_plan_text or no_plan)
            deck.text(f'{key}.{m}.var', DASH)

    # ---- the close
    pm = inp['pnl']['month']
    A, P, LY = pm['actual'], pm.get('plan'), pm.get('last_year')
    YA, YP, YLY = inp['pnl']['ytd']['actual'], inp['pnl']['ytd'].get('plan'), inp['pnl']['ytd'].get('last_year')
    for d in (A, P, LY, YA, YP, YLY):
        if d:
            d.setdefault('total_opex', d.get('sm', 0) + d.get('rd', 0) + d.get('ga', 0))
            d['below'] = d['ebitda'] - d['net_income']
    gm = lambda d: d['gross_profit'] / d['revenue'] if d and d.get('revenue') else None
    em = lambda d: d['ebitda'] / d['revenue'] if d and d.get('revenue') else None
    arr = inp.get('arr')
    AA, AP = (dict(arr['actual']), dict(arr['plan']) if arr.get('plan') else None) if arr else (None, None)
    for d in (AA, AP):
        if d:
            d['adds'] = d['new_business'] + d['expansion'] + d['reactivation']
            d['losses'] = d['contraction'] + d['churn']
            d['net_new'] = d['adds'] + d['losses']
            d['grr'] = ((d['beginning'] + d['losses']) / d['beginning']) if d['beginning'] else None
    cash = inp.get('cash')
    CA, CP = (dict(cash['actual']), dict(cash['plan']) if cash.get('plan') else None) if cash else (None, None)
    CASH_LINES = ['collections', 'payroll', 'vendors', 'commissions', 'capex']
    for d in (CA, CP):
        if d:
            d['other'] = d['ending'] - d['beginning'] - sum(d[x] for x in CASH_LINES)
            d['net_change'] = d['ending'] - d['beginning']
    ol = inp.get('outlook')
    FY, FYP = (ol['fy'], ol.get('plan_fy')) if ol else (None, None)
    end_arr, end_arr_p = (AA['ending'] if AA else None), (AP['ending'] if AP else None)
    end_cash, end_cash_p = (CA['ending'] if CA else inp.get('ending_cash')), (CP['ending'] if CP else None)

    # ================================================================ 2 executive dashboard
    key = 'dash'
    ly_arr = (arr or {}).get('last_year_ending')
    ly_cash = (cash or {}).get('last_year_ending')
    measures = [('arr', 'ARR', end_arr, end_arr_p, 'amount', end_arr, end_arr_p, ly_arr, ly_arr),
                ('rev', 'revenue', A['revenue'], P and P['revenue'], 'amount', YA['revenue'], YP and YP['revenue'], LY and LY['revenue'], YLY and YLY['revenue']),
                ('gm', 'gross margin', gm(A), gm(P), 'margin', gm(YA), gm(YP), gm(LY), gm(YLY)),
                ('ebitda', 'EBITDA', A['ebitda'], P and P['ebitda'], 'amount', YA['ebitda'], YP and YP['ebitda'], LY and LY['ebitda'], YLY and YLY['ebitda']),
                ('ni', 'net income', A['net_income'], P and P['net_income'], 'amount', YA['net_income'], YP and YP['net_income'], LY and LY['net_income'], YLY and YLY['net_income']),
                ('cash', 'cash', end_cash, end_cash_p, 'amount', end_cash, end_cash_p, ly_cash, ly_cash)]
    for m, _, a, p, kind, *_ in measures:
        if m == 'ni':
            continue
        if kind == 'margin':
            d = None if p is None else a - p
            tile(key, m, margin(a), a, 'margin', p, margin(p), pts(d), d, tone(d), P is not None)
        else:
            vr = ratio(a, p)
            tile(key, m, usd(a), a, 'amount', p, usd(p), pct(vr), vr, tone(None if p is None or a is None else a - p), p is not None)
    deck.text('dash.mx.g.m', lab['month'])
    deck.text('dash.mx.g.ytd', lab['ytd'])
    heads(key, 'mx', ['m_plan', 'm_var', 'ytd_plan', 'ytd_var'])
    deck.text('dash.mx.h.m_ly', f'vs {lab["ly_month"]}')
    deck.text('dash.mx.h.ytd_ly', f'vs {lab["ly_ytd"]}')
    for m, _, a, p, kind, ya, yp, ly, yly in measures:
        for grp, x, y, z in (('m', a, p, ly), ('ytd', ya, yp, yly)):
            d = None if (x is None or y is None) else x - y
            if kind == 'margin':
                deck.text(f'dash.mx.{m}.{grp}_act', margin(x), x, 'margin')
                deck.text(f'dash.mx.{m}.{grp}_plan', margin(y), y, 'margin')
                deck.text(f'dash.mx.{m}.{grp}_var', pts(d), d, 'pts', tone(d))
                dl = None if z is None else x - z
                deck.text(f'dash.mx.{m}.{grp}_ly', pts(dl), dl, 'pts', tone(dl))
            else:
                deck.text(f'dash.mx.{m}.{grp}_act', usd(x), x, 'amount')
                deck.text(f'dash.mx.{m}.{grp}_plan', usd(y), y, 'amount')
                deck.text(f'dash.mx.{m}.{grp}_var', usd(d, True), d, 'amount', tone(d))
                r = ratio(x, z)
                deck.text(f'dash.mx.{m}.{grp}_ly', pct(r), r, 'pct', tone(r))
    if P:
        missed, ahead = [], []
        for m, name, a, p, kind, *_ in measures:
            if m == 'ni' or a is None or p is None:
                continue
            if kind == 'margin':
                (missed if (a - p) * 100 < -0.5 else ahead if (a - p) * 100 > 0.5 else []).append((name, pts(a - p)))
            else:
                r = ratio(a, p)
                if r is None:
                    continue
                (missed if r < -0.01 else ahead if r > 0.01 else []).append((name, usd(abs(a - p))))
        t = []
        if missed:
            t.append(f'{joined([n for n, _ in missed])} under {plan}')
        if ahead:
            t.append(joined([f'{n} {g} ahead' for n, g in ahead]))
        titles[key] = cap('; '.join(t)) if t else f'Headline measures in line with {plan}'
        rv, ev, nv = A['revenue'] - P['revenue'], A['ebitda'] - P['ebitda'], A['net_income'] - P['net_income']
        ps = []
        body = f' Revenue {"grew" if LY and A["revenue"] >= LY["revenue"] else "fell"} {pabs(ratio(A["revenue"], LY["revenue"]))} on {lab["ly_month"]}' if LY else ''
        if YP:
            yr = YA['revenue'] - YP['revenue']
            yr_share = ratio(YA['revenue'], YP['revenue'])
            body += (f'; year to date it is {usd(YA["revenue"])}'
                     + (f', {pabs(yr_share)} {under(yr)} {plan}' if yr_share is not None else '')
                     + (f' and {pabs(ratio(YA["revenue"], YLY["revenue"]))} {"above" if YA["revenue"] >= YLY["revenue"] else "below"} {lab["ly_year"]}' if YLY else ''))
        rv_share = ratio(A['revenue'], P['revenue'])
        ps.append((f'Revenue {usd(A["revenue"])}' + (f', {pabs(rv_share)} {under(rv)} {plan}' if rv_share is not None else '') + '.', body + '.' if body else ''))
        body = f' The month was {usd(abs(ev))} {under(ev)} {plan}'
        if YP:
            ye = YA['ebitda'] - YP['ebitda']
            body += (f'; year to date EBITDA is {usd(YA["ebitda"])}, {usd(abs(ye))} {under(ye)} {plan}'
                     + (f' and {pabs(ratio(YA["ebitda"], YLY["ebitda"]))} {"above" if YA["ebitda"] >= YLY["ebitda"] else "below"} {lab["ly_year"]}' if YLY else ''))
        ps.append((f'EBITDA {usd(A["ebitda"])} against {usd(P["ebitda"])} {plan}.', body + '.'))
        if ev * nv > 0 and abs(ev) < abs(nv):
            body = f' EBITDA accounts for {usd(abs(ev))} of the gap; the rest sits below EBITDA, in D&A, interest and tax.'
        else:
            body = f' EBITDA was {usd(abs(ev))} {under(ev)} {plan}.'
        ps.append((f'Net income {usd(A["net_income"])}, {usd(abs(nv))} {under(nv)} {plan}.', body))
        if end_arr is not None and end_arr_p:
            av = end_arr - end_arr_p
            ps.append((f'Ending ARR {usd(end_arr)}, {pabs(av / end_arr_p)} {under(av)} {plan}.',
                       f' The gap to {plan} at the end of {lab["month_name"]} is {usd(abs(av))}.'))
        if end_cash is not None and end_cash_p is not None:
            cv = end_cash - end_cash_p
            only = [n for n, _ in ahead] == ['cash']
            ps.append((f'Ending cash {usd(end_cash)}, {usd(abs(cv))} {"ahead of" if cv >= 0 else "behind"} {plan}.',
                       f' Cash is the one headline measure ahead of {plan}.' if only else ''))
        g_a, g_p = gm(A), gm(P)
        parts = ([f'year to date {margin(gm(YA))} against {margin(gm(YP))}'] if YP else []) + ([f'{pts(g_a - gm(LY))} on {lab["ly_month"]}'] if LY else [])
        ps.append((f'Gross margin {margin(g_a)} against {margin(g_p)}.', (' ' + cap('; '.join(parts)) + '.') if parts else ''))
        built[key] = ps
    shown[key] = True

    # ================================================================ 3 ARR: budget-to-actual net new, by period, customers behind the month
    key = 'arr'
    PER = {p[0]: p for p in lab['periods']}
    G3 = dict(zip(['g1', 'g2', 'g3'], [p[0] for p in lab['periods']] + [None, None, None]))   # groups fill left to right
    hist = {h['month']: h for h in inp.get('history', [])}
    mkeys = lab['fiscal_months']

    def month_data(i, part):
        """Fiscal month i (1-based) of one part ('arr', 'gtm', 'pipeline'): the close month from the close, earlier months from history."""
        mk = mkeys[i - 1]
        if i == lab['months_closed']:
            return {'arr': {'actual': AA, 'plan': AP} if AA else None,
                    'gtm': inp.get('gtm') and {'channels': inp['gtm']['channels'], 'funnel': inp['gtm']['funnel']},
                    'pipeline': inp.get('pipeline')}[part]
        return hist.get(mk, {}).get(part)

    def arr_period(months):
        ms = [month_data(i, 'arr') for i in months]
        if not ms or any(x is None or not x.get('plan') for x in ms):
            return None
        out = {}
        for side in ('actual', 'plan'):
            d = {c: sum(x[side][c] for x in ms) for c in ('new_business', 'expansion', 'reactivation', 'contraction', 'churn')}
            d['loss'] = d['contraction'] + d['churn']
            d['nn'] = d['new_business'] + d['expansion'] + d['reactivation'] + d['loss']
            out[side] = d
        return out
    if AA:
        for g, pid in G3.items():
            p = PER.get(pid) if pid else None
            agg = arr_period(p[2]) if p else None
            deck.text(f'arr.p.{g}', p[1] if (p and agg) else '')
            deck.text(f'arr.p.h.{g}_act', 'Actual' if (p and agg) else '')
            deck.text(f'arr.p.h.{g}_pct', f'% of {plan}' if (p and agg) else '')
            for rk, f in (('nb', 'new_business'), ('ex', 'expansion'), ('loss', 'loss'), ('nn', 'nn')):
                if not agg:
                    deck.text(f'arr.p.{rk}.{g}_act', '', None, 'blank')
                    deck.text(f'arr.p.{rk}.{g}_pct', '', None, 'blank')
                    continue
                a, pv = agg['actual'][f] + (agg['actual']['reactivation'] if f == 'expansion' else 0), agg['plan'][f] + (agg['plan']['reactivation'] if f == 'expansion' else 0)
                deck.text(f'arr.p.{rk}.{g}_act', usd(abs(a) if rk == 'loss' else a), abs(a) if rk == 'loss' else a)
                deck.text(f'arr.p.{rk}.{g}_pct', share(a, pv), (a / pv) if pv else None, 'margin' if pv else 'blank')
            deck.show_shape(f'arr.p.{g}.rule', bool(p and agg))
        deck.text('arr.bridge.label', f'NET NEW ARR · {plan.upper()} TO ACTUAL · {lab["month_name"].upper()}')
        if AP:
            ex_a, ex_p = AA['expansion'] + AA['reactivation'], AP['expansion'] + AP['reactivation']
            gnb, gex, gls = AA['new_business'] - AP['new_business'], ex_a - ex_p, AA['losses'] - AP['losses']
            deck.waterfall('arr.bridge', [Plan, 'New business', 'Expansion and reactivation', 'Churn and contraction', 'Actual'],
                           AP['net_new'], [gnb, gex, gls], AA['net_new'],
                           [usd(AP['net_new']), usd(gnb, True), usd(gex, True), usd(gls, True), usd(AA['net_new'])])
            deck.text('arr.p.note', nb(f'Ending ARR {usd(AA["ending"])} against {usd(AP["ending"])} {plan}, {usd(AA["ending"] - AP["ending"], True)}. '
                                       f'Gross retention {margin(AA["grr"])} against {margin(AP["grr"])}.'))
        else:
            deck.chart('arr.bridge', [Plan, 'New business', 'Expansion and reactivation', 'Churn and contraction', 'Actual'],
                       [(n_, [None] * 5) for n_ in ('Base', 'Increase', 'Decrease', 'Total', 'Label')])
            deck.waterfall_labels('arr.bridge', [''] * 5)
            deck.connectors('arr.bridge', None)
            deck.text('arr.p.note', f'Ending ARR {usd(AA["ending"])}.')
        # customers behind the month
        cu = inp.get('customers') or {}
        top = lambda k_, n_: sorted(cu.get(k_, []), key=lambda c: -abs(c['arr']))[:n_]
        nxt = lab['next_name']
        deck.text('arr.c.h.what', lab['month_name'])
        kinds = (('new_business', 'New customer'), ('expansion', 'Expansion'), ('reactivation', 'Reactivated'),
                 ('contraction', 'Contracted'), ('churn', 'Churned'), ('closed_won', 'Closed won'),
                 ('slipped', f'Slipped to {nxt}'))
        ranked = []
        for key_, label in kinds:
            for c in sorted(cu.get(key_, []), key=lambda c: -abs(c['arr'])):
                ranked.append((c, label, usd(c['arr'], True) if key_ in ('new_business', 'expansion', 'reactivation', 'closed_won') else usd(c['arr'])))
        picks = ranked[:9]
        for n_ in range(1, 10):
            on = n_ <= len(picks)
            deck.show_shape(f'arr.c.c{n_}.rule', on)
            if on:
                c, what, amt = picks[n_ - 1]
                deck.text(f'arr.c.c{n_}.label', c['name'])
                deck.text(f'arr.c.c{n_}.what', what)
                deck.text(f'arr.c.c{n_}.arr', amt, c['arr'])
            else:
                for col in ('label', 'what', 'arr'):
                    deck.text(f'arr.c.c{n_}.{col}', '', None, 'blank')
        if AP:
            nn_share = AA['net_new'] / AP['net_new'] if AP['net_new'] else None
            adds_short = gnb < 0 or gex < 0
            bigger = 'new business' if abs(gnb) >= abs(gex) else 'expansion'
            if gls > 0 and adds_short and AA['net_new'] < AP['net_new']:
                titles[key] = f'Net new ARR {share(AA["net_new"], AP["net_new"])} of {plan}; low churn offset part of a {bigger} miss'
            else:
                titles[key] = f'Net new ARR {usd(AA["net_new"])}, {share(AA["net_new"], AP["net_new"])} of {plan}'
            ps = []
            drv = []
            if gnb < 0:
                drv.append(f'new business ({usd(-gnb)} short)')
            if gex < 0:
                drv.append(f'expansion ({usd(-gex)} short)')
            body = (f' {cap(joined(drv))} drove the gap' if drv else ' Adds came in at or above plan')
            if gls > 0:
                part = 'more than half' if gls > 0.5 * (max(0, -gnb) + max(0, -gex)) else 'part'
                body += f'; churn and contraction {usd(gls)} below {plan} recovered {part} of it.' if drv else f'; churn and contraction ran {usd(gls)} below {plan}.'
            else:
                body += f'; churn and contraction ran {usd(-gls)} above {plan}.'
            ps.append((f'Net new ARR {usd(AA["net_new"])}, {share(AA["net_new"], AP["net_new"])} of {plan}.', body))
            yp, qp = PER.get('ytd'), PER.get('quarter')
            ya_, qa_ = (arr_period(yp[2]) if yp else None), (arr_period(qp[2]) if qp else None)
            if ya_:
                plan_nn = ya_['plan']['nn']
                s_y = ya_['actual']['nn'] / plan_nn if plan_nn else None
                body = ''
                if qa_:
                    q_nn = qa_['plan']['nn']
                    s_q = qa_['actual']['nn'] / q_nn if q_nn else None
                    body = f' {qp[1]}: {usd(qa_["actual"]["nn"])}, {share(qa_["actual"]["nn"], qa_["plan"]["nn"])}'
                    body += ('; the share has fallen each period.' if (nn_share is not None and s_q is not None and s_y is not None and nn_share < s_q < s_y) else '.')
                ps.append((f'{yp[1]} net new ARR {usd(ya_["actual"]["nn"])}, {share(ya_["actual"]["nn"], ya_["plan"]["nn"])} of {plan}.', body))
            nw = top('new_business', 3)
            if nw:
                ps.append((f'{len(cu.get("new_business", []))} new customers in {lab["month_name"]}.',
                           ' ' + cap(joined([f'{c["name"]} ({usd(c["arr"])})' for c in nw])) + (' were the largest.' if len(nw) > 1 else ' was the only one.')))
            won = top('closed_won', 3)
            if won:
                ps.append((f'{len(cu.get("closed_won", []))} customers closed won in {lab["month_name"]}.',
                           ' ' + cap(joined([f'{c["name"]} ({usd(c["arr"])})' for c in won])) + '.'))
            sp = top('slipped', 2)
            if sp:
                ps.append((f'Slipped to {nxt}.', ' ' + cap(joined([f'{c["name"]} ({usd(c["arr"])})' for c in sp])) + f' moved out of {lab["month_name"]}.'))
            lo = top('churn', 1) + top('contraction', 1)
            if lo:
                parts = [f'{c["name"]} {"churned" if c in cu.get("churn", []) else "contracted"} ({usd(-c["arr"])})' for c in lo]
                ps.append(('Retention held.' if AA['grr'] >= AP['grr'] else 'Retention slipped.',
                           f' {cap(joined(parts))}; gross retention was {margin(AA["grr"])} against {margin(AP["grr"])}.'))
            built[key] = ps
    shown[key] = bool(AA)

    # ================================================================ 4 P&L: by period, the rest of the year, takeaways
    key = 'pnl'
    QA_ = (inp['pnl'].get('quarter') or {}).get('actual')
    QP_ = (inp['pnl'].get('quarter') or {}).get('prior')
    for d in (QA_, QP_):
        if d:
            d.setdefault('total_opex', d.get('sm', 0) + d.get('rd', 0) + d.get('ga', 0))
    ROWS4 = [('rev', 'revenue'), ('gm', gm), ('ebitda', 'ebitda'), ('em', em), ('ni', 'net_income')]
    val = lambda d, f: (f(d) if callable(f) else d[f]) if d else None
    has_q = 'quarter' in PER and QA_ is not None
    has_y = 'ytd' in PER
    deck.text('pnl.p.g1', lab['month_name'])
    deck.text('pnl.p.g2', PER['quarter'][1] if has_q else '')
    deck.text('pnl.p.g3', PER['ytd'][1] if has_y else '')
    deck.show_shape('pnl.p.g2.rule', has_q)
    deck.show_shape('pnl.p.g3.rule', has_y)
    deck.text('pnl.p.h.g1_cmp', vs)
    deck.text('pnl.p.h.g2_act', 'Actual' if has_q else '')
    deck.text('pnl.p.h.g3_act', 'Actual' if has_y else '')
    deck.text('pnl.p.h.g2_cmp', f'vs {lab["prior_quarter"]}' if has_q else '')
    deck.text('pnl.p.h.g3_cmp', vs if has_y else '')
    deck.text('pnl.p.h.g3_ly', f'vs {lab["ly_ytd"]}' if has_y else '')
    for r, f in ROWS4:
        mg = callable(f)
        a, p = val(A, f), val(P, f)
        d = None if p is None else a - p
        deck.text(f'pnl.p.{r}.g1_act', margin(a) if mg else usd(a), a, 'margin' if mg else 'amount')
        deck.text(f'pnl.p.{r}.g1_cmp', pts(d) if mg else usd(d, True), d, 'pts' if mg else 'amount', tone(d))
        if has_q:
            a, p = val(QA_, f), val(QP_, f)
            d = (a - p) if mg else ratio(a, p)
            deck.text(f'pnl.p.{r}.g2_act', margin(a) if mg else usd(a), a, 'margin' if mg else 'amount')
            deck.text(f'pnl.p.{r}.g2_cmp', pts(d) if mg else pct(d), d, 'pts' if mg else 'pct', tone(d))
        else:
            deck.text(f'pnl.p.{r}.g2_act', '', None, 'blank')
            deck.text(f'pnl.p.{r}.g2_cmp', '', None, 'blank')
        if has_y:
            a, p, l = val(YA, f), val(YP, f), val(YLY, f)
            d = None if p is None else a - p
            dl = None if l is None else ((a - l) if mg else ratio(a, l))
            deck.text(f'pnl.p.{r}.g3_act', margin(a) if mg else usd(a), a, 'margin' if mg else 'amount')
            deck.text(f'pnl.p.{r}.g3_cmp', pts(d) if mg else usd(d, True), d, 'pts' if mg else 'amount', tone(d))
            deck.text(f'pnl.p.{r}.g3_ly', pts(dl) if mg else pct(dl), dl, 'pts' if mg else 'pct', tone(dl))
        else:
            for c in ('g3_act', 'g3_cmp', 'g3_ly'):
                deck.text(f'pnl.p.{r}.{c}', '', None, 'blank')
    # the rest of the year
    k_ = lab['months_closed']
    n_open = 12 - k_
    ytd_lbl = PER['ytd'][1] if has_y else lab['month_name']
    rest_lbl = lab['rest_name'] or ''
    ry = {}
    for m_, f in (('rev', 'revenue'), ('ebitda', 'ebitda')):
        fy_o = FY and FY.get(f)
        fy_p = FYP and FYP.get(f)
        h1, h1p = YA[f], YP and YP.get(f)
        h2, h2p = (fy_o - h1) if fy_o is not None else None, (fy_p - h1p) if (fy_p is not None and h1p is not None) else None
        ry[m_] = (h1, h1p, h2, h2p, fy_o, fy_p)
        deck.chart(f'pnl.{m_}.ry', [f'{ytd_lbl} actual', f'{rest_lbl} outlook' if n_open else 'No months open', f'{lab["fy_name"]} outlook'],
                   [('Actual and outlook', [h1 / 1e6, h2 / 1e6 if h2 is not None else None, fy_o / 1e6 if fy_o is not None else None]),
                    (Plan, [h1p / 1e6 if h1p is not None else None, h2p / 1e6 if h2p is not None else None, fy_p / 1e6 if fy_p is not None else None])])
        parts = []
        if h1p is not None:
            parts.append(f'{ytd_lbl} {usd(h1 - h1p, True)}')
        if h2 is not None and h2p is not None and n_open:
            parts.append(f'{rest_lbl} {usd(h2 - h2p, True)}')
        if fy_o is not None and fy_p is not None:
            parts.append(f'Full year {usd(fy_o - fy_p, True)}')
        deck.text(f'pnl.{m_}.ry.note', nb(' · '.join(parts) + f' against {plan}') if parts else '')
        deck.text(f'pnl.{m_}.ry.label', f'{"REVENUE" if m_ == "rev" else "EBITDA"} · THE REST OF THE YEAR')
    if P:
        h1, h1p, h2, h2p, fy_o, fy_p = ry['ebitda']
        if h1p is not None and h2 is not None and h2p is not None and n_open:
            g1_, g2_ = h1 - h1p, h2 - h2p
            titles[key] = (f'{ytd_lbl} EBITDA {usd(abs(g1_))} {"under" if g1_ < 0 else "over"} {plan}; the outlook '
                           + (f'adds {usd(-g2_)} more in {rest_lbl}' if (g2_ < 0 and g1_ < 0) else f'{"recovers" if g2_ > 0 else "misses by"} {usd(abs(g2_))} in {rest_lbl}'))
        else:
            ev = A['ebitda'] - P['ebitda']
            titles[key] = f'EBITDA {usd(A["ebitda"])}, {usd(abs(ev))} {"under" if ev < 0 else "over"} {plan}'
        rv = A['revenue'] - P['revenue']
        yoy = ratio(A['revenue'], LY['revenue']) if LY else None
        ps = []
        if yoy is not None:
            ps.append((f'Revenue {usd(A["revenue"])}, {"up" if yoy >= 0 else "down"} {pabs(yoy)} on {lab["ly_month"]}.',
                       f' The business {"grew" if yoy >= 0 else "shrank"} on last year, but {lab["month_name"]} came in {usd(abs(rv))}'
                       + (f', {pabs(rv / P["revenue"])}, {under(rv)} {plan}.' if P.get('revenue') else '.')))
        if has_q:
            qg, qe = ratio(QA_['revenue'], QP_['revenue']), ratio(QA_['ebitda'], QP_['ebitda'])
            ps.append((f'{PER["quarter"][1]} revenue {usd(QA_["revenue"])}, {"up" if qg >= 0 else "down"} {pabs(qg)} on {lab["prior_quarter"]}.',
                       f' EBITDA was {usd(QA_["ebitda"])}, {"up" if qe >= 0 else "down"} {pabs(qe)}; the quarter\'s EBITDA margin was {margin(em(QA_))} '
                       f'against {margin(em(QP_))} in {lab["prior_quarter"]}.'))
        if has_y and YP:
            yr, ye = YA['revenue'] - YP['revenue'], YA['ebitda'] - YP['ebitda']
            body = (f' Revenue is {pabs(ratio(YA["revenue"], YLY["revenue"]))} {"above" if YA["revenue"] >= YLY["revenue"] else "below"} {lab["ly_ytd"]}; ' if YLY else ' ')
            body += f'{ytd_lbl} EBITDA of {usd(YA["ebitda"])} is {usd(abs(ye))} {under(ye)} {plan}.'
            ps.append((f'{ytd_lbl} revenue {usd(YA["revenue"])}, {usd(abs(yr))} {under(yr)} {plan}.', body))
        h1, h1p, h2, h2p, fy_o, fy_p = ry['rev']
        if h2 is not None and h2p is not None and n_open:
            g1_, g2_ = h1 - h1p, h2 - h2p
            ps.append((f'{rest_lbl} revenue outlook {usd(h2)} against {usd(h2p)} {plan}.',
                       (f' The outlook adds to the {ytd_lbl} miss rather than recovering it' if (g1_ < 0 and g2_ < 0) else
                        f' The outlook recovers part of the {ytd_lbl} miss' if (g1_ < 0 < g2_) else ' The outlook stays ahead of plan')
                       + f': full-year revenue lands {usd(abs(fy_o - fy_p))} {"short of" if fy_o < fy_p else "above"} {plan}.'))
        h1, h1p, h2, h2p, fy_o, fy_p = ry['ebitda']
        if h2 is not None and fy_p is not None and n_open and h1 > 0:
            x_need, x_out = ((fy_p - h1) / n_open) / (h1 / k_), ((fy_o - h1) / n_open) / (h1 / k_)
            ps.append((f'{rest_lbl} EBITDA outlook {usd(h2)}' + (f' against {usd(h2p)}.' if h2p is not None else '.'),
                       f' Reaching full-year {plan} would take {x_need:.1f} times the {ytd_lbl} monthly rate; the outlook has {x_out:.1f} times.'))
        if LY and A.get('revenue') and P and P.get('revenue') and LY.get('revenue'):
            s_a, s_p, s_l = A['sm'] / A['revenue'], P['sm'] / P['revenue'], LY['sm'] / LY['revenue']
            ps.append(('Selling cost per revenue dollar.',
                       f' Sales and marketing took {margin(s_a)} of {lab["month_name"]} revenue, against {margin(s_p)} in the {plan} and {margin(s_l)} a year ago: '
                       + ('more revenue per sales and marketing dollar than a year ago' if s_a < s_l else 'less revenue per sales and marketing dollar than a year ago')
                       + (', but less than planned.' if s_a > s_p else ', and more than planned.')))
            gr = {n_: ratio(A[f], LY[f]) for n_, f in (('sales and marketing', 'sm'), ('R&D', 'rd'), ('G&A', 'ga'))}
            slow = [f'{n_} ({pct(v)})' for n_, v in gr.items() if v < yoy]
            fast = [f'{n_} ({pct(v)})' for n_, v in gr.items() if v >= yoy]
            body = f' Revenue {"grew" if yoy >= 0 else "fell"} {pabs(yoy)} on last year.'
            if slow:
                body += f' {cap(joined(slow))} grew more slowly'
            if fast:
                body += (', while ' if slow else ' ') + f'{joined(fast)} grew faster' + ('' if slow else ' than revenue')
            ps.append(('Cost growth against revenue growth.', body + '.'))
        built[key] = ps
    shown[key] = True

    # ---- appendix: P&L detail
    key = 'pnlx'
    deck.text('pnlx.t.g.m', lab['month'])
    deck.text('pnlx.t.g.ytd', lab['ytd'])
    heads(key, 't', ['m_plan', 'm_var', 'ytd_plan', 'ytd_var'])
    deck.text('pnlx.t.h.m_ly', lab['ly_month'])
    deck.text('pnlx.t.h.ytd_ly', lab['ly_ytd'])
    LINES = [('rev', 'revenue', 1), ('cogs', 'cogs', -1), ('gp', 'gross_profit', 1), ('gm', gm, 0), ('sm', 'sm', -1), ('rd', 'rd', -1), ('ga', 'ga', -1),
             ('opex', 'total_opex', -1), ('ebitda', 'ebitda', 1), ('em', em, 0), ('below', 'below', -1), ('ni', 'net_income', 1)]
    for r, f, s in LINES:
        for grp, x, y, z in (('m', A, P, LY), ('ytd', YA, YP, YLY)):
            if s == 0:
                a, p, l = f(x), f(y) if y else None, f(z) if z else None
                d = None if p is None else a - p
                dl = None if l is None else a - l
                deck.text(f'pnlx.t.{r}.{grp}_act', margin(a), a, 'margin')
                deck.text(f'pnlx.t.{r}.{grp}_plan', margin(p), p, 'margin')
                deck.text(f'pnlx.t.{r}.{grp}_var', pts(d), d, 'pts', tone(d))
                deck.text(f'pnlx.t.{r}.{grp}_ly', margin(l), l, 'margin')
                deck.text(f'pnlx.t.{r}.{grp}_yoy', pts(dl), dl, 'pts', tone(dl))
            else:
                a, p, l = x[f], y[f] if y and f in y else None, z[f] if z else None
                d = None if p is None else (a - p) * s
                yy = ratio(a, l)
                deck.text(f'pnlx.t.{r}.{grp}_act', usd(a), a)
                deck.text(f'pnlx.t.{r}.{grp}_plan', usd(p), p)
                deck.text(f'pnlx.t.{r}.{grp}_var', usd(d, True), d, None, tone(d))
                deck.text(f'pnlx.t.{r}.{grp}_ly', usd(l), l)
                deck.text(f'pnlx.t.{r}.{grp}_yoy', pct(yy), yy, 'pct', tone(yy) if s > 0 else 'neu')
    titles[key] = 'P&L detail, month and year to date'
    shown[key] = True

    # ================================================================ 5 people: headcount bridge and labor cost
    key = 'people'
    pe = inp.get('people')
    if pe:
        D_ = sorted(pe['departments'], key=lambda d: -d['labor']['actual']['salaries'])
        if len(D_) > 8:  # the table holds eight rows; the rest are summed into one
            rest = D_[7:]
            agg_ = {'name': 'Other departments'}
            for f in ('heads_open', 'hires', 'departures', 'transfers_net', 'heads_close'):
                agg_[f] = sum(d.get(f, 0) for d in rest)
            agg_['heads_plan'] = None if any(d.get('heads_plan') is None for d in rest) else sum(d['heads_plan'] for d in rest)
            agg_['labor'] = {s: {g: sum((d['labor'].get(s) or {}).get(g, 0) for d in rest) for g in ('salaries', 'taxes_benefits', 'variable', 'sbc')} for s in ('actual', 'plan') if any(d['labor'].get(s) for d in rest)}
            D_ = D_[:7] + [agg_]
        tot = lambda f: sum(d.get(f) or 0 for d in D_)
        opn, hires, deps, cls = tot('heads_open'), tot('hires'), tot('departures'), tot('heads_close')
        has_hp = all(d.get('heads_plan') is not None for d in D_)
        pln = tot('heads_plan') if has_hp else None
        ye = pe.get('year_end', {})
        LAB_ = lambda d, s: sum(d['labor'][s].get(g, 0) for g in ('salaries', 'taxes_benefits', 'variable')) if d['labor'].get(s) else None
        has_la = all(d['labor'].get('actual') for d in D_)
        has_lp = has_la and P is not None and all(d['labor'].get('plan') for d in D_)
        La = sum(LAB_(d, 'actual') for d in D_) if has_la else None
        Lp = sum(LAB_(d, 'plan') for d in D_) if has_lp else None
        sbc = sum((d['labor'].get('actual') or {}).get('sbc', 0) for d in D_)
        sgn = lambda n: (f'+{n}' if n > 0 else f'{MINUS}{abs(n)}' if n < 0 else '0')
        plural = lambda n, w: f'{n} {w}' if n == 1 else (f'{n} people' if w == 'person' else f'{n} {w}s')

        def who(f):
            n = [d['name'] for d in D_ if d.get(f)]
            lim = deck.reg[f'people.{f}.sub']['max_chars']
            return joined(n) if (0 < len(n) <= 2 and len(joined(n)) <= lim) else (f'{len(n)} departments' if len(n) > 1 else n[0][:lim] if n else 'None')
        deck.text('people.open.label', f'{lab["prev_name"].upper()} CLOSE')
        deck.text('people.open.value', count(opn), opn, 'count')
        deck.text('people.open.sub', 'Opening heads')
        deck.text('people.hires.label', 'HIRES')
        deck.text('people.hires.value', sgn(hires), hires, 'count')
        deck.text('people.hires.sub', who('hires'))
        deck.text('people.departures.label', 'DEPARTURES')
        deck.text('people.departures.value', sgn(-deps), deps, 'count')
        deck.text('people.departures.sub', who('departures'))
        deck.text('people.close.label', f'{lab["month_name"].upper()} CLOSE')
        deck.text('people.close.value', count(cls), cls, 'count')
        deck.text('people.close.sub', f'Net {sgn(cls - opn)} in the month')
        deck.text('people.plan.label', f'{lab["month_name"].upper()} {plan.upper()}')
        if pln is not None:
            deck.text('people.plan.value', count(pln), pln, 'count')
            deck.text('people.plan.sub', f'{abs(pln - cls)} {"more" if pln > cls else "fewer"} than actual' if pln != cls else 'Same as actual')
        else:
            deck.text('people.plan.value', DASH)
            deck.text('people.plan.sub', no_plan)
        for m, v, lbl in (('ye_plan', ye.get('plan'), f'{lab["fy_end_name"].upper()} {plan.upper()}'), ('ye_outlook', ye.get('outlook'), f'{lab["fy_end_name"].upper()} OUTLOOK')):
            deck.text(f'people.{m}.label', lbl)
            if v is not None:
                deck.text(f'people.{m}.value', count(v), v, 'count')
                deck.text(f'people.{m}.sub', f'{sgn(v - cls)} from today')
            else:
                deck.text(f'people.{m}.value', DASH)
                deck.text(f'people.{m}.sub', '')
        heads(key, 't', ['plan', 'var', 'cost_var'])
        deck.text('people.t.h.open', lab['prev_name'][:3] if len(lab['prev_name']) > 5 else lab['prev_name'])
        deck.text('people.t.h.close', lab['month_name'][:3] if len(lab['month_name']) > 5 else lab['month_name'])
        rows_ = [(f'd{n}', D_[n - 1] if n <= len(D_) else None) for n in range(1, 9)]
        totals = {'name': 'All departments', 'heads_open': opn, 'hires': hires, 'departures': deps, 'heads_close': cls, 'heads_plan': pln,
                  '_La': La, '_Lp': Lp}
        for rk, d in rows_ + [('total', totals)]:
            if rk != 'total':
                deck.show_shape(f'people.t.{rk}.rule', d is not None)
            if d is None:
                for c in ('label', 'open', 'hires', 'departures', 'close', 'plan', 'var', 'cost', 'cost_var'):
                    deck.text(f'people.t.{rk}.{c}', '', None, 'blank')
                continue
            la = d['_La'] if rk == 'total' else LAB_(d, 'actual')
            lp = d['_Lp'] if rk == 'total' else (LAB_(d, 'plan') if has_lp else None)
            hp = d.get('heads_plan')
            deck.text(f'people.t.{rk}.label', d['name'])
            deck.text(f'people.t.{rk}.open', count(d['heads_open']), d['heads_open'], 'count')
            deck.text(f'people.t.{rk}.hires', count(d['hires']), d['hires'], 'count')
            deck.text(f'people.t.{rk}.departures', count(d['departures']), d['departures'], 'count')
            deck.text(f'people.t.{rk}.close', count(d['heads_close']), d['heads_close'], 'count')
            deck.text(f'people.t.{rk}.plan', count(hp) if hp is not None else DASH, hp, 'count' if hp is not None else 'blank')
            hv = None if hp is None else d['heads_close'] - hp
            deck.text(f'people.t.{rk}.var', sgn(hv) if hv is not None else DASH, None if hv is None else abs(hv), 'count' if hv is not None else 'blank', 'neu')
            deck.text(f'people.t.{rk}.cost', usd(la) if la is not None else DASH, la)
            cv = None if lp is None else la - lp
            deck.text(f'people.t.{rk}.cost_var', usd(cv, True), cv, None, tone(None if cv is None else -cv))
        deck.text('people.chart.label', f'LABOR COST AGAINST {plan.upper()} · {lab["month"].upper()}')
        names_ = [f'Heads vs {plan}', 'Pay rate and mix', 'Taxes and benefits', 'Variable pay']
        if has_lp and has_hp:
            he = sum((d['heads_close'] - d['heads_plan']) * d['labor']['plan']['salaries'] / d['heads_plan'] for d in D_ if d['heads_plan'])
            re_ = sum(d['labor']['actual']['salaries'] - d['labor']['plan']['salaries'] for d in D_) - he
            te = sum(d['labor']['actual']['taxes_benefits'] - d['labor']['plan']['taxes_benefits'] for d in D_)
            ve = sum(d['labor']['actual']['variable'] - d['labor']['plan']['variable'] for d in D_)
            eff = [he, re_, te, ve]
            assert abs(sum(eff) - (La - Lp)) < 0.02, 'labor bridge does not add up'
            deck.chart('people.chart', [f'{n_} {usd(e, True)}' for n_, e in zip(names_, eff)],
                       [(f'Above {plan}', [max(e, 0) / 1000 for e in eff]), (f'Below {plan}', [min(e, 0) / 1000 for e in eff])])
            deck.text('people.chart.note', nb(f'Labor cost {usd(La)} against {usd(Lp)} {plan}, {usd(La - Lp, True)}. Excludes stock-based compensation ({usd(sbc)}).'))
        else:
            eff = None
            deck.chart('people.chart', names_, [(f'Above {plan}', [None] * 4), (f'Below {plan}', [None] * 4)])
            deck.text('people.chart.note', f'Labor cost {usd(La)}. Excludes stock-based compensation ({usd(sbc)}).' if La is not None else '')
        # message and commentary
        if pln is not None and Lp is not None:
            gap, lg = cls - pln, La - Lp
            titles[key] = (f'{cls} people at {lab["month_name"]}, ' + (f'{abs(gap)} {"fewer" if gap < 0 else "more"} than {plan}' if gap else f'in line with {plan}')
                           + f'; labor cost {usd(abs(lg))} {"under" if lg < 0 else "over"} {plan}')
        else:
            titles[key] = f'{cls} people at {lab["month_name"]}, net {sgn(cls - opn)} in the month'
        ps = []
        hn, dn = [d['name'] for d in D_ if d['hires']], [d['name'] for d in D_ if d['departures']]
        body = f' {lab["month_name"]} brought {plural(hires, "hire")}' + (f' ({joined(hn)})' if hn and len(hn) <= 3 else '')
        body += f' and {plural(deps, "departure")}' + (f' ({joined(dn)})' if dn and len(dn) <= 3 else '')
        body += f', a net {"gain" if cls >= opn else "loss"} of {abs(cls - opn)}.' if cls != opn else ', no net change.'
        lead = f'{cls} people at the end of {lab["month_name"]}' + (f', {abs(cls - pln)} {"fewer" if cls < pln else "more"} than {plan}.' if (pln is not None and pln != cls) else '.')
        ps.append((lead, body))
        if eff:
            he, re_, te, ve = eff
            lg = La - Lp
            body = (f' Running {plural(abs(cls - pln), "person")} {"short of" if cls < pln else "above"} {plan} {"saved" if he < 0 else "added"} {usd(abs(he))}' if cls != pln else ' Heads matched the plan')
            body += f'; pay rates and mix {"saved" if re_ < 0 else "added"} {usd(abs(re_))}.'
            ps.append((f'Labor cost {usd(La)}, {usd(abs(lg))} {"under" if lg < 0 else "over"} {plan}.', body))
            body = ''
            if AA and AP and AP.get('new_business'):
                body = (f' Bonus and commissions ran {"below" if ve < 0 else "above"} {plan} in a month when new business ARR came in at '
                        f'{share(AA["new_business"], AP["new_business"])} of {plan}.')
            ps.append((f'Variable pay {usd(abs(ve))} {"under" if ve < 0 else "over"} {plan}.', body))
        n_open = 12 - lab['months_closed']
        if ye.get('plan') is not None and n_open:
            body = f' The {plan} has {ye["plan"]} people in {lab["fy_end_name"]}, {abs(ye["plan"] - cls)} {"more" if ye["plan"] >= cls else "fewer"} than today: '
            body += f'{(ye["plan"] - cls) / n_open:.1f} net hires a month.'
            if ye.get('outlook') is not None:
                body += f' The outlook has {ye["outlook"]}, {sgn(ye["outlook"] - cls)} from today.'
            ps.append(('Hiring to year end.', body))
        if has_hp:
            gaps_ = sorted([d for d in D_ if d['heads_close'] != d['heads_plan']], key=lambda d: d['heads_close'] - d['heads_plan'])[:2]
            if gaps_:
                parts = [f'{d["name"]} has {d["heads_close"]} against {d["heads_plan"]}' for d in gaps_]
                ps.append((f'Furthest from {plan}.', ' ' + cap(joined(parts)) + '.'))
        if opn + cls:
            ar = deps / ((opn + cls) / 2) * 12
            ps.append(('Attrition.', f' {plural(deps, "departure")} in the month is an annualized rate of {pct(ar, False)} of average heads.'))
        built[key] = ps
    shown[key] = bool(pe)

    # ================================================================ 5 cash
    key = 'cash'
    if CA:
        ROWS = ['beginning'] + CASH_LINES + ['other', 'net_change', 'ending']
        LAB = {'beginning': 'Beginning', 'collections': 'Collections', 'payroll': 'Payroll', 'vendors': 'Vendors', 'commissions': 'Commissions',
               'capex': 'Capex', 'other': 'Other, net', 'ending': 'Ending'}
        heads(key, 't', ['plan', 'var'])
        for r in ROWS:
            a, p = CA[r], CP and CP[r]
            sign = r not in ('beginning', 'ending')
            d = None if p is None else a - p
            deck.text(f'cash.t.{r}.act', usd(a, sign), a)
            deck.text(f'cash.t.{r}.plan', usd(p, sign), p)
            deck.text(f'cash.t.{r}.var', usd(d, True), d, None, tone(d))
        WR = [r for r in ROWS if r != 'net_change']
        deck.waterfall('cash.chart', [LAB[r] for r in WR], CA['beginning'], [CA[r] for r in CASH_LINES + ['other']], CA['ending'],
                       [usd(CA[r], r not in ('beginning', 'ending')) for r in WR])
        if CP:
            ev, bv, nv = CA['ending'] - CP['ending'], CA['beginning'] - CP['beginning'], CA['net_change'] - CP['net_change']
            titles[key] = f'Cash {usd(CA["ending"])}, {usd(abs(ev))} {"ahead of" if ev >= 0 else "behind"} {plan}'
            body = (f' The business {"generated" if CA["net_change"] >= 0 else "used"} {usd(abs(CA["net_change"]))} of cash in {lab["month_name"]} '
                    f'against {usd(abs(CP["net_change"]))} planned')
            body += (f'; {usd(bv)} of the lead was built in earlier months.' if 0 <= bv <= ev else
                     f'; it started the month {usd(abs(bv))} {"ahead" if bv >= 0 else "behind"}.')
            ps = [(f'Cash {usd(CA["ending"])}, {usd(abs(ev))} {"ahead of" if ev >= 0 else "behind"} {plan}.', body)]
            cg = CA['collections'] - CP['collections']
            rev_under = P is not None and A['revenue'] < P['revenue']
            ps.append((f'Customers paid {usd(CA["collections"])}.',
                       f' Collections were {usd(abs(cg))} {"below" if cg < 0 else "above"} {plan}'
                       + (f', in a month when revenue also came in under {plan}.' if (cg < 0 and rev_under) else '.')))
            sp = {k: CA[k] - CP[k] for k in ('payroll', 'vendors', 'commissions')}
            word = lambda v: 'under' if v >= 0 else 'over'
            lead = (f'Spending came in under {plan}.' if all(v >= 0 for v in sp.values()) else f'Spending ran over {plan}.' if all(v < 0 for v in sp.values())
                    else f'Spending was mixed against {plan}.')
            body = (f' Payroll was {usd(abs(sp["payroll"]))} {word(sp["payroll"])} {plan}, vendor payments {usd(abs(sp["vendors"]))} {word(sp["vendors"])} '
                    f'and commissions {usd(abs(sp["commissions"]))} {word(sp["commissions"])}.')
            cs = CA['commissions'] / CP['commissions'] if CP['commissions'] else None
            if cs is not None and cs < 0.75 and AA and AP and AP['new_business']:
                body += (f' Commissions were {share(CA["commissions"], CP["commissions"])} of {plan}, in a month when new business ARR came in at '
                         f'{share(AA["new_business"], AP["new_business"])} of {plan}.')
            ps.append((lead, body))
            if cg < 0 and sum(sp.values()) > -cg:
                ps.append(('What it means.', f' Lower spending more than covered the collections shortfall; after other items, the month added '
                                              f'{usd(abs(nv))} {"more" if nv >= 0 else "less"} cash than planned.'))
            built[key] = ps
    shown[key] = bool(CA)

    # ================================================================ 6 go to market: by period, spend by channel, takeaways
    key = 'gtm'
    gtm = inp.get('gtm')
    if gtm:
        def gtm_period(months):
            gs = [month_data(i, 'gtm') for i in months]
            pls = [month_data(i, 'pipeline') for i in months]
            if not gs or any(x is None for x in gs):
                return None
            ch_ = {}
            for g_ in gs:
                for c in g_['channels']:
                    e = ch_.setdefault(c['name'], {'name': c['name'], 'spend': 0.0, 'plan': 0.0, 'plan_ok': True})
                    e['spend'] += c['spend']
                    if c.get('plan') is None:
                        e['plan_ok'] = False
                    else:
                        e['plan'] += c['plan']
            fa = lambda k_: sum((g_['funnel']['actual'].get(k_) or 0) for g_ in gs)
            fp = [g_['funnel'].get('plan', {}).get('mql') if g_['funnel'].get('plan') else None for g_ in gs]
            fopp = [g_['funnel'].get('plan', {}).get('opp') if g_['funnel'].get('plan') else None for g_ in gs]
            out = {'channels': list(ch_.values()), 'spend': sum(c['spend'] for c in ch_.values()),
                   'spend_p': sum(c['plan'] for c in ch_.values()) if all(c['plan_ok'] for c in ch_.values()) else None,
                   'mql': fa('mql'), 'mql_p': sum(fp) if all(x is not None for x in fp) else None,
                   'opp': fa('opp'), 'opp_p': sum(fopp) if all(x is not None for x in fopp) else None,
                   'sal': fa('sal'), 'sql': fa('sql')}
            if all(p_ is not None and p_.get('plan') for p_ in pls):
                out['created'] = sum(p_['actual']['created'] for p_ in pls)
                out['created_p'] = sum(p_['plan']['created'] for p_ in pls)
            out['cpm'] = out['spend'] / out['mql'] if out['mql'] else None
            out['cpm_p'] = out['spend_p'] / out['mql_p'] if (out['spend_p'] is not None and out['mql_p']) else None
            return out
        BYP = {pid: (PER[pid], gtm_period(PER[pid][2])) for pid in PER}
        GP = {g: BYP.get(pid, (None, None)) if pid else (None, None) for g, pid in G3.items()}
        for g, (p, d) in GP.items():
            on = bool(p and d)
            deck.text(f'gtm.p.{g}', p[1] if on else '')
            deck.text(f'gtm.p.h.{g}_act', 'Actual' if on else '')
            deck.show_shape(f'gtm.p.{g}.rule', on)
            deck.text(f'gtm.p.h.{g}_cmp', vs if on else '')
            for rk, fa_, fp_, kind, higher_good in (('spend', 'spend', 'spend_p', 'amount', False), ('mql', 'mql', 'mql_p', 'count', True),
                                                    ('cpm', 'cpm', 'cpm_p', 'amount', False), ('opp', 'opp', 'opp_p', 'count', True),
                                                    ('created', 'created', 'created_p', 'amount', True)):
                if not on or d.get(fa_) is None:
                    deck.text(f'gtm.p.{rk}.{g}_act', '' if not on else DASH, None, 'blank')
                    deck.text(f'gtm.p.{rk}.{g}_cmp', '' if not on else DASH, None, 'blank')
                    continue
                a = d[fa_]
                pv = d.get(fp_) if fp_ else None
                deck.text(f'gtm.p.{rk}.{g}_act', usd(a) if kind == 'amount' else count(a), a, kind)
                r_ = ratio(a, pv)
                deck.text(f'gtm.p.{rk}.{g}_cmp', pct(r_), r_, 'pct' if r_ is not None else 'blank', tone(None if r_ is None else (r_ if higher_good else -r_)))
        chp = BYP['quarter'] if BYP.get('quarter', (None, None))[1] else BYP['month']
        deck.text('gtm.chart.label', f'SPEND BY CHANNEL · {chp[0][1].upper()} · ACTUAL AND {plan.upper()}')
        chs = sorted(chp[1]['channels'], key=lambda c: -c['spend'])[:8]
        deck.chart('gtm.chart', [c['name'] for c in chs], [('Spend', [c['spend'] / 1000 for c in chs]), (Plan, [c['plan'] / 1000 if c['plan_ok'] else None for c in chs])])
        yp_, qp_, mp_ = BYP.get('ytd', (None, None)), BYP.get('quarter', (None, None)), BYP['month']
        main_ = yp_ if yp_[1] else mp_
        if main_[1] and main_[1]['spend_p'] and main_[1]['mql_p']:
            d = main_[1]
            sv, mv = ratio(d['spend'], d['spend_p']), ratio(d['mql'], d['mql_p'])
            titles[key] = (f'{main_[0][1]} spend {pabs(sv)} over {plan} for {pabs(mv)} fewer MQLs' if sv > 0 and mv < 0 else
                           f'{main_[0][1]} spend {pct(sv)} against {plan}; MQLs {pct(mv)}')
            cv = ratio(d['cpm'], d['cpm_p'])
            ps = [(f'{main_[0][1]} spend {usd(d["spend"])}, {pabs(sv)} {"over" if sv >= 0 else "under"} {plan}.',
                   f' MQLs were {count(d["mql"])}, {pabs(mv)} {"under" if mv < 0 else "over"} {plan}, so each MQL cost {usd(d["cpm"])}, '
                   f'{pabs(cv)} {"more" if cv >= 0 else "less"} than planned.')]
            series_ = [(p[1], x) for p, x in (yp_, qp_, mp_) if p and x and x['mql_p']]
            if len(series_) > 1:
                rs = [ratio(x['mql'], x['mql_p']) for _, x in series_]
                worse = all(rs[i] > rs[i + 1] for i in range(len(rs) - 1))
                ps.append(('MQLs are falling further behind.' if worse else 'MQLs against plan.',
                           ' MQLs ran ' + joined([f'{pabs(r_)} {"under" if r_ < 0 else "over"} {plan} for {nm}' if i == 0 else f'{pabs(r_)} for {nm}'
                                                 for i, ((nm, _), r_) in enumerate(zip(series_, rs))]) + '.'))
            cr = [(p[1], x) for p, x in (yp_, qp_, mp_) if p and x and x.get('created_p')]
            if cr:
                nm0, x0 = cr[0]
                r0 = ratio(x0['created'], x0['created_p'])
                rest_ = [f'{nm} {usd(x["created"])}, {pabs(ratio(x["created"], x["created_p"]))} {"under" if x["created"] < x["created_p"] else "over"}' for nm, x in cr[1:]]
                ps.append((f'Pipeline created {usd(x0["created"])} in {nm0}, {pabs(r0)} {"under" if r0 < 0 else "over"} {plan}.',
                           (' ' + cap(joined(rest_)) + '.') if rest_ else ''))
            if qp_[1] or mp_[1]:
                cp = qp_ if qp_[1] else mp_
                chs_ = cp[1]['channels']
                over = [c for c in chs_ if c['plan_ok'] and c['spend'] > c['plan']]
                topc = max(chs_, key=lambda c: c['spend'])
                ps.append(((f'Every channel ran over {plan} in {cp[0][1]}.' if len(over) == len(chs_) else f'{len(over)} of {len(chs_)} channels ran over {plan} in {cp[0][1]}.'),
                           f' {topc["name"]} took the largest share of spend at {share(topc["spend"], cp[1]["spend"])}.'))
            if main_[1]['opp']:
                parts = [f'{count(x["opp"])} in {p[1]}' for p, x in (qp_, mp_) if p and x]
                ps.append((f'{count(main_[1]["opp"])} opportunities created in {main_[0][1]}.', (' ' + cap(joined(parts)) + '.') if parts else ''))
            built[key] = ps
    shown[key] = bool(gtm)

    # ================================================================ 7 pipeline
    key = 'pipe'
    pipe = inp.get('pipeline')
    if pipe:
        PA, PP = pipe['actual'], pipe.get('plan')
        ROWS = ['beginning', 'created', 'closed_won', 'closed_lost', 'slipped', 'ending']
        LAB = {'beginning': 'Beginning', 'created': 'Created', 'closed_won': 'Closed won', 'closed_lost': 'Closed lost', 'slipped': 'Slipped', 'ending': 'Ending'}
        heads(key, 't', ['plan', 'share'])
        for r in ROWS:
            sign = r not in ('beginning', 'ending')
            p = PP[r] if PP else None
            deck.text(f'pipe.t.{r}.act', usd(PA[r], sign), PA[r])
            deck.text(f'pipe.t.{r}.plan', usd(p, sign), p)
            deck.text(f'pipe.t.{r}.share', share(PA[r], p), None if not p else PA[r] / p, 'margin' if p else 'blank')
        wr = -PA['closed_won'] / -(PA['closed_won'] + PA['closed_lost']) if (PA['closed_won'] + PA['closed_lost']) else None
        wrp = (-PP['closed_won'] / -(PP['closed_won'] + PP['closed_lost'])) if (PP and (PP['closed_won'] + PP['closed_lost'])) else None
        deck.text('pipe.t.win_rate.act', margin(wr), wr, 'margin')
        deck.text('pipe.t.win_rate.plan', margin(wrp), wrp, 'margin')
        deck.text('pipe.t.win_rate.share', '', None, 'blank')
        deck.waterfall('pipe.chart', [LAB[r] for r in ROWS], PA['beginning'], [PA[r] for r in ROWS[1:-1]], PA['ending'],
                       [usd(PA[r], r not in ('beginning', 'ending')) for r in ROWS])
        if PP and PP.get('created'):
            titles[key] = f'Pipeline created at {share(PA["created"], PP["created"])} of {plan}; the month ends with {usd(PA["ending"])}'
            cs_ = PA['created'] / PP['created']
            ps = [(f'New pipeline {usd(PA["created"])}, {share(PA["created"], PP["created"])} of {plan}.',
                   f' The month added less than half the new pipeline planned ({usd(PP["created"])}).' if cs_ < 0.5 else
                   f' {Plan} called for {usd(PP["created"])} of new pipeline in the month.')]
            if wr is not None and wrp is not None and (PP['closed_won'] + PP['closed_lost']):
                close_ = abs(wr - wrp) < 0.05
                decided = (PA['closed_won'] + PA['closed_lost']) / (PP['closed_won'] + PP['closed_lost'])
                ps.append((f'Win rate {margin(wr)} against {margin(wrp)}.',
                           f' Closed-won was {usd(-PA["closed_won"])} against {usd(-PP["closed_won"])}: only {share(decided, 1)} of the planned volume reached a decision'
                           + ('; the win rate held close to plan.' if close_ else '.')))
            if PP.get('closed_lost') and PP.get('slipped'):
                cl, sl_ = PA['closed_lost'] / PP['closed_lost'], PA['slipped'] / PP['slipped']
                ps.append(('Fewer losses and slips.' if (cl < 1 and sl_ < 1) else 'Losses and slips.',
                           f' Closed lost and slipped ran at {share(PA["closed_lost"], PP["closed_lost"])} and {share(PA["slipped"], PP["slipped"])} of {plan}, '
                           f'in line with a pipeline that started the month at {share(PA["beginning"], PP["beginning"])} of {plan}.'))
            ps.append((f'Ending pipeline {usd(PA["ending"])}, {share(PA["ending"], PP["ending"])} of {plan}.',
                       f' {lab["next_name"]} starts with {"less" if PA["ending"] < PA["beginning"] else "more"} pipeline than {lab["month_name"]} did '
                       f'({usd(PA["beginning"])}).'))
            built[key] = ps
        elif PP:
            titles[key] = f'The month ends with {usd(PA["ending"])} of pipeline'
            built[key] = [(f'Ending pipeline {usd(PA["ending"])}.', '')]
    shown[key] = bool(pipe)

    # ================================================================ 8 where the year is heading
    key = 'year'
    if ol:
        open_ = lab['months_closed'] < 12
        minis = {'rev': ('Revenue', YA['revenue'], FY['revenue'], FYP and FYP['revenue'], 'flow', None),
                 'ebitda': ('EBITDA', YA['ebitda'], FY['ebitda'], FYP and FYP['ebitda'], 'flow', None),
                 'arr': ('Ending ARR', end_arr, FY['ending_arr'], FYP and FYP['ending_arr'], 'balance', end_arr_p),
                 'cash': ('Ending cash', end_cash, FY['ending_cash'], FYP and FYP['ending_cash'], 'balance', end_cash_p)}
        for m, (name, h1, fy, p, kind, p_close) in minis.items():
            deck.text(f'year.{m}.label', f'{name.upper()} · {lab["fy_name"]}')
            gap = None if p is None else fy - p
            note = f'Outlook {usd(fy)} · {Plan} {usd(p)} · {usd(gap, True)} ({pct(ratio(fy, p))})' if p is not None else f'Outlook {usd(fy)} · {no_plan}'
            if kind == 'flow':
                h2 = fy - h1 if open_ else None
                deck.chart(f'year.{m}.chart', ['Outlook', Plan],
                           [(lab['h1'], [None if h1 is None else h1 / 1e6, None]), (lab['h2'], [h2 / 1e6 if h2 is not None else None, None]), (Plan, [None, p / 1e6 if p is not None else None])])
                note += f' · {lab["closed_span"]} {usd(h1)}' + (f' · {lab["rest_span"]} {usd(h2)}' if open_ else '') + (f' · {plan} needs {usd(p - h1)}' if (p is not None and open_) else '')
            else:
                deck.chart(f'year.{m}.chart', [lab['month_short'], f'{lab["fy_end_mon"]} outlook', f'{lab["fy_end_mon"]} {plan}'],
                           [('Actual', [None if h1 is None else h1 / 1e6, None, None]), ('Outlook', [None, None if fy is None else fy / 1e6, None]), (Plan, [None, None, p / 1e6 if p is not None else None])])
                if open_ and m == 'arr' and p is not None and h1 is not None and AA:
                    n_ = 12 - lab['months_closed']
                    note += (f' · {usd((fy - h1) / n_)} a month from {lab["next_short"]} reaches the outlook, {usd((p - h1) / n_)} reaches {plan}; '
                             f'{lab["month_short"].split()[0]} {usd(AA["net_new"])}')
                elif open_ and h1 is not None:
                    note += f' · {lab["rest_span"]} change {usd(fy - h1, True)}' + (f', {plan} path {usd(p - p_close, True)}' if (p is not None and p_close is not None) else '')
            deck.text(f'year.{m}.note', nb(note))
        h2gm = ol.get('rest_of_year_gross_margin') if open_ else None
        deck.text('year.gm', f'Gross margin: {lab["closed_span"]} {margin(gm(YA))}' + (f' · {lab["rest_span"]} outlook {margin(h2gm)}' if open_ else '')
                  + f' · FY outlook {margin(FY["gross_margin"])}' + (f' · {Plan} {margin(FYP["gross_margin"])}' if FYP else ''))
        if FYP:
            rows = [(m, *minis[m]) for m in ('rev', 'ebitda', 'arr', 'cash')]
            behind = sorted([r for r in rows if r[4] and r[3] < r[4]], key=lambda r: (r[3] - r[4]) / abs(r[4]))
            ahead = [r for r in rows if r[3] >= r[4]]
            low = lambda n: n if n in ('EBITDA',) else n[:1].lower() + n[1:]
            t = 'Full-year outlook: ' + (joined([f'{low(r[1])} {usd(r[4] - r[3])}' for r in behind[:2]]) + f' short of {plan}' if behind else f'every measure at or ahead of {plan}')
            titles[key] = t
            k_, n_ = lab['months_closed'], 12 - lab['months_closed']
            ps = []
            name, h1, fy, p = minis['rev'][:4]
            body = ''
            if open_ and h1:
                o_rate, h_rate, n_rate = (fy - h1) / n_, h1 / k_, (p - h1) / n_
                body = (f' The outlook has monthly revenue for {lab["rest_span"]} {pabs(o_rate / h_rate - 1)} {"above" if o_rate >= h_rate else "below"} '
                        f'the {lab["closed_span"]} average; reaching {plan} needs {pabs(n_rate / h_rate - 1)} {"above" if n_rate >= h_rate else "below"}.')
            ps.append((f'Revenue outlook {usd(fy)}, {usd(abs(fy - p))} {"short of" if fy < p else "above"} {plan}.', body))
            name, h1, fy, p = minis['ebitda'][:4]
            body = ''
            if open_ and h1 is not None and h1 > 0:
                x = ((p - h1) / n_) / (h1 / k_)
                body = (f' Reaching {plan} needs {usd(p - h1)} of EBITDA in {lab["rest_span"]}, {x:.1f} times the monthly rate so far; '
                        f'the outlook has {usd(fy - h1)}.')
            ps.append((f'EBITDA outlook {usd(fy)} against {usd(p)}.', body))
            name, h1, fy, p, _, pc = minis['arr']
            if open_ and AA and h1 is not None:
                ps.append((f'Ending ARR outlook {usd(fy)} against {usd(p)}.',
                           f' The outlook takes {usd((fy - h1) / n_)} of net new ARR a month from {lab["next_name"]}; {plan} takes {usd((p - h1) / n_)}, '
                           f'against {usd(AA["net_new"])} in {lab["month_name"]}.'))
            else:
                ps.append((f'Ending ARR outlook {usd(fy)} against {usd(p)}.', ''))
            name, h1, fy, p, _, pc = minis['cash']
            only = [r[0] for r in ahead] == ['cash']
            ps.append((f'Ending cash outlook {usd(fy)}, {usd(abs(fy - p))} {"ahead of" if fy >= p else "behind"} {plan}.',
                       f' Cash is the one full-year measure ahead of {plan}.' if only else
                       (f' The outlook {"adds" if fy >= h1 else "uses"} {usd(abs(fy - h1))} of cash over {lab["rest_span"]}.' if open_ and h1 is not None else '')))
            g1, g2, gf, gp = gm(YA), h2gm, FY['gross_margin'], FYP['gross_margin']
            ps.append((f'Gross margin outlook {margin(gf)} against {margin(gp)}.',
                       (f' The outlook holds the {lab["closed_span"]} margin of {margin(g1)} through {lab["rest_span"]}.' if margin(g1) == margin(g2) else
                        f' The outlook has {margin(g2)} for {lab["rest_span"]} against {margin(g1)} so far.') if open_ and g2 is not None else ''))
            built[key] = ps
    shown[key] = bool(ol)

    # ================================================================ 9 appendix: YTD cash flow
    key = 'cf'
    cf = inp.get('cf_ytd')
    if cf:
        XA, XP = dict(cf['actual']), dict(cf['plan']) if cf.get('plan') else None
        WC = ['net_income', 'da', 'sbc', 'ar', 'deferred_revenue', 'ap', 'prepaids', 'deferred_commissions']
        for d in (XA, XP):
            if d:
                d['other'] = d['cfo'] - sum(d[x] for x in WC)
        deck.text('cf.t.h.act', f'{lab["ytd_short"]} actual')
        deck.text('cf.t.h.plan', f'{lab["ytd_short"]} {plan}')
        deck.text('cf.t.h.var', vs)
        for r in ['beginning'] + WC + ['other', 'cfo', 'capex', 'cff', 'net_change', 'ending']:
            a, p = XA[r], XP and XP[r]
            d = None if p is None else a - p
            deck.text(f'cf.t.{r}.act', usd(a), a)
            deck.text(f'cf.t.{r}.plan', usd(p), p)
            deck.text(f'cf.t.{r}.var', usd(d, True), d, None, tone(d))
        titles[key] = 'Cash flow, year to date'
    shown[key] = bool(cf)

    # ================================================================ hide, then write titles and commentary (each held to its slide)
    for k, on in shown.items():
        deck.show_slide(k, on)
        if not on:
            deck.blank_slide(k)
    heads_ = {n for n, s in deck.reg.items() if s['kind'] in ('commentary', 'headline')}
    notes = inp.get('notes', {})
    report = {}
    for k in [x for x in deck.sections if x != 'cover']:
        if not shown.get(k, True):
            continue
        vis = set(dollars(visible_text(deck.slide[k], heads_)))
        t = titles.get(k)
        ok = t and not [x for x in dollars(t) if x not in vis] and len(t) <= deck.reg[f'{k}.title']['max_chars']
        deck.text(f'{k}.title', nb(t) if ok else deck.sections[k])
        rep = {'title': 'message' if ok else 'section name'}
        groups = [n[:-6] for n, s_ in deck.reg.items() if s_['slide'] == k and n.endswith('.notes')]
        for grp in groups:
            boxes = [f'{grp}.notes'] + ([f'{grp}.notes.right'] if f'{grp}.notes.right' in deck.reg else [])
            cands = []
            for n in notes.get(grp, []) if isinstance(notes.get(grp), list) else ([notes[grp]] if notes.get(grp) else []):
                cands.append(('close note', (n.get('lead', ''), ' ' + n.get('body', '').lstrip()) if isinstance(n, dict) else ('', n)))
            cands += [('built', (a, b)) for a, b in built.get(grp, [])]
            ok_, dropped, n_notes = [], [], 0
            for src, (a, b) in cands:
                miss = [x for x in dollars(a + b) if x not in vis]
                if miss:
                    dropped.append(f'{src} "{a or (a + b)[:30]}" cites {miss}, not on the slide')
                else:
                    ok_.append((src, a, b))
            # fit by the box's own size: estimated lines at its font, never past its character limit
            fit = [box_fit(deck.shape[b], deck.reg[b]['max_chars']) for b in boxes]
            hts = [fit[0]['height'](a + b) for _, a, b in ok_]
            total = sum(hts)
            cols, i = [[] for _ in boxes], 0
            for c in range(len(boxes)):
                used, chars = 0.0, 0
                target = total / 2 if (len(boxes) == 2 and c == 0) else float('inf')
                while i < len(ok_):
                    src, a, b = ok_[i]
                    h = fit[c]['height'](a + b)
                    if used + h > fit[c]['capacity'] or chars + len(a + b) > fit[c]['limit']:
                        break
                    cols[c].append((nb(a), nb(b)))
                    n_notes += src == 'close note'
                    used += h
                    chars += len(a + b) + 1
                    i += 1
                    if used >= target:
                        break
                total -= used
            for src, a, b in ok_[i:]:
                dropped.append(f'{src} "{a or (a + b)[:30]}" does not fit')
            for b_, ps_ in zip(boxes, cols):
                deck.paras(b_, ps_)
            keep = [p_ for c in cols for p_ in c]
            rep[grp] = {'paragraphs': len(keep), 'from_notes': n_notes, 'dropped': dropped}
        report[k] = rep
    return {'labels': lab, 'shown': shown, 'commentary': report}


# ------------------------------------------------------------------ deck check
LINT = re.compile(r'\b(' + '|'.join(MON + MON3) + r')\b|\bQ[1-4]\b|\b(19|20)\d\d\b|\bYTD\b|\bbudget\b|\bforecast\b', re.I)


def parse_amount(tok):
    t = tok.replace(WJ, '')
    m = re.search(r'([+−]?)\$([\d,]+(?:\.\d+)?)([KM]?)', t)
    if not m:
        return None, None
    v = Decimal(m.group(2).replace(',', ''))
    unit = {'M': Decimal(1000000), 'K': Decimal(1000), '': Decimal(1)}[m.group(3)]
    step = {'M': Decimal('0.01'), 'K': Decimal('0.1'), '': Decimal(1)}[m.group(3)] * unit
    return v * unit * (-1 if m.group(1) == MINUS else 1), step


def check(out_path, template_path, reg, info, written):
    prs, tpl = Presentation(out_path), Presentation(template_path)
    regs = {s['name']: s for s in reg['slots']}
    problems, n_boxes, n_sent = [], 0, 0
    geo = lambda p: [(i, sh.name, sh.left, sh.top, sh.width, sh.height) for i, sl in enumerate(p.slides) for sh in sl.shapes]
    if geo(prs) != geo(tpl):
        problems.append({'check': 'geometry', 'detail': sorted(map(str, set(geo(prs)) ^ set(geo(tpl))))[:10]})
    shapes = {sh.name: (sl, sh) for sl in prs.slides for sh in sl.shapes}
    for name, s in regs.items():
        if name not in written:
            problems.append({'check': 'unwritten', 'slot': name})
            continue
        w = written[name]
        if s['kind'] == 'chart':
            ch = shapes[name][1].chart
            if [str(c) for c in ch.plots[0].categories] != [str(c) for c in w['categories']]:
                problems.append({'check': 'chart categories', 'slot': name})
            if 'labels' in w:
                got = [bar_plot(ch).series[4].points[i].data_label.text_frame.text for i in range(len(w['labels']))]
                if got != w['labels']:
                    problems.append({'check': 'chart labels', 'slot': name, 'got': got})
            allser = [sr for p_ in cat_plots(ch) for sr in p_.series]
            if 'connectors' in w:
                sc = ch._chartSpace.find('.//' + qn('c:scatterChart'))
                got = [tuple([float(v.text) for v in ser.find(qn(t)).iter(qn('c:v'))] for t in ('c:xVal', 'c:yVal'))
                       for ser in sc.findall(qn('c:ser'))]
                if got != [tuple(xy) for xy in w['connectors']]:
                    problems.append({'check': 'chart connectors', 'slot': name})
                if 'scale' in w:
                    _, mx, _ = w['scale']
                    if abs(box_axis(ch).maximum_scale - mx) > 1e-9:
                        problems.append({'check': 'chart scale', 'slot': name})
                for xs, ys in w['connectors']:
                    if xs and not (xs[0] % 1 > 0 and xs[1] % 1 > 0 and int(xs[0]) == int(xs[1])):
                        problems.append({'check': 'connector crosses a box', 'slot': name, 'x': xs})
            if len(allser) != len(w['series']):
                problems.append({'check': 'chart series count', 'slot': name, 'got': len(allser), 'given': len(w['series'])})
            for sr, (nm, vals) in zip(allser, w['series']):
                gv = list(sr.values)
                if any((x is None) != (y is None) or (x is not None and abs(x - y) > 1e-6) for x, y in zip(gv, vals)):
                    problems.append({'check': 'chart values', 'slot': name, 'series': nm})
            continue
        box = shapes[name][1].text_frame.text
        if box != w['text']:
            problems.append({'check': 'box text', 'slot': name, 'box': box[:80], 'given': (w['text'] or '')[:80]})
            continue
        n_boxes += 1
        lim = s['max_chars']
        if lim and len(box.replace(WJ, '')) > lim:
            problems.append({'check': 'limit', 'slot': name, 'chars': len(box.replace(WJ, '')), 'limit': lim})
        v = w.get('value')
        if v is None:
            continue
        if w['kind'] in ('amount', 'label+amount'):
            got, step = parse_amount(box)
            if got is None or abs(got - D(v)) > step / 2 + Decimal('0.000001'):
                problems.append({'check': 'number', 'slot': name, 'box': box, 'given': v})
        elif w['kind'] in ('pct', 'margin', 'label+margin', 'pts'):
            m = re.search(r'([+−]?)(\d+\.\d)', box)
            got = Decimal(m.group(2)) * (-1 if m.group(1) == MINUS else 1)
            if abs(got - (D(v) * 100)) > Decimal('0.0500001'):
                problems.append({'check': 'number', 'slot': name, 'box': box, 'given': v})
        elif w['kind'] in ('count', 'label+count'):
            if int(re.search(r'[\d,]+', box).group(0).replace(',', '')) != int(round(v)):
                problems.append({'check': 'number', 'slot': name, 'box': box, 'given': v})
    heads_ = {n for n, s in regs.items() if s['kind'] in ('commentary', 'headline')}
    for name in heads_:
        sl, sh = shapes[name]
        txt = sh.text_frame.text
        if not txt.strip():
            continue
        if regs[name]['kind'] == 'commentary':
            n_sent += len(re.findall(r'[.!?](\s|$)', txt))
        vis = set(dollars(visible_text(sl, heads_)))
        miss = [t for t in dollars(txt) if t not in vis]
        if miss:
            problems.append({'check': 'sentence dollars', 'slot': name, 'not on slide': miss})
    for sl in prs.slides:
        for sh in sl.shapes:
            if sh.name in regs or not sh.has_text_frame:
                continue
            if LINT.search(sh.text_frame.text):
                problems.append({'check': 'static period word', 'shape': sh.name, 'text': sh.text_frame.text})
    return {'passed': not problems, 'boxes_checked': n_boxes, 'sentences_checked': n_sent, 'problems': problems,
            'slides_shown': info['shown'], 'commentary': info['commentary']}


def main(deck_in, template, slots, input_path, deck_out, check_out):
    reg = json.load(open(slots))
    inp = json.load(open(input_path))
    deck = Deck(deck_in, reg)
    info = fill(deck, inp)
    deck.prs.save(deck_out)
    res = check(deck_out, template, reg, info, deck.written)
    json.dump(res, open(check_out, 'w'), indent=1, ensure_ascii=False)
    print('passed' if res['passed'] else 'FAILED', '| boxes', res['boxes_checked'], '| sentences', res['sentences_checked'], '| problems', len(res['problems']))
    for p in res['problems'][:15]:
        print('  ', p)
    for k, v in res['commentary'].items():
        print('  ', k, v)


if __name__ == '__main__':
    main(*sys.argv[1:7])
