"""
analysis/charts.py - small inline SVG charts (no JavaScript library, no internet, prints cleanly).

Encoding used everywhere (one hue only, so it is colour-blind safe):
  bar          = actual (ERP outturn)            blue  #2a78d6
  black tick   = target (HQ / RB pro-rata / ...)
  light band   = RB annual target (where shown)
Every mark carries a <title>, so hovering shows the exact numbers.
"""
from html import escape

ACT = "#2a78d6"
OWN = "#eb6834"          # our own shop, where a chart highlights it (palette slot 2, validated with slot 1)
TGT = "#0b0b0b"
BAND = "#e8e7e2"
GRID = "#e1e0dc"
INK = "#52514e"
INK1 = "#1d2430"


def _t(s):
    return escape(str(s))


def _pct(a, t):
    return f"{round(100 * a / t)}%" if t else "—"


def bullets(rows, title_note=""):
    """rows: [{label, actual, target, band (optional), note (optional)}] -> horizontal bullet chart.
    Bar = actual, tick = target, light band = band (e.g. RB annual)."""
    rows = [r for r in rows if r.get("actual") is not None]
    if not rows:
        return ""
    lw, bw, rh, pad = 170, 430, 30, 8
    vmax = max([r["actual"] for r in rows] + [r.get("target") or 0 for r in rows] + [r.get("band") or 0 for r in rows] + [1])
    sx = lambda v: lw + (v / vmax) * bw
    h = len(rows) * rh + 28
    out = [f'<svg class="chart" viewBox="0 0 {lw + bw + 200} {h}" role="img" aria-label="Actual against target">']
    for k in range(5):
        x = lw + bw * k / 4
        out.append(f'<line x1="{x:.1f}" y1="4" x2="{x:.1f}" y2="{h - 22}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{h - 8}" font-size="10" fill="{INK}" text-anchor="middle">{round(vmax * k / 4)}</text>')
    for i, r in enumerate(rows):
        y = 6 + i * rh
        a, t, b = r["actual"], r.get("target"), r.get("band")
        out.append(f'<text x="{lw - 8}" y="{y + 14}" font-size="12" fill="{INK1}" text-anchor="end">{_t(r["label"])}</text>')
        if b:
            out.append(f'<rect x="{lw}" y="{y + 2}" width="{sx(b) - lw:.1f}" height="18" fill="{BAND}" rx="2">'
                       f'<title>{_t(r["label"])}: annual target {b}</title></rect>')
        out.append(f'<rect x="{lw}" y="{y + 6}" width="{max(sx(a) - lw, 1):.1f}" height="10" fill="{ACT}" rx="2">'
                   f'<title>{_t(r["label"])}: actual {a}' + (f', target {t} ({_pct(a, t)})' if t else '') + '</title></rect>')
        if t:
            out.append(f'<line x1="{sx(t):.1f}" y1="{y + 1}" x2="{sx(t):.1f}" y2="{y + 21}" stroke="{TGT}" stroke-width="2.5">'
                       f'<title>{_t(r["label"])}: target {t}</title></line>')
        lab = f'{a}' + (f' / {t}  ({_pct(a, t)})' if t else '') + (f'  {r["note"]}' if r.get("note") else "")
        out.append(f'<text x="{lw + bw + 8}" y="{y + 14}" font-size="11" fill="{INK}">{_t(lab)}</text>')
    out.append("</svg>")
    return "".join(out)


def monthly(months, series, cols=3):
    """Small multiples: series = [{label, actual[], target[]}] per month -> bars (actual) + ticks (target)."""
    series = [s for s in series if any(series_v for series_v in s["actual"]) or any(s["target"])]
    if not series:
        return ""
    w, h, top, left, bottom = 300, 150, 22, 28, 22
    n = len(months)
    cw = (w - left - 8) / max(n, 1)
    blocks = []
    for s in series:
        vals = [v or 0 for v in s["actual"]] + [v or 0 for v in s["target"]]
        vmax = max(vals + [1])
        sy = lambda v: top + (h - top - bottom) * (1 - v / vmax)
        o = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{_t(s["label"])} by month">',
             f'<text x="4" y="14" font-size="12" font-weight="600" fill="{INK1}">{_t(s["label"])}</text>']
        for k in (0, 0.5, 1):
            yv = sy(vmax * k)
            o.append(f'<line x1="{left}" y1="{yv:.1f}" x2="{w - 6}" y2="{yv:.1f}" stroke="{GRID}"/>'
                     f'<text x="{left - 4}" y="{yv + 3:.1f}" font-size="9" fill="{INK}" text-anchor="end">{round(vmax * k)}</text>')
        for i, m in enumerate(months):
            x = left + i * cw
            a, t = s["actual"][i], s["target"][i]
            tip = f'{s["label"]} {m:%b-%y}: actual {a if a is not None else "—"}' + (f', target {t}' if t is not None else ', no target')
            if a:
                o.append(f'<rect x="{x + cw * 0.18:.1f}" y="{sy(a):.1f}" width="{cw * 0.64:.1f}" height="{sy(0) - sy(a):.1f}" fill="{ACT}" rx="2"><title>{_t(tip)}</title></rect>')
            else:
                o.append(f'<rect x="{x:.1f}" y="{top}" width="{cw:.1f}" height="{h - top - bottom}" fill="transparent"><title>{_t(tip)}</title></rect>')
            if t is not None:
                o.append(f'<line x1="{x + cw * 0.08:.1f}" y1="{sy(t):.1f}" x2="{x + cw * 0.92:.1f}" y2="{sy(t):.1f}" stroke="{TGT}" stroke-width="2.5"><title>{_t(tip)}</title></line>')
            o.append(f'<text x="{x + cw / 2:.1f}" y="{h - 8}" font-size="9" fill="{INK}" text-anchor="middle">{m:%b}</text>')
        o.append("</svg>")
        blocks.append("".join(o))
    return '<div class="multiples">' + "".join(f"<div>{b}</div>" for b in blocks) + "</div>"


def hbars(rows, unit="", fmt=lambda v: str(v)):
    """rows: [{label, value, note}] -> single-series horizontal bars, value labelled at the end."""
    rows = [r for r in rows if r.get("value") is not None]
    if not rows:
        return ""
    lw, bw, rh = 150, 360, 24
    vmax = max([r["value"] for r in rows] + [1])
    h = len(rows) * rh + 8
    out = [f'<svg class="chart" viewBox="0 0 {lw + bw + 210} {h}" role="img">']
    for i, r in enumerate(rows):
        y = 4 + i * rh
        wv = max(r["value"] / vmax * bw, 1)
        col = OWN if r.get("own") else ACT
        out.append(f'<text x="{lw - 8}" y="{y + 13}" font-size="12" fill="{INK1}" text-anchor="end">{_t(r["label"])}</text>'
                   f'<rect x="{lw}" y="{y + 4}" width="{wv:.1f}" height="12" fill="{col}" rx="2">'
                   f'<title>{_t(r["label"])}: {fmt(r["value"])}{unit}' + (f' · {r["note"]}' if r.get("note") else "") + '</title></rect>'
                   f'<text x="{lw + wv + 6:.1f}" y="{y + 13}" font-size="11" fill="{INK}">{_t(fmt(r["value"]) + unit)}'
                   + (f'  ·  {_t(r["note"])}' if r.get("note") else "") + '</text>')
    out.append("</svg>")
    return "".join(out)
