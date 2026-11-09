"""Build the Board Operating Review template, version 7: one fixed design, eleven slides, each with its
own layout. Every period word, comparison label, number, chart category, headline and commentary
paragraph is a named slot. Writes the template and slots.json (the registry the filler, the deck
check and the slot map read).

Static text is limited to section names and line labels that never change with the close.

usage: python bor_template.py out_template.pptx out_slots.json
"""
import json
import sys

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION, XL_TICK_MARK
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from lxml import etree

# ------------------------------------------------------------------ look (from the Board Operating Review)
BG = RGBColor(0x07, 0x0D, 0x18)
CARD = RGBColor(0x11, 0x1D, 0x2E)
LINE = RGBColor(0x1A, 0x2E, 0x42)
ZEBRA = RGBColor(0x0D, 0x15, 0x20)
MUTED = RGBColor(0x6B, 0x8C, 0xA8)
SOFT = RGBColor(0xB4, 0xC6, 0xD6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEAL = RGBColor(0x00, 0xD4, 0xAA)
GREEN = RGBColor(0x22, 0xC5, 0x5E)
RED = RGBColor(0xEF, 0x44, 0x44)
PLAN = RGBColor(0x3E, 0x5F, 0x80)
FONT = 'Calibri'
L, R = 0.45, 13.333 - 0.45
W = R - L

SLOTS, SLIDES = [], []


def slot(name, slide, kind, receives, limit=None, group=None, tone=False):
    SLOTS.append({'name': name, 'slide': slide, 'kind': kind, 'receives': receives, 'max_chars': limit, 'group': group, 'tone': tone})


def _nostyle(el):
    st = el.find(qn('p:style'))
    if st is not None:
        el.remove(st)


def text(sl, name, x, y, w, h, value, size=11, bold=False, color=WHITE, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, wrap=True):
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.name = name
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    tf.auto_size = None
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = value
    f = r.font
    f.name, f.size, f.bold = FONT, Pt(size), bold
    f.color.rgb = color
    return tb


def stext(sl, key, name, x, y, w, h, sample, kind, receives, limit=None, group=None, tone=False, **kw):
    slot(name, key, kind, receives, limit, group, tone)
    return text(sl, name, x, y, w, h, sample, **kw)


def rect(sl, name, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE):
    s = sl.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.name = name
    _nostyle(s._element)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(0.75)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.5
    return s


def rule(sl, name, x, y, w, color=LINE, weight=0.75):
    """A hairline drawn as a thin filled rectangle, so it can be hidden like any other shape."""
    s = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Pt(weight))
    s.name = name
    _nostyle(s._element)
    s.fill.solid()
    s.fill.fore_color.rgb = color
    s.line.fill.background()
    return s


def section(sl, name, x, y, w, value):
    return text(sl, name, x, y, w, 0.22, value, size=9.5, bold=True, color=TEAL)


def new_slide(prs, key, section_name, kicker):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    sl.background.fill.solid()
    sl.background.fill.fore_color.rgb = BG
    SLIDES.append({'key': key, 'title': section_name})
    if key == 'cover':
        return sl
    text(sl, f'{key}.kicker', L, 0.32, 8, 0.22, kicker, size=10, bold=True, color=TEAL)
    stext(sl, key, f'{key}.title', L, 0.52, 11.0, 0.5, f'{section_name} — June 2026', 'label',
          f'"{section_name} — " then the close month and year ("June 2026").', 60, size=24, bold=True)
    rule(sl, f'{key}.footer_rule', L, 6.98, W, LINE)
    stext(sl, key, f'{key}.footer', L, 7.06, 10.5, 0.22, 'SMPL Demo Co · Board Operating Review · June 2026 · Draft', 'label',
          'Company · "Board Operating Review" · close month · "Draft" while the close is a draft (nothing when approved).', 90, size=9, color=MUTED)
    pn = text(sl, f'{key}.page', R - 0.6, 7.06, 0.6, 0.22, '', size=9, color=MUTED, align=PP_ALIGN.RIGHT)
    p = pn.text_frame.paragraphs[0]._p
    for r in p.findall(qn('a:r')):
        p.remove(r)
    fld = etree.SubElement(p, qn('a:fld'))
    fld.set('id', '{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}')
    fld.set('type', 'slidenum')
    rpr = etree.SubElement(fld, qn('a:rPr'))
    rpr.set('lang', 'en-US')
    rpr.set('sz', '900')
    sf = etree.SubElement(rpr, qn('a:solidFill'))
    etree.SubElement(sf, qn('a:srgbClr')).set('val', '6B8CA8')
    etree.SubElement(rpr, qn('a:latin')).set('typeface', FONT)
    etree.SubElement(fld, qn('a:t')).text = '2'
    return sl


def tile(sl, key, mkey, x, y, w, h, label, value_sample, plan_sample, var_sample, receives, kind, plan_group, value_size=24):
    rect(sl, f'{key}.{mkey}.bg', x, y, w, h, CARD, LINE)
    text(sl, f'{key}.{mkey}.label', x + 0.16, y + 0.13, w - 0.32 - 0.66, 0.2, label, size=9, bold=True, color=MUTED)
    stext(sl, key, f'{key}.{mkey}.var', x + w - 0.16 - 0.66, y + 0.12, 0.66, 0.22, var_sample, 'pct' if kind != 'pct' else 'pts',
          f'{receives}: actual against plan, {"percent" if kind != "pct" else "points"}; green ahead, red behind.', 10, plan_group, True,
          size=10, bold=True, color=SOFT, align=PP_ALIGN.RIGHT)
    stext(sl, key, f'{key}.{mkey}.value', x + 0.16, y + 0.36, w - 0.32, 0.46, value_sample, kind, f'{receives}: actual.', 12,
          size=value_size, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    stext(sl, key, f'{key}.{mkey}.plan', x + 0.16, y + h - 0.36, w - 0.32, 0.22, plan_sample, 'label+' + kind,
          f'{receives}: plan label and plan figure ("Budget $84.89M"); "No budget loaded" when not loaded.', 24, plan_group, size=9.5, color=MUTED)


def grid(sl, key, tkey, x, y, cols, rows, row_h=0.4, head_h=0.34, zebra=True, label_slot=None, row_rules=False, size=11):
    """cols: [(ckey, width, header, header_slot_receives|None, kind, receives, group, tone, align)]
    The first col is the row label. rows: [(rkey, label, emphasis)]."""
    cx = x
    xs = []
    for c in cols:
        xs.append(cx)
        cx += c[1]
    width = cx - x
    for i, c in enumerate(cols):
        ckey, cw, head, head_slot = c[0], c[1], c[2], c[3]
        al = c[8] if len(c) > 8 else (PP_ALIGN.LEFT if i == 0 else PP_ALIGN.RIGHT)
        pad = 0.12
        if head_slot:
            stext(sl, key, f'{key}.{tkey}.h.{ckey}', xs[i] + pad, y, cw - 2 * pad, head_h, head, 'label', head_slot, 22,
                  size=9, bold=True, color=MUTED, align=al, anchor=MSO_ANCHOR.MIDDLE)
        else:
            text(sl, f'{key}.{tkey}.h.{ckey}', xs[i] + pad, y, cw - 2 * pad, head_h, head, size=9, bold=True, color=MUTED, align=al, anchor=MSO_ANCHOR.MIDDLE)
    rule(sl, f'{key}.{tkey}.h.rule', x, y + head_h, width, LINE, 1.0)
    for j, (rkey, label, emph) in enumerate(rows):
        ry = y + head_h + j * row_h
        if zebra and j % 2 == 1:
            rect(sl, f'{key}.{tkey}.{rkey}.zebra', x, ry, width, row_h, ZEBRA)
        if row_rules:
            rule(sl, f'{key}.{tkey}.{rkey}.rule', x, ry + row_h, width, LINE, 0.5)
        for i, c in enumerate(cols):
            ckey, cw = c[0], c[1]
            al = c[8] if len(c) > 8 else (PP_ALIGN.LEFT if i == 0 else PP_ALIGN.RIGHT)
            pad = 0.12
            nm = f'{key}.{tkey}.{rkey}.{ckey}'
            if i == 0:
                if label_slot:
                    stext(sl, key, nm, xs[i] + pad, ry, cw - 2 * pad, row_h, label, 'label', label_slot(rkey), 26,
                          size=size, bold=emph, color=WHITE if emph else SOFT, anchor=MSO_ANCHOR.MIDDLE)
                else:
                    text(sl, nm, xs[i] + pad, ry, cw - 2 * pad, row_h, label, size=size, bold=emph, color=WHITE if emph else SOFT, anchor=MSO_ANCHOR.MIDDLE)
                continue
            kind, receives, group, tone = c[4], c[5], c[6], c[7]
            stext(sl, key, nm, xs[i] + pad, ry, cw - 2 * pad, row_h, '$0.00M', kind, f'{label}: {receives}', 12, group, tone,
                  size=size, bold=emph or tone, color=SOFT if tone else WHITE, align=al, anchor=MSO_ANCHOR.MIDDLE)
    return width


def read_box(sl, key, x, y, w, h, heading, limit, size=13, receives=None):
    rect(sl, f'{key}.read.bg', x, y, w, h, CARD, LINE)
    text(sl, f'{key}.read.label', x + 0.22, y + 0.16, w - 0.44, 0.2, heading, size=9.5, bold=True, color=TEAL)
    stext(sl, key, f'{key}.read', x + 0.22, y + 0.44, w - 0.44, h - 0.58, '', 'commentary',
          receives or 'Commentary about the business: what moved against plan and what it means. Every dollar in it is on this slide; blank if a sentence cannot meet that.',
          limit, size=size, color=WHITE)


# ------------------------------------------------------------------ charts
def style_chart(chart, legend=False):
    chart.has_title = False
    chart.font.size = Pt(9)
    chart.font.name = FONT
    chart.font.color.rgb = MUTED
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(9)
        chart.legend.font.color.rgb = SOFT
    # transparent chart and plot area
    cs = chart._chartSpace
    sp = cs.find(qn('c:spPr'))
    if sp is None:
        sp = etree.SubElement(cs, qn('c:spPr'))
        cs.insert(cs.index(cs.find(qn('c:chart'))) + 1, sp)
    for ch in list(sp):
        sp.remove(ch)
    etree.SubElement(sp, qn('a:noFill'))
    ln = etree.SubElement(sp, qn('a:ln'))
    etree.SubElement(ln, qn('a:noFill'))


def style_axes(chart, num_fmt, cat_low=True, gridlines=True):
    ca, va = chart.category_axis, chart.value_axis
    ca.format.line.color.rgb = LINE
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.tick_labels.font.size = Pt(9)
    ca.tick_labels.font.color.rgb = SOFT
    if cat_low:
        ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    va.has_major_gridlines = gridlines
    if gridlines:
        va.major_gridlines.format.line.color.rgb = LINE
        va.major_gridlines.format.line.width = Pt(0.5)
    va.format.line.fill.background()
    va.major_tick_mark = XL_TICK_MARK.NONE
    va.tick_labels.number_format = num_fmt
    va.tick_labels.number_format_is_linked = False
    va.tick_labels.font.size = Pt(9)
    va.tick_labels.font.color.rgb = MUTED


def fill_series(s, color):
    s.format.fill.solid()
    s.format.fill.fore_color.rgb = color
    s.format.line.fill.background()


def no_fill_series(s):
    s.format.fill.background()
    s.format.line.fill.background()


def add_chart(sl, name, kind, x, y, w, h, cats, series):
    cd = CategoryChartData()
    cd.categories = cats
    for nm, vals in series:
        cd.add_series(nm, vals)
    gf = sl.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    gf.name = name
    return gf.chart


def waterfall(sl, key, name, x, y, w, h, cats, receives, group):
    n = len(cats)
    ch = add_chart(sl, name, XL_CHART_TYPE.COLUMN_STACKED, x, y, w, h, cats,
                   [('Base', [1] * n), ('Increase', [1] * n), ('Decrease', [1] * n), ('Total', [1] * n)])
    style_chart(ch)
    style_axes(ch, '"$"#,##0"M"')
    pl = ch.plots[0]
    pl.gap_width = 45
    pl.overlap = 100
    s = pl.series
    no_fill_series(s[0])
    fill_series(s[1], GREEN)
    fill_series(s[2], RED)
    fill_series(s[3], TEAL)
    slot(name, key, 'chart', receives, None, group)
    return ch



# ================================================================== version 2 overrides
import copy


def new_slide(prs, key, section_name, kicker_sample, title_sample):
    """Kicker = section and close month (a slot); title = the slide's message (a slot, checked like commentary)."""
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    sl.background.fill.solid()
    sl.background.fill.fore_color.rgb = BG
    SLIDES.append({'key': key, 'title': section_name})
    if key == 'cover':
        return sl
    stext(sl, key, f'{key}.kicker', L, 0.3, 9, 0.22, kicker_sample, 'label',
          f'"{kicker_sample.split(" · ")[0]} · " and the close month, upper case ("{kicker_sample}").', 48, size=10, bold=True, color=TEAL)
    stext(sl, key, f'{key}.title', L, 0.52, W, 0.5, title_sample, 'headline',
          f'The slide\'s message, built from figures on the slide; every dollar in it is on the slide. Falls back to "{section_name}" if it cannot be.',
          74, size=22, bold=True)
    rule(sl, f'{key}.footer_rule', L, 6.98, W, LINE)
    stext(sl, key, f'{key}.footer', L, 7.06, 10.5, 0.22, 'SMPL Demo Co · Board Operating Review · June 2026 · Draft', 'label',
          'Company · "Board Operating Review" · close month · "Draft" while the close is a draft (nothing when approved).', 90, size=9, color=MUTED)
    pn = text(sl, f'{key}.page', R - 0.6, 7.06, 0.6, 0.22, '', size=9, color=MUTED, align=PP_ALIGN.RIGHT)
    p = pn.text_frame.paragraphs[0]._p
    for r in p.findall(qn('a:r')):
        p.remove(r)
    fld = etree.SubElement(p, qn('a:fld'))
    fld.set('id', '{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}')
    fld.set('type', 'slidenum')
    rpr = etree.SubElement(fld, qn('a:rPr'))
    rpr.set('lang', 'en-US')
    rpr.set('sz', '900')
    sf = etree.SubElement(rpr, qn('a:solidFill'))
    etree.SubElement(sf, qn('a:srgbClr')).set('val', '6B8CA8')
    etree.SubElement(rpr, qn('a:latin')).set('typeface', FONT)
    etree.SubElement(fld, qn('a:t')).text = '2'
    return sl



def _el(tag, parent=None, **attrs):
    el = etree.SubElement(parent, qn(tag)) if parent is not None else etree.Element(qn(tag))
    for k_, v_ in attrs.items():
        el.set(k_, str(v_))
    return el


def _num_lit(parent, tag, n_pts):
    lit = _el('c:numLit', _el(tag, parent))
    _el('c:formatCode', lit).text = 'General'
    _el('c:ptCount', lit, val=n_pts)
    return lit


def _pin_chart_font(run, size_pt):
    """Chart labels stay in Calibri. A missing east-asian or complex-script face makes PowerPoint swap the whole run."""
    rpr = run._r.find(qn('a:rPr'))
    if rpr is None:
        return
    rpr.set('sz', str(int(round(size_pt * 100))))
    rpr.set('b', '1')
    for tag in ('a:latin', 'a:ea', 'a:cs'):
        el = rpr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rpr, qn(tag))
        el.set('typeface', FONT)


def waterfall(sl, key, name, x, y, w, h, cats, receives, group, label_size=9):
    """Standard bridge. Boxes stack on an invisible base on the visible axes (value axis in $M with gridlines). Each box's
    amount sits in bold above it. A thin connector runs across each gap, from the right edge of one box to the left edge of
    the next, at the level where one ends and the next begins; it never crosses a box.

    How it is built: the boxes are a stacked column chart. Series: Base (invisible), Increase, Decrease, Total, Label (an
    invisible sliver on top of each column that carries the amount above the box). The connectors are a scatter chart on
    hidden secondary axes, one two-point line per gap. Its horizontal axis runs from 0.5 to the number of boxes plus 0.5,
    so x = 1, 2, 3 ... are the box centres, and each line runs between the box edges. Its vertical axis carries the same
    scale as the visible value axis. The filler sets both scales and the connector points from the data."""
    from pptx.enum.chart import XL_LABEL_POSITION
    n = len(cats)
    ch = add_chart(sl, name, XL_CHART_TYPE.COLUMN_STACKED, x, y, w, h, cats,
                   [('Base', [1] * n), ('Increase', [1] * n), ('Decrease', [1] * n), ('Total', [1] * n), ('Label', [0.1] * n)])
    style_chart(ch)
    style_axes(ch, '"$"#,##0"M"', cat_low=True, gridlines=True)
    pl = ch.plots[0]
    pl.gap_width = 50
    pl.overlap = 100
    s = pl.series
    no_fill_series(s[0])
    fill_series(s[1], GREEN)
    fill_series(s[2], RED)
    fill_series(s[3], TEAL)
    no_fill_series(s[4])
    for i in range(n):
        dl = s[4].points[i].data_label
        dl.text_frame.text = '$0.00M'
        dl.position = XL_LABEL_POSITION.INSIDE_BASE
        r = dl.text_frame.paragraphs[0].runs[0]
        r.font.bold, r.font.size, r.font.name = True, Pt(label_size), FONT
        r.font.color.rgb = WHITE
        _pin_chart_font(r, label_size)
    # connectors: a line chart on hidden secondary axes. lineMarker makes PowerPoint draw the default thick stroke
    # and ignore the width below. The axes stay in the file (not deleted) so the scale is the same rectangle as the columns.
    pa = ch._chartSpace.find('.//' + qn('c:plotArea'))
    bc = pa.find(qn('c:barChart'))
    top_id = max(int(a.find(qn('c:axId')).get('val')) for a in pa.findall(qn('c:valAx')) + pa.findall(qn('c:catAx')))
    id_x, id_y = str(top_id + 11), str(top_id + 12)
    sc = _el('c:scatterChart')
    _el('c:scatterStyle', sc, val='line')
    _el('c:varyColors', sc, val=0)
    for k in range(n - 1):
        ser = _el('c:ser', sc)
        _el('c:idx', ser, val=5 + k)
        _el('c:order', ser, val=5 + k)
        _el('c:v', _el('c:tx', ser)).text = f'Connector {k + 1}'
        ln = _el('a:ln', _el('c:spPr', ser), w=6350, cap='flat', cmpd='sng')
        _el('a:srgbClr', _el('a:solidFill', ln), val=str(SOFT))
        _el('a:prstDash', ln, val='solid')
        marker = _el('c:marker', ser)
        _el('c:symbol', marker, val='none')
        _el('a:noFill', _el('a:ln', _el('c:spPr', marker)))
        _num_lit(ser, 'c:xVal', 2)
        _num_lit(ser, 'c:yVal', 2)
        _el('c:smooth', ser, val=0)
    _el('c:axId', sc, val=id_x)
    _el('c:axId', sc, val=id_y)
    bc.addnext(sc)
    last_ax = [a for a in pa if a.tag in (qn('c:valAx'), qn('c:catAx'))][-1]
    for own, cross, pos, lo, hi in ((id_x, id_y, 'b', 0.5, n + 0.5), (id_y, id_x, 'r', 0, 1)):
        ax = _el('c:valAx')
        _el('c:axId', ax, val=own)
        scl = _el('c:scaling', ax)
        _el('c:orientation', scl, val='minMax')
        _el('c:max', scl, val=hi)
        _el('c:min', scl, val=lo)
        _el('c:delete', ax, val=0)
        _el('c:axPos', ax, val=pos)
        _el('c:numFmt', ax, formatCode='General', sourceLinked=0)
        _el('c:majorTickMark', ax, val='none')
        _el('c:minorTickMark', ax, val='none')
        _el('c:tickLblPos', ax, val='none')
        _el('a:noFill', _el('a:ln', _el('c:spPr', ax)))
        _el('c:crossAx', ax, val=cross)
        _el('c:crosses', ax, val='max' if pos == 'r' else 'autoZero')
        _el('c:crossBetween', ax, val='midCat')
        last_ax.addnext(ax)
        last_ax = ax
    slot(name, key, 'chart', receives, None, group)
    return ch


def grid(sl, key, tkey, x, y, cols, rows, row_h=0.4, head_h=0.34, zebra=True, label_slot=None, row_rules=False, size=11, pad=0.12, gaps=None):
    """cols: [(ckey, width, header, header_slot_receives|None, kind, receives, group, tone)]
    The first col is the row label. rows: [(rkey, label, emphasis)]. gaps: {col index: extra space before it}."""
    gaps = gaps or {}
    cx = x
    xs = []
    for i, c in enumerate(cols):
        cx += gaps.get(i, 0)
        xs.append(cx)
        cx += c[1]
    width = cx - x
    for i, c in enumerate(cols):
        ckey, cw, head, head_slot = c[0], c[1], c[2], c[3]
        al = PP_ALIGN.LEFT if i == 0 else PP_ALIGN.RIGHT
        if head_slot:
            stext(sl, key, f'{key}.{tkey}.h.{ckey}', xs[i] + pad, y, cw - 2 * pad, head_h, head, 'label', head_slot, 22,
                  size=8.5, bold=True, color=MUTED, align=al, anchor=MSO_ANCHOR.MIDDLE)
        else:
            text(sl, f'{key}.{tkey}.h.{ckey}', xs[i] + pad, y, cw - 2 * pad, head_h, head, size=8.5, bold=True, color=MUTED, align=al, anchor=MSO_ANCHOR.MIDDLE)
    rule(sl, f'{key}.{tkey}.h.rule', x, y + head_h, width, LINE, 1.0)
    for j, (rkey, label, emph) in enumerate(rows):
        ry = y + head_h + j * row_h
        if zebra and j % 2 == 1:
            rect(sl, f'{key}.{tkey}.{rkey}.zebra', x, ry, width, row_h, ZEBRA)
        if row_rules:
            rule(sl, f'{key}.{tkey}.{rkey}.rule', x, ry + row_h, width, LINE, 0.5)
        for i, c in enumerate(cols):
            ckey, cw = c[0], c[1]
            al = PP_ALIGN.LEFT if i == 0 else PP_ALIGN.RIGHT
            nm = f'{key}.{tkey}.{rkey}.{ckey}'
            if i == 0:
                if label_slot:
                    stext(sl, key, nm, xs[i] + pad, ry, cw - 2 * pad, row_h, label, 'label', label_slot(rkey), 26,
                          size=size, bold=emph, color=WHITE if emph else SOFT, anchor=MSO_ANCHOR.MIDDLE)
                else:
                    text(sl, nm, xs[i] + pad, ry, cw - 2 * pad, row_h, label, size=size, bold=emph, color=WHITE if emph else SOFT, anchor=MSO_ANCHOR.MIDDLE)
                continue
            kind, receives, group, tone = c[4], c[5], c[6], c[7]
            stext(sl, key, nm, xs[i] + pad, ry, cw - 2 * pad, row_h, '$0.00M', kind, f'{label}: {receives}', 12, group, tone,
                  size=size, bold=emph or tone, color=SOFT if tone else WHITE, align=al, anchor=MSO_ANCHOR.MIDDLE)
    return width


def group_head(sl, key, name, x, w, y, sample, receives, limit=28):
    stext(sl, key, name, x + 0.06, y, w - 0.12, 0.24, sample, 'label', receives, limit,
          size=9.5, bold=True, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    rule(sl, name + '.rule', x + 0.06, y + 0.26, w - 0.12, MUTED, 0.75)


def panel(sl, key, x, y, w, h, heading, limit, size=11, cols=1, receives=None):
    """Commentary panel: a heading and one or two text boxes of paragraphs, each paragraph a bold lead-in and a body.
    With two boxes the filler fills the left box first and splits the paragraphs so the columns balance; a paragraph is never split."""
    rect(sl, f'{key}.notes.bg', x, y, w, h, CARD, LINE)
    text(sl, f'{key}.notes.label', x + 0.24, y + 0.18, w - 0.48, 0.2, heading, size=9.5, bold=True, color=TEAL)
    gap = 0.45
    bw = (w - 0.48 - gap * (cols - 1)) / cols
    for c in range(cols):
        name = f'{key}.notes' if c == 0 else f'{key}.notes.right'
        tb = sl.shapes.add_textbox(Inches(x + 0.24 + c * (bw + gap)), Inches(y + 0.48), Inches(bw), Inches(h - 0.62))
        tb.name = name
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.auto_size = None
        p = tf.paragraphs[0]
        p.space_after = Pt(7)
        p.line_spacing = 1.08
        for t, color, bold in (('Lead-in.', WHITE, True), (' Body of the paragraph.', SOFT, False)):
            r = p.add_run()
            r.text = t
            r.font.name, r.font.size, r.font.bold = FONT, Pt(size), bold
            r.font.color.rgb = color
        lim = limit if cols == 1 else int(limit * 0.6)
        rec = receives or ('Paragraphs, each a bold lead-in and a body: accepted close notes first, then paragraphs built from the figures on this slide. '
                           'Every dollar in it is on this slide; a paragraph that cannot meet that, or does not fit, is left out.')
        if cols > 1:
            rec = ('Left column. ' if c == 0 else 'Right column: the paragraphs after the left column, so the two balance. ') + rec
        slot(name, key, 'commentary', rec, lim)


def para_box(sl, key, name, x, y, w, h, size, limit, receives):
    """A borderless commentary box: paragraphs, each a bold lead-in and a body (the lead may be empty)."""
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.auto_size = None
    p = tf.paragraphs[0]
    p.space_after = Pt(5)
    p.line_spacing = 1.08
    for t, color, bold in (('', WHITE, True), ('Body of the paragraph.', SOFT, False)):
        r = p.add_run()
        r.text = t
        r.font.name, r.font.size, r.font.bold = FONT, Pt(size), bold
        r.font.color.rgb = color
    slot(name, key, 'commentary', receives + ' Every dollar in it is on this slide; a paragraph that cannot meet that, or does not fit, is left out.', limit)
    return tb


def caption(sl, key, name, x, y, w, h, sample, receives, limit, size=9.5, align=PP_ALIGN.LEFT):
    return stext(sl, key, name, x, y, w, h, sample, 'caption', receives, limit, size=size, color=SOFT, align=align)


def label_line(sl, key, name, x, y, w, sample, receives, limit=60):
    return stext(sl, key, name, x, y, w, 0.22, sample, 'label', receives, limit, size=9.5, bold=True, color=TEAL)


def data_labels(series, fmt='"$"#,##0.00"M"', pos=None, size=9, color=WHITE):
    dl = series.data_labels
    dl.number_format = fmt
    dl.number_format_is_linked = False
    dl.show_value = True
    dl.show_category_name = False
    dl.show_series_name = False
    if pos is not None:
        dl.position = pos
    dl.font.size = Pt(size)
    dl.font.name = FONT
    dl.font.color.rgb = color


# ------------------------------------------------------------------ slides
def build(out_pptx, out_slots):
    from pptx.enum.chart import XL_LABEL_POSITION, XL_MARKER_STYLE
    from pptx.enum.dml import MSO_LINE_DASH_STYLE
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    PM, PY = 'plan_m', 'plan_ytd'
    TOP = 1.22

    # 1 ---------------------------------------------------------------- cover
    sl = new_slide(prs, 'cover', 'Cover', '', '')
    rect(sl, 'cover.accent', L, 2.35, 0.08, 2.3, TEAL)
    text(sl, 'cover.title', L + 0.35, 2.3, 10, 0.8, 'Board Operating Review', size=44, bold=True)
    stext(sl, 'cover', 'cover.period', L + 0.35, 3.15, 10, 0.5, 'June 2026 close · Q2 2026', 'label',
          'Close month and year, then the quarter it closes in ("June 2026 close · Q2 2026").', 40, size=22, color=TEAL)
    stext(sl, 'cover', 'cover.company', L + 0.35, 3.75, 10, 0.45, 'SMPL Demo Co', 'label', 'Company name.', 48, size=20, color=SOFT)
    rect(sl, 'cover.status.bg', L + 0.35, 4.4, 1.5, 0.38, CARD, LINE, MSO_SHAPE.ROUNDED_RECTANGLE)
    stext(sl, 'cover', 'cover.status', L + 0.35, 4.4, 1.5, 0.38, 'Draft', 'status', '"Draft" or "Approved", from the close status.', 10,
          size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(sl, 'cover.confidential', L + 0.35, 6.75, 6, 0.25, 'Confidential', size=10, color=MUTED)

    # 2 ---------------------------------------------------------------- executive dashboard: tiles, matrix, takeaways
    key = 'dash'
    sl = new_slide(prs, key, 'Executive dashboard', 'EXECUTIVE DASHBOARD · JUNE 2026', 'ARR, revenue, gross margin and EBITDA under budget; cash $3.85M ahead')
    tw, gap = (W - 4 * 0.15) / 5, 0.15
    tiles = [('arr', 'ENDING ARR', '$81.72M', 'Ending ARR', 'amount'), ('rev', 'REVENUE · MONTH', '$7.40M', 'Revenue for the month', 'amount'),
             ('cash', 'ENDING CASH', '$30.00M', 'Ending cash', 'amount'), ('gm', 'GROSS MARGIN · MONTH', '85.3%', 'Gross margin for the month', 'pct'),
             ('ebitda', 'EBITDA · MONTH', '$984.5K', 'EBITDA for the month', 'amount')]
    for i, (m, lab, v, rec, kind) in enumerate(tiles):
        tile(sl, key, m, L + i * (tw + gap), TOP, tw, 1.12, lab, v, 'Budget $84.89M', '−3.7%', rec, kind, PM, value_size=24)
    lw, nw, g = 1.38, 0.8, 0.16
    cols = [('label', lw, 'Measure', None)]
    for grp, gl, gg in (('m', 'month', PM), ('ytd', 'year to date', PY)):
        cols += [(f'{grp}_act', nw, 'Actual', None, 'amount', f'actual, {gl}.', None, False),
                 (f'{grp}_plan', nw, 'Budget', f'Plan label, capitalised, {gl}.', 'amount', f'plan, {gl}.', gg, False),
                 (f'{grp}_var', nw, 'vs budget', f'"vs " and the plan label, {gl}.', 'amount', f'actual less plan, {gl} ($; points for margin).', gg, True),
                 (f'{grp}_ly', nw, 'vs LY', f'"vs " and last year\'s period ("vs June 2025", "vs 2025 YTD"), {gl}.', 'pct',
                  f'change on the same period last year, {gl} (percent; points for margin; "—" for ARR and cash, which the close does not carry for last year).', 'ly', True)]
    rows = [('arr', 'Ending ARR', False), ('rev', 'Revenue', False), ('gm', 'Gross margin', False), ('ebitda', 'EBITDA', False),
            ('ni', 'Net income', False), ('cash', 'Ending cash', False)]
    my = 2.62
    group_head(sl, key, 'dash.mx.g.m', L + lw, 4 * nw, my, 'June 2026', 'Close month and year.')
    group_head(sl, key, 'dash.mx.g.ytd', L + lw + 4 * nw + g, 4 * nw, my, '2026 YTD · Jan–Jun', 'Fiscal year and the months in the year to date.')
    mw = grid(sl, key, 'mx', L, my + 0.32, cols, rows, row_h=0.5, head_h=0.3, size=10.5, pad=0.07, gaps={5: g})
    px = L + mw + 0.3
    panel(sl, key, px, my, R - px, 6.85 - my, 'KEY TAKEAWAYS', 900, size=11)

    # 3 ---------------------------------------------------------------- ARR: budget-to-actual net new, by period, customers behind the month
    key = 'arr'
    sl = new_slide(prs, key, 'ARR', 'ARR · JUNE 2026', 'Net new ARR at 63.3% of budget: new business short, churn well below plan')
    lw_ = 7.4
    label_line(sl, key, 'arr.bridge.label', L, TOP, lw_, 'NET NEW ARR · BUDGET TO ACTUAL · JUNE', '"NET NEW ARR · " plan label " TO ACTUAL · " close month, upper case.', 60)
    ch = waterfall(sl, key, 'arr.bridge', L, TOP + 0.24, lw_, 2.62,
              ['Budget', 'New business', 'Expansion and reactivation', 'Churn and contraction', 'Actual'],
              'Five categories: the planned net new ARR (named with the plan label), the gap in new business, in expansion and reactivation, and in churn '
              'and contraction (positive when losses were lower than planned), then actual net new ARR. Bars in $ millions; the plan bar is grey. '
              'Each bar\'s amount is written in bold above it; a thin line crosses each gap from the edge of one bar to the edge of the next, at the level where one ends and the next begins; value axis in $ millions with gridlines.', 'arr')
    tp = [p_ for p_ in ch.plots if type(p_).__name__ == 'BarPlot'][0].series[3].points[0]
    tp.format.fill.solid()
    tp.format.fill.fore_color.rgb = PLAN
    px = L + lw_ + 0.3
    pw_ = R - px
    lw2, nw2 = 1.2, (pw_ - 1.2 - 0.2) / 6
    for gi, (g, sample) in enumerate((('g1', 'June'), ('g2', 'Q2'), ('g3', 'H1'))):
        group_head(sl, key, f'arr.p.{g}', px + lw2 + gi * (2 * nw2 + 0.1), 2 * nw2, TOP + 0.24, sample,
                   'The periods this close reads, in order: the month, then the quarter (or quarter to date) when it differs from the month and the year to date, '
                   'then the year to date ("H1" at the half, "Full year" at year end). Groups fill left to right; unused groups are blank.', 24)
    cols = [('label', lw2, 'Net new ARR', None)]
    for g, gg in (('g1', 'plan_m'), ('g2', 'period'), ('g3', 'period')):
        cols += [(f'{g}_act', nw2, 'Actual', '"Actual"; blank when the group has no period.', 'amount', f'actual for the period ({g}); churn and contraction shown as a positive amount lost.', 'period' if g != 'g1' else None, False),
                 (f'{g}_pct', nw2, '% of budget', '"% of " and the plan label.', 'pct', f'actual as a share of plan for the period ({g}).', gg, False)]
    rows = [('nb', 'New business', False), ('ex', 'Expansion', False), ('loss', 'Churn and contraction', False), ('nn', 'Net new ARR', True)]
    grid(sl, key, 'p', px, TOP + 0.56, cols, rows, row_h=0.4, head_h=0.28, size=9, pad=0.04, gaps={3: 0.1, 5: 0.1})
    caption(sl, key, 'arr.p.note', px, TOP + 0.56 + 0.28 + 4 * 0.4 + 0.1, pw_, 0.42,
            'Ending ARR $81.72M against $84.89M budget, −$3.17M. Gross retention 100.0% against 98.9%.',
            'Ending ARR against plan and the gap; gross retention for the month against plan.', 130, size=9.5)
    cy = TOP + 0.24 + 2.62 + 0.18
    text(sl, 'arr.c.label', L, cy, lw_, 0.22, 'CUSTOMERS BEHIND THE MONTH', size=9.5, bold=True, color=TEAL)
    cols = [('label', 3.3, 'Customer', None),
            ('what', 2.5, 'What happened', 'Header (static wording).', 'label', 'what happened: "New customer", "Expansion", "Churned", "Contracted", "Slipped to July".', 'customers', False),
            ('arr', lw_ - 5.8, 'ARR', None, 'amount', 'ARR of the movement (slipped deals: the deal\'s ARR).', 'customers', False)]
    rows = [(f'c{n}', f'Customer {n}', False) for n in range(1, 10)]
    grid(sl, key, 'c', L, cy + 0.24, cols, rows, row_h=(6.85 - cy - 0.24 - 0.26) / 9, head_h=0.26, zebra=False, row_rules=True, size=9.5, pad=0.07,
         label_slot=lambda rk: 'Customer name: the three largest new customers, the two largest expansions, the largest churn and contraction, '
                               'the two largest deals that slipped; blank (row and rule hidden) when there are fewer.')
    panel(sl, key, px, cy, pw_, 6.85 - cy, 'KEY TAKEAWAYS', 700, size=10)
    for s_ in SLOTS:
        if s_['name'].startswith('arr.c.c') and s_['name'].endswith('.what'):
            s_['max_chars'] = 26

    # 4 ---------------------------------------------------------------- P&L: by period, the rest of the year, takeaways
    key = 'pnl'
    sl = new_slide(prs, key, 'P&L', 'P&L · JUNE 2026', 'H1 EBITDA $1.26M under budget; the outlook adds $2.56M more in H2')
    lw3, aw, cw_, g3 = 1.42, 0.92, 0.84, 0.12
    xs_ = [L + lw3, L + lw3 + aw + cw_ + g3, L + lw3 + 2 * (aw + cw_ + g3)]
    for g, sample, w_, rec in (('g1', 'June', aw + cw_, 'The close month.'), ('g2', 'Q2', aw + cw_, 'The quarter; blank when it would repeat the month or the year to date.'),
                               ('g3', 'H1', aw + 2 * cw_, 'The year to date ("H1" at the half); blank in the first month.')):
        group_head(sl, key, f'pnl.p.{g}', xs_[int(g[1]) - 1], w_, TOP, sample, rec, 24)
    cols = [('label', lw3, 'Measure', None),
            ('g1_act', aw, 'Actual', None, 'amount', 'actual, close month.', None, False),
            ('g1_cmp', cw_, 'vs budget', '"vs " and the plan label.', 'amount', 'actual less plan, close month ($; points for margins).', 'plan_m', True),
            ('g2_act', aw, 'Actual', '"Actual"; blank when there is no quarter view.', 'amount', 'actual, quarter.', 'period', False),
            ('g2_cmp', cw_, 'vs Q1', '"vs " and the prior quarter ("vs Q1").', 'pct', 'change on the prior quarter (percent; points for margins).', 'period', True),
            ('g3_act', aw, 'Actual', '"Actual"; blank in the first month.', 'amount', 'actual, year to date.', 'period', False),
            ('g3_cmp', cw_, 'vs budget', '"vs " and the plan label.', 'amount', 'actual less plan, year to date ($; points for margins).', 'plan_ytd', True),
            ('g3_ly', cw_, 'vs H1 2025', '"vs " and last year\'s same period ("vs H1 2025").', 'pct', 'change on the same period last year (percent; points for margins).', 'ly', True)]
    rows = [('rev', 'Revenue', True), ('gm', 'Gross margin', False), ('ebitda', 'EBITDA', True), ('em', 'EBITDA margin', False), ('ni', 'Net income', False)]
    tw4 = grid(sl, key, 'p', L, TOP + 0.32, cols, rows, row_h=0.42, head_h=0.28, size=10, pad=0.06, gaps={3: g3, 5: g3})
    ry = TOP + 0.32 + 0.28 + 5 * 0.42 + 0.22
    cwh = (tw4 - 0.3) / 2
    for i, (m, nm) in enumerate((('rev', 'REVENUE'), ('ebitda', 'EBITDA'))):
        x = L + i * (cwh + 0.3)
        label_line(sl, key, f'pnl.{m}.ry.label', x, ry, cwh, f'{nm} · THE REST OF THE YEAR', f'"{nm} · THE REST OF THE YEAR" (static wording kept as a slot for other languages).', 48)
        ch = add_chart(sl, f'pnl.{m}.ry', XL_CHART_TYPE.COLUMN_CLUSTERED, x, ry + 0.22, cwh, 2.0, ['H1 actual', 'H2 outlook', 'FY 2026 outlook'],
                       [('Actual and outlook', [1, 1, 1]), ('Budget', [1, 1, 1])])
        style_chart(ch, legend=(i == 0))
        style_axes(ch, '"$"#,##0"M"', cat_low=True, gridlines=False)
        ch.value_axis.visible = False
        ch.plots[0].gap_width, ch.plots[0].overlap = 60, -5
        fill_series(ch.plots[0].series[0], TEAL)
        fill_series(ch.plots[0].series[1], PLAN)
        for s in ch.plots[0].series:
            data_labels(s, pos=XL_LABEL_POSITION.OUTSIDE_END, size=8.5, color=WHITE)
        slot(f'pnl.{m}.ry', key, 'chart', f'{"Revenue" if m == "rev" else "EBITDA"} for the months closed (actual), the months open (outlook) and the full year (outlook), each against plan; '
             'categories carry the period names from the close date; $ millions, labelled.', None, 'outlook')
        caption(sl, key, f'pnl.{m}.ry.note', x, ry + 2.24, cwh, 0.3, 'H1 −$621.0K · H2 −$2.73M · Full year −$3.35M against budget',
                'The gap to plan for the months closed, the months open and the full year.', 90, size=9)
    px = L + tw4 + 0.3
    panel(sl, key, px, TOP, R - px, 6.85 - TOP, 'KEY TAKEAWAYS', 1500, size=10.5)

    # 5 ---------------------------------------------------------------- people: headcount bridge, departments, labor cost against budget
    key = 'people'
    sl = new_slide(prs, key, 'People', 'PEOPLE · JUNE 2026', '130 people at June, 5 fewer than budget; labor cost $149.1K under budget')
    arrow_w, grp_gap, box_gap = 0.32, 0.45, 0.14
    bw = (W - 3 * arrow_w - grp_gap - 2 * box_gap) / 7
    flow = [('open', 'MAY CLOSE', '129', 'Opening heads', 'Heads at the prior month end; label is the prior month, upper case ("MAY CLOSE").'),
            ('hires', 'HIRES', '+2', 'Engineering, G&A', 'Hires in the month; the sub-line names the departments (or counts them when more than two).'),
            ('departures', 'DEPARTURES', '−1', 'Sales', 'Departures in the month; the sub-line names the departments.'),
            ('close', 'JUNE CLOSE', '130', 'Net +1 in the month', 'Heads at the close; label is the close month, upper case. Sub-line: net change (transfers between departments net to zero).'),
            ('plan', 'JUNE BUDGET', '135', '5 more than actual', 'Budgeted heads at the close; label is the close month and the plan label. Sub-line: the gap to actual.'),
            ('ye_plan', 'DECEMBER BUDGET', '152', '+22 from today', 'Budgeted heads at the fiscal year end; sub-line: the change from the close.'),
            ('ye_outlook', 'DECEMBER OUTLOOK', '268', '+138 from today', 'Year-end heads in the full-year outlook; sub-line: the change from the close. Blank when no outlook heads are loaded.')]
    x = L
    for i, (m, lab, v, sub, rec) in enumerate(flow):
        hl = m in ('close',)
        rect(sl, f'people.{m}.bg', x, TOP, bw, 1.02, CARD, TEAL if hl else LINE)
        stext(sl, key, f'people.{m}.label', x + 0.14, TOP + 0.12, bw - 0.28, 0.2, lab, 'label', rec, 22, size=8.5, bold=True, color=TEAL if hl else MUTED)
        stext(sl, key, f'people.{m}.value', x + 0.14, TOP + 0.3, bw - 0.28, 0.44, v, 'count', rec.split(';')[0].split('.')[0] + ' (a count).', 8,
              size=26, bold=True, anchor=MSO_ANCHOR.MIDDLE)
        stext(sl, key, f'people.{m}.sub', x + 0.14, TOP + 0.74, bw - 0.28, 0.22, sub, 'caption', rec, 30, size=9, color=SOFT)
        x += bw
        if i < 3:
            text(sl, f'people.arrow{i + 1}', x, TOP + 0.26, arrow_w, 0.5, '→', size=20, bold=True, color=MUTED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            x += arrow_w
        elif i == 3:
            x += grp_gap
        else:
            x += box_gap
    ty = TOP + 1.18
    text(sl, 'people.t.label', L, ty, 5, 0.22, 'BY DEPARTMENT', size=9.5, bold=True, color=TEAL)
    cols = [('label', 1.72, 'Department', None),
            ('open', 0.62, 'May', 'Prior month, short ("May").', 'count', 'heads at the prior month end.', 'people', False),
            ('hires', 0.62, 'Hires', None, 'count', 'hires in the month.', 'people', False),
            ('departures', 0.86, 'Departures', None, 'count', 'departures in the month.', 'people', False),
            ('close', 0.62, 'June', 'Close month, short ("June").', 'count', 'heads at the close.', 'people', False),
            ('plan', 0.7, 'Budget', 'Plan label, capitalised.', 'count', 'budgeted heads at the close.', 'people_plan', False),
            ('var', 0.78, 'vs budget', '"vs " and the plan label.', 'count', 'heads less budgeted heads (signed, not coloured: fewer heads saves cost but means less capacity).', 'people_plan', False),
            ('cost', 0.95, 'Labor cost', None, 'amount', 'labor cost for the month (salaries, payroll taxes, benefits, retirement match, bonus, commissions; excludes stock-based compensation).', None, False),
            ('cost_var', 0.95, 'vs budget', '"vs " and the plan label.', 'amount', 'labor cost less plan; green below plan, red above.', 'plan_m', True)]
    rows = [(f'd{n}', f'Department {n}', False) for n in range(1, 9)] + [('total', 'All departments', True)]
    tw_ = grid(sl, key, 't', L, ty + 0.24, cols, rows, row_h=0.234, head_h=0.28, zebra=False, row_rules=True, size=9.5, pad=0.07,
               label_slot=lambda rk: ('Department name, largest payroll first; blank (row and rule hidden) when the close has fewer departments.'
                                      if rk != 'total' else '"All departments".'))
    cx = L + tw_ + 0.35
    label_line(sl, key, 'people.chart.label', cx, ty, R - cx, 'LABOR COST AGAINST BUDGET · JUNE 2026',
               '"LABOR COST AGAINST " plan label " · " close month, upper case.', 52)
    ch = add_chart(sl, 'people.chart', XL_CHART_TYPE.BAR_STACKED, cx, ty + 0.24, R - cx, 2.05,
                   ['Heads vs budget', 'Pay rate and mix', 'Taxes and benefits', 'Variable pay'], [('Above budget', [1] * 4), ('Below budget', [1] * 4)])
    style_chart(ch, legend=False)
    style_axes(ch, '"$"#,##0"K";"−$"#,##0"K";"$0"', cat_low=True)
    ch.category_axis.reverse_order = True
    ch.plots[0].gap_width, ch.plots[0].overlap = 55, 100
    fill_series(ch.plots[0].series[0], RED)
    fill_series(ch.plots[0].series[1], GREEN)
    slot('people.chart', key, 'chart', 'Four categories, each the driver and its effect on labor cost against plan ("Heads vs budget −$88.0K"): fewer or more heads than plan at '
         'plan pay, pay rate and mix (the rest of salaries), payroll taxes and benefits, variable pay (bonus and commissions). Series: above plan (red), below plan (green), '
         '$ thousands. They add to the labor-cost gap in the caption.', None, 'plan_m')
    caption(sl, key, 'people.chart.note', cx, ty + 2.32, R - cx, 0.42,
            'Labor cost $3.54M against $3.69M budget, −$149.1K. Excludes stock-based compensation ($392.3K).',
            'Labor cost against plan and the gap; stock-based compensation, which the figures exclude.', 140, size=9)
    panel(sl, key, L, 5.16, W, 6.85 - 5.16, 'KEY TAKEAWAYS', 1100, size=10, cols=2)

    # 5 ---------------------------------------------------------------- cash: waterfall and table (kept), takeaways below
    key = 'cash'
    sl = new_slide(prs, key, 'Cash', 'CASH · JUNE 2026', 'Cash $30.00M, $3.85M ahead of budget')
    text(sl, 'cash.chart.label', L, TOP, 6, 0.22, 'MONTHLY CASH BRIDGE · ACTUAL', size=9.5, bold=True, color=TEAL)
    waterfall(sl, key, 'cash.chart', L, TOP + 0.24, 6.55, 3.36,
              ['Beginning', 'Collections', 'Payroll', 'Vendors', 'Commissions', 'Capex', 'Other, net', 'Ending'],
              'Eight categories, the line names. Bars in $ millions; each bar\'s actual amount is written in bold above it ("+$6.85M"); a thin line crosses each gap from the edge of one bar to the edge of the next, at the level where one ends and the next begins; value axis in $ millions with gridlines.', 'cash')
    tx = L + 6.85
    cols = [('label', 1.75, 'Line', None),
            ('act', 1.2, 'Actual', None, 'amount', 'actual for the month (outflows negative).', None, False),
            ('plan', 1.2, 'Budget', 'Plan label, capitalised.', 'amount', 'plan for the month (outflows negative).', PM, False),
            ('var', R - tx - 4.15, 'vs budget', '"vs " and the plan label.', 'amount', 'actual less plan; effect on cash.', PM, True)]
    rows = [('beginning', 'Beginning cash', True), ('collections', 'Collections', False), ('payroll', 'Payroll', False), ('vendors', 'Vendors', False),
            ('commissions', 'Commissions', False), ('capex', 'Capex', False), ('other', 'Other, net', False), ('net_change', 'Net change', True),
            ('ending', 'Ending cash', True)]
    grid(sl, key, 't', tx, TOP + 0.24, cols, rows, row_h=0.35, head_h=0.3)
    panel(sl, key, L, 4.98, W, 6.85 - 4.98, 'KEY TAKEAWAYS', 950, size=11, cols=2)

    # 6 ---------------------------------------------------------------- go to market: by period, spend by channel, takeaways
    key = 'gtm'
    sl = new_slide(prs, key, 'Go to market', 'GO TO MARKET · JUNE 2026', 'H1 spend 9.0% over budget for 10.4% fewer MQLs')
    lw4, aw4, cw4 = 1.8, 0.92, 0.86
    for gi, (g, sample) in enumerate((('g1', 'June'), ('g2', 'Q2'), ('g3', 'H1'))):
        group_head(sl, key, f'gtm.p.{g}', L + lw4 + gi * (aw4 + cw4 + 0.12), aw4 + cw4, TOP, sample,
                   'The periods this close reads, in order: the month, the quarter when it differs from the month and the year to date, then the year to date. '
                   'Groups fill left to right; unused groups are blank.', 24)
    cols = [('label', lw4, 'Measure', None)]
    for g, gg in (('g1', 'gtm_plan'), ('g2', 'period'), ('g3', 'period')):
        cols += [(f'{g}_act', aw4, 'Actual', '"Actual"; blank when the group has no period.', 'amount', f'actual for the period ({g}); counts for MQLs and opportunities.', None if g == 'g1' else 'period', False),
                 (f'{g}_cmp', cw4, 'vs budget', '"vs " and the plan label.', 'pct', f'actual against plan, percent ({g}); red when spend runs over or volume under.', gg, True)]
    rows = [('spend', 'Marketing spend', True), ('mql', 'MQLs', False), ('cpm', 'Spend per MQL', False), ('opp', 'Opportunities created', False),
            ('created', 'Pipeline created', True)]
    tw6 = grid(sl, key, 'p', L, TOP + 0.32, cols, rows, row_h=0.44, head_h=0.28, size=10, pad=0.06, gaps={3: 0.12, 5: 0.12})
    cx = L + tw6 + 0.35
    label_line(sl, key, 'gtm.chart.label', cx, TOP, R - cx, 'SPEND BY CHANNEL · Q2 · ACTUAL AND BUDGET',
               '"SPEND BY CHANNEL · " the quarter (or the month when there is no quarter view) " · ACTUAL AND " plan label, upper case.', 60)
    ch = add_chart(sl, 'gtm.chart', XL_CHART_TYPE.BAR_CLUSTERED, cx, TOP + 0.24, R - cx, 2.66,
                   ['Channel 1', 'Channel 2', 'Channel 3'], [('Spend', [1, 1, 1]), ('Budget', [1, 1, 1])])
    style_chart(ch, legend=True)
    style_axes(ch, '"$"#,##0"K"', cat_low=False)
    ch.category_axis.reverse_order = True
    ch.plots[0].gap_width, ch.plots[0].overlap = 45, -5
    fill_series(ch.plots[0].series[0], TEAL)
    fill_series(ch.plots[0].series[1], PLAN)
    slot('gtm.chart', key, 'chart', 'One category per channel that exists in the close, for the quarter (or the month). Series: spend and plan, $ thousands.', None, 'gtm')
    panel(sl, key, L, 4.3, W, 6.85 - 4.3, 'KEY TAKEAWAYS', 1100, size=10.5, cols=2)

    # 7 ---------------------------------------------------------------- pipeline: wide waterfall, table and takeaways below
    key = 'pipe'
    sl = new_slide(prs, key, 'Pipeline', 'PIPELINE · JUNE 2026', 'Pipeline created at 43.7% of budget; the month ends with $4.24M')
    text(sl, 'pipe.chart.label', L, TOP, 6, 0.22, 'PIPELINE BRIDGE · ACTUAL', size=9.5, bold=True, color=TEAL)
    waterfall(sl, key, 'pipe.chart', L, TOP + 0.24, W, 2.75,
              ['Beginning', 'Created', 'Closed won', 'Closed lost', 'Slipped', 'Ending'],
              'Six categories, the line names. Bars in $ millions; each bar\'s actual amount is written in bold above it; a thin line crosses each gap from the edge of one bar to the edge of the next, at the level where one ends and the next begins; value axis in $ millions with gridlines.', 'pipeline')
    by = TOP + 0.24 + 2.75 + 0.2
    cols = [('label', 2.35, 'Component', None),
            ('act', 1.2, 'Actual', None, 'amount', 'actual for the month (outflows negative); the win rate in percent.', None, False),
            ('plan', 1.2, 'Budget', 'Plan label, capitalised.', 'amount', 'plan for the month (outflows negative).', PM, False),
            ('share', 1.2, '% of budget', '"% of " and the plan label.', 'pct', 'actual as a share of plan.', PM, False)]
    rows = [('beginning', 'Beginning pipeline', True), ('created', 'Created', False), ('closed_won', 'Closed won', False),
            ('closed_lost', 'Closed lost', False), ('slipped', 'Slipped', False), ('ending', 'Ending pipeline', True),
            ('win_rate', 'Win rate (won ÷ won and lost)', False)]
    tw_ = grid(sl, key, 't', L, by, cols, rows, row_h=(6.85 - by - 0.3) / 7, head_h=0.3, size=10.5)
    px = L + tw_ + 0.3
    panel(sl, key, px, by, R - px, 6.85 - by, 'KEY TAKEAWAYS', 900, size=10.5)

    # 8 ---------------------------------------------------------------- where the year is heading: four small charts, takeaways below
    key = 'year'
    sl = new_slide(prs, key, 'Where the year is heading', 'FULL YEAR · JUNE 2026', 'Full-year outlook: revenue $3.35M and EBITDA $3.82M short of budget')
    cw4, g4 = (W - 3 * 0.22) / 4, 0.22
    minis = [('rev', 'REVENUE · FY 2026', 'flow'), ('ebitda', 'EBITDA · FY 2026', 'flow'),
             ('arr', 'ENDING ARR · FY 2026', 'balance'), ('cash', 'ENDING CASH · FY 2026', 'balance')]
    for i, (m, lab, kind) in enumerate(minis):
        x = L + i * (cw4 + g4)
        rect(sl, f'year.{m}.bg', x, TOP, cw4, 3.36, CARD, LINE)
        label_line(sl, key, f'year.{m}.label', x + 0.16, TOP + 0.12, cw4 - 0.32, lab, f'The measure and the fiscal year ("{lab}").', 34)
        if kind == 'flow':
            cats, ser = ['Outlook', 'Budget'], [('Jan–Jun actual', [1, None]), ('Jul–Dec outlook', [1, None]), ('Budget', [None, 2])]
            rec = ('Two categories, outlook and plan (named with the plan label). Series: months closed (actual), months open (outlook), plan; '
                   'stacked, $ millions, labelled. Series names carry the month ranges ("Jan–Jun actual", "Jul–Dec outlook").')
        else:
            cats, ser = ['Jun 2026', 'Dec outlook', 'Dec budget'], [('Actual', [1, None, None]), ('Outlook', [None, 1, None]), ('Budget', [None, None, 1])]
            rec = 'Three categories: the close month end, the year-end outlook and the year-end plan. One series each, $ millions, labelled.'
        ch = add_chart(sl, f'year.{m}.chart', XL_CHART_TYPE.COLUMN_STACKED, x + 0.08, TOP + 0.38, cw4 - 0.16, 2.2, cats, ser)
        style_chart(ch, legend=False)
        style_axes(ch, '"$"#,##0"M"', cat_low=True, gridlines=False)
        ch.value_axis.visible = False
        ch.plots[0].gap_width, ch.plots[0].overlap = 55, 100
        cols3 = [TEAL, RGBColor(0x0A, 0x7F, 0x6A), PLAN] if kind == 'flow' else [TEAL, RGBColor(0x0A, 0x7F, 0x6A), PLAN]
        for s, c in zip(ch.plots[0].series, cols3):
            fill_series(s, c)
            data_labels(s, pos=XL_LABEL_POSITION.CENTER, size=9)
        slot(f'year.{m}.chart', key, 'chart', rec, None, 'outlook')
        caption(sl, key, f'year.{m}.note', x + 0.16, TOP + 2.6, cw4 - 0.32, 0.72,
                'Outlook $89.81M · Budget $93.16M · −$3.35M (−3.6%) · Jan–Jun $42.91M · Jul–Dec $46.90M · budget needs $50.25M',
                'Outlook and plan with the gap; for revenue and EBITDA also the months closed, the months open and what the open months need to reach plan; for balances, the change still to come.', 170, size=9)
    caption(sl, key, 'year.gm', L, TOP + 3.44, W, 0.24, 'Gross margin: Jan–Jun 85.1% · Jul–Dec outlook 85.1% · FY outlook 85.1% · Budget 85.6%',
            'Gross margin for the months closed, the months open, the full-year outlook and plan.', 120, size=9.5)
    panel(sl, key, L, 4.98, W, 6.85 - 4.98, 'KEY TAKEAWAYS', 1100, size=10.5, cols=2)

    # 9 ---------------------------------------------------------------- appendix: P&L detail
    key = 'pnlx'
    sl = new_slide(prs, key, 'P&L detail, month and year to date', 'APPENDIX · JUNE 2026', 'P&L detail, month and year to date')
    lw, nw, g = 2.45, 0.98, 0.2
    cols = [('label', lw, '$', None)]
    for grp, gl, gg in (('m', 'month', PM), ('ytd', 'year to date', PY)):
        cols += [(f'{grp}_act', nw, 'Actual', None, 'amount', f'actual, {gl}.', None, False),
                 (f'{grp}_plan', nw, 'Budget', f'Plan label, capitalised, {gl}.', 'amount', f'plan, {gl}.', gg, False),
                 (f'{grp}_var', nw, 'vs budget', f'"vs " and the plan label, {gl}.', 'amount', f'effect on profit against plan, {gl} ($; points for margins).', gg, True),
                 (f'{grp}_ly', nw, 'June 2025', f'Last year\'s period ("June 2025", "2025 YTD").', 'amount', f'same period last year, {gl}.', 'ly', False),
                 (f'{grp}_yoy', nw, 'YoY', None, 'pct', f'change on last year, {gl} (percent; points for margins).', 'ly', True)]
    rows = [('rev', 'Revenue', True), ('cogs', 'Cost of revenue', False), ('gp', 'Gross profit', True), ('gm', 'Gross margin', False),
            ('sm', 'Sales and marketing', False), ('rd', 'Research and development', False), ('ga', 'General and administrative', False),
            ('opex', 'Operating expenses', False), ('ebitda', 'EBITDA', True), ('em', 'EBITDA margin', False),
            ('below', 'D&A, interest and tax', False), ('ni', 'Net income', True)]
    group_head(sl, key, 'pnlx.t.g.m', L + lw, 5 * nw, TOP, 'June 2026', 'Close month and year.')
    group_head(sl, key, 'pnlx.t.g.ytd', L + lw + 5 * nw + g, 5 * nw, TOP, '2026 YTD · Jan–Jun', 'Fiscal year and the months in the year to date.')
    grid(sl, key, 't', L, TOP + 0.32, cols, rows, row_h=0.42, head_h=0.32, size=10.5, pad=0.08, gaps={6: g})

    # 10 --------------------------------------------------------------- appendix: YTD cash flow (kept)
    key = 'cf'
    sl = new_slide(prs, key, 'Cash flow, year to date', 'APPENDIX · JUNE 2026', 'Cash flow, year to date')
    cols = [('label', 3.6, 'Line', None),
            ('act', 2.0, '2026 YTD actual', 'Fiscal year, "2026 YTD actual".', 'amount', 'year-to-date actual.', 'cf_ytd', False),
            ('plan', 2.0, '2026 YTD budget', 'Fiscal year and plan label, "2026 YTD budget".', 'amount', 'year-to-date plan.', 'cf_ytd_plan', False),
            ('var', 2.0, 'vs budget', '"vs " and the plan label.', 'amount', 'actual less plan; effect on cash.', 'cf_ytd_plan', True)]
    rows = [('beginning', 'Beginning cash', True), ('net_income', 'Net income', False), ('da', 'Depreciation and amortization', False),
            ('sbc', 'Stock-based compensation', False), ('ar', 'Accounts receivable', False), ('deferred_revenue', 'Deferred revenue', False),
            ('ap', 'Accounts payable', False), ('prepaids', 'Prepaid expenses', False), ('deferred_commissions', 'Deferred commissions', False),
            ('other', 'Other operating, net', False), ('cfo', 'Cash from operations', True), ('capex', 'Capital expenditures', False),
            ('cff', 'Financing', False), ('net_change', 'Net change in cash', True), ('ending', 'Ending cash', True)]
    grid(sl, key, 't', L, TOP, cols, rows, row_h=0.355, head_h=0.34, size=10.5)

    prs.save(out_pptx)
    json.dump({'slides': SLIDES, 'slots': SLOTS}, open(out_slots, 'w'), indent=1)
    print('slides', len(SLIDES), 'slots', len(SLOTS))


if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2])
