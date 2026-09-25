"""One-page PDF order report (ReportLab): status, ETA, bottleneck, pipeline, feature contributions, summary."""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

import config

RED, ORANGE, INK, MUTE, LINE, PAPER = (colors.HexColor(h) for h in ("#c8342b", "#e08a1e", "#221f1c", "#7a746c", "#e4ddd2", "#faf7f2"))
GREEN = colors.HexColor("#2f8f5b")
STATUS_COLOR = {"ON TIME": GREEN, "AT RISK": ORANGE, "DELAY LIKELY": RED}
W, H = A4
M = 40


def _text(c: canvas.Canvas, x, y, s, size=10, font="Helvetica", color=INK, align="left"):
    c.setFont(font, size)
    c.setFillColor(color)
    {"left": c.drawString, "right": c.drawRightString, "center": c.drawCentredString}[align](x, y, s)


def _para(c, text, x, y_top, width, size=9.5, color=INK, leading=13.5) -> float:
    p = Paragraph(text, ParagraphStyle("p", fontName="Helvetica", fontSize=size, leading=leading, textColor=color))
    _, h = p.wrap(width, 1000)
    p.drawOn(c, x, y_top - h)
    return y_top - h


def _logo(c, x, y, s=26):
    c.setFillColor(RED)
    c.roundRect(x, y, s, s, 6, stroke=0, fill=1)
    c.setStrokeColor(colors.white)
    c.setLineWidth(2.2)
    c.setLineCap(1)
    p = c.beginPath()
    p.moveTo(x + s * 0.24, y + s * 0.66)
    p.lineTo(x + s * 0.5, y + s * 0.66)
    p.lineTo(x + s * 0.5, y + s * 0.34)
    p.lineTo(x + s * 0.76, y + s * 0.34)
    c.drawPath(p, stroke=1, fill=0)


def _card(c, x, y, w, h, label, value, color=INK):
    c.setFillColor(colors.white)
    c.setStrokeColor(LINE)
    c.roundRect(x, y, w, h, 8, stroke=1, fill=1)
    _text(c, x + 10, y + h - 15, label.upper(), 7, "Helvetica-Bold", MUTE)
    _text(c, x + 10, y + 12, value, 15 if len(value) < 15 else 11, "Helvetica-Bold", color)


def _footer(c, page_note: str):
    c.setStrokeColor(LINE)
    c.line(M, 62, W - M, 62)
    _text(c, M, 48, "ORDERFLOW", 8, "Helvetica-Bold", RED)
    _text(c, M + 62, 48, "Food Delivery Delay Intelligence", 8, "Helvetica", MUTE)
    _text(c, W - M, 48, config.CREDIT, 8, "Helvetica-Bold", INK, "right")
    _para(c, config.DISCLAIMER, M, 42, W - 2 * M, size=6.8, color=MUTE, leading=9)
    _text(c, W - M, 20, page_note, 6.8, "Helvetica", MUTE, "right")


def build_pdf(a: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"ORDERFLOW report {a['order_id']}")
    c.setAuthor("ORDERFLOW - Aarav Singh")
    c.setFillColor(PAPER)
    c.rect(0, 0, W, H, stroke=0, fill=1)

    # header
    _logo(c, M, H - 66)
    _text(c, M + 36, H - 52, "ORDERFLOW", 19, "Helvetica-Bold", INK)
    _text(c, M + 36, H - 65, "Food Delivery Delay Intelligence", 8.5, "Helvetica", MUTE)
    _text(c, W - M, H - 50, "ORDER INTELLIGENCE REPORT", 9, "Helvetica-Bold", RED, "right")
    _text(c, W - M, H - 63, datetime.now().strftime("%d %b %Y, %H:%M"), 8, "Helvetica", MUTE, "right")
    c.setStrokeColor(LINE)
    c.line(M, H - 78, W - M, H - 78)

    # order + status
    y = H - 112
    _text(c, M, y, "ORDER", 7.5, "Helvetica-Bold", MUTE)
    _text(c, M, y - 22, a["order_id"], 22, "Helvetica-Bold", INK)
    col = STATUS_COLOR[a["status"]]
    tw = c.stringWidth(a["status"], "Helvetica-Bold", 10) + 24
    c.setFillColor(col)
    c.roundRect(W - M - tw, y - 20, tw, 24, 12, stroke=0, fill=1)
    _text(c, W - M - tw / 2, y - 12.5, a["status"], 10, "Helvetica-Bold", colors.white, "center")

    # metric cards
    y -= 84
    gap, cw = 10, (W - 2 * M - 30) / 4
    eta = a["eta"]
    b = a["bottleneck"]["primary"]
    cards = [
        ("Delay probability", f"{a['delay_probability'] * 100:.0f}%", col),
        ("Estimated delivery", f"{eta['minutes']:.0f} min", INK),
        ("Expected delay", f"{a['expected_delay_minutes']:.0f} min", ORANGE if a["expected_delay_minutes"] > 0 else GREEN),
        ("Likely bottleneck", b["name"], INK),
    ]
    for i, (lab, val, colr) in enumerate(cards):
        _card(c, M + i * (cw + gap), y, cw, 50, lab, val, colr)
    _text(c, M, y - 14, f"Promised ETA {a['promised_eta']:.0f} min{' (baseline quote)' if a['promised_eta_estimated'] else ''}   |   "
                        f"Likely range {eta['low']:.0f}-{eta['high']:.0f} min   |   Delay confidence {a['delay_confidence']}   |   "
                        f"ETA confidence {eta['confidence']}", 7.8, "Helvetica", MUTE)

    # pipeline
    y -= 52
    _text(c, M, y, "DELIVERY PIPELINE", 8, "Helvetica-Bold", MUTE)
    stages = a["pipeline"]["stages"]
    n = len(stages)
    bw = (W - 2 * M - (n - 1) * 6) / n
    top = y - 14
    for i, s in enumerate(stages):
        x = M + i * (bw + 6)
        flag = s["flag"]
        fill = colors.HexColor("#fbe3e0") if flag == "primary" else colors.HexColor("#fdf0dc") if flag == "secondary" else colors.white
        stroke = RED if flag == "primary" else ORANGE if flag == "secondary" else LINE
        c.setFillColor(fill)
        c.setStrokeColor(stroke)
        c.setLineWidth(1.4 if flag else 0.8)
        c.roundRect(x, top - 62, bw, 62, 6, stroke=1, fill=1)
        lab = s["label"].split(" ")
        _text(c, x + bw / 2, top - 14, lab[0], 6.6, "Helvetica-Bold", INK, "center")
        _text(c, x + bw / 2, top - 22.5, " ".join(lab[1:]), 6.6, "Helvetica-Bold", INK, "center")
        mins = "-" if s["key"] in ("placed", "delivered") else f"{s['minutes']:.0f} min"
        _text(c, x + bw / 2, top - 40, mins, 10.5, "Helvetica-Bold", stroke if flag else INK, "center")
        _text(c, x + bw / 2, top - 55, f"T+{s['cumulative']:.0f}", 6.8, "Helvetica", MUTE, "center")
        if flag:
            c.setFillColor(stroke)
            c.circle(x + bw - 8, top - 9, 3.2, stroke=0, fill=1)
    _text(c, M, top - 78, f"Estimated total {a['pipeline']['total_minutes']:.0f} min. Highlighted stages are the likely contributing factors "
                          f"(red = primary, orange = secondary).", 7.8, "Helvetica", MUTE)

    # two columns: bottleneck + influence
    y = top - 106
    colw = (W - 2 * M - 24) / 2

    def bars(x0, y0, rows, title, color, note):
        _text(c, x0, y0, title, 8, "Helvetica-Bold", MUTE)
        yy = y0 - 20
        for lab, val, pct, colr in rows:
            _text(c, x0, yy, lab, 8.6, "Helvetica", INK)
            _text(c, x0 + colw, yy, val, 8.6, "Helvetica-Bold", INK, "right")
            c.setFillColor(colors.HexColor("#ece5d9"))
            c.roundRect(x0, yy - 9, colw, 4.5, 2, stroke=0, fill=1)
            c.setFillColor(colr)
            c.roundRect(x0, yy - 9, max(2, colw * min(pct, 100) / 100), 4.5, 2, stroke=0, fill=1)
            yy -= 25
        _para(c, note, x0, yy + 12, colw, size=7.3, color=MUTE, leading=9.5)

    contrib = a["bottleneck"]["contributions"][:6]
    bars(M, y, [(k["name"], f"{k['pct']:.0f}%", k["pct"], RED if i == 0 else ORANGE if i == 1 else colors.HexColor("#c9bfae"))
                for i, k in enumerate(contrib)] or [("No major bottleneck", "-", 0, LINE)],
         "LIKELY BOTTLENECK CONTRIBUTIONS", RED,
         "Share of excess minutes identified across stages (rules + ETA-model what-if). Likely contributing factors, not proven causes.")
    expl = a["explanation"][:6]
    bars(M + colw + 24, y, [(f"{e['label']} ({e['value']})", f"{'+' if e['direction'] == 'increases' else '-' if e['direction'] == 'reduces' else ''}{e['influence_pct']:.0f}%",
                             e["influence_pct"], RED if e["direction"] == "increases" else GREEN if e["direction"] == "reduces" else LINE) for e in expl],
         "WHY WAS THIS ORDER FLAGGED?", RED,
         "Model influence: change in delay probability when that input is set to a typical value (+ raises risk, - lowers it). Not proof of causation.")

    # summary
    y2 = y - 20 - 25 * 6 - 24
    _text(c, M, y2, "SUMMARY", 8, "Helvetica-Bold", MUTE)
    y2 = _para(c, a["summary"], M, y2 - 8, W - 2 * M, size=9.6, leading=14)
    _para(c, f"<b>Delay rule:</b> {a['delay_rule']}. Predictions come from models trained on synthetic data and demonstrate operational "
             "ML techniques; ORDERFLOW has no access to any real platform's internal systems.", M, y2 - 8, W - 2 * M, size=7.6, color=MUTE, leading=10.5)

    # inputs
    i = a["inputs"]
    yi = 168
    _text(c, M, yi, "ORDER INPUTS", 8, "Helvetica-Bold", MUTE)
    cells = [("Order time", f"{i['order_time']} {i['day_of_week'][:3]}"), ("Items", str(i["num_items"])), ("Value", f"INR {i['order_value']:.0f}"),
             ("Prep time", f"{i['prep_time']:g} min"), ("Restaurant load", i["restaurant_load"]), ("Rider assignment", f"{i['rider_assignment_delay']:g} min"),
             ("Pickup wait", f"{i['pickup_wait']:g} min"), ("Distance", f"{i['distance_km']:g} km"), ("Traffic", i["traffic_level"]),
             ("Weather", i["weather"]), ("Area", i["area_type"]), ("Rider", i["rider_experience"]), ("Peak hour", "Yes" if i["peak_hour"] else "No"),
             ("Batch", "Yes" if i["batch_delivery"] else "No")]
    cw2 = (W - 2 * M) / 7
    for k, (lab, val) in enumerate(cells):
        cx, cy = M + (k % 7) * cw2, yi - 20 - (k // 7) * 30
        _text(c, cx, cy, lab.upper(), 6.4, "Helvetica-Bold", MUTE)
        _text(c, cx, cy - 12, val, 9, "Helvetica-Bold", INK)

    _footer(c, "Generated by ORDERFLOW - portfolio project")
    c.showPage()
    c.save()
    return buf.getvalue()
