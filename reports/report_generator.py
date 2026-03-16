"""
report_generator.py
───────────────────
Phase 4 – PDF Report Generator.

Converts the XAIReport + final CCFAState into a legally defensible,
professionally formatted PDF audit report using ReportLab.

Output:  reports/CCFA_Report_<txn_id>_<timestamp>.pdf
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone
from xai.xai_engine import XAIReport

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Color palette
# ─────────────────────────────────────────────────────────────────────────────

DARK_NAVY    = colors.HexColor("#0D1B2A")
ACCENT_RED   = colors.HexColor("#C0392B")
ACCENT_GOLD  = colors.HexColor("#D4AC0D")
SAFE_GREEN   = colors.HexColor("#1E8449")
LIGHT_GRAY   = colors.HexColor("#F2F3F4")
MID_GRAY     = colors.HexColor("#BDC3C7")
WHITE        = colors.white


# ─────────────────────────────────────────────────────────────────────────────
# Plain-text fallback
# ─────────────────────────────────────────────────────────────────────────────

def _generate_text_report(final_state: dict, xai_report: XAIReport, output_path: str) -> str:
    txt_path = output_path.replace(".pdf", ".txt")
    lines = [
        "=" * 72,
        "  CCFA AUDIT REPORT  —  Cognitive Compliance & Forensic Auditor",
        "=" * 72,
        f"Transaction ID : {xai_report.transaction_id}",
        f"Generated At   : {xai_report.generated_at}",
        f"Prediction     : {xai_report.model_prediction}",
        f"Confidence     : {xai_report.model_confidence:.0%}",
        f"Frozen         : {final_state.get('transaction_frozen', False)}",
        "",
        "── FINAL VERDICT ──────────────────────────────────────────────────",
        final_state.get("final_verdict", ""),
        "",
        "── TOP RISK FACTORS ───────────────────────────────────────────────",
    ]
    for f in xai_report.top_risk_factors:
        lines.append(f"  • {f}")
    lines += [
        "",
        "── MITIGATING FACTORS ─────────────────────────────────────────────",
    ]
    for f in xai_report.top_mitigating_factors:
        lines.append(f"  • {f}")
    lines += [
        "",
        "── REGULATORY BREACHES ────────────────────────────────────────────",
    ]
    for r in xai_report.regulatory_links:
        status = "BREACH" if r["breach"] else "COMPLIANT"
        lines.append(f"  [{r['rule_id']}]  {status}")
        lines.append(f"    {r['reason']}")
        lines.append(f"    Penalty: {r['penalty']}")
        lines.append("")
    lines += [
        "── SHAP FEATURE ATTRIBUTIONS ──────────────────────────────────────",
        f"  {'Feature':<40} {'SHAP':>8}  {'Direction':<10}",
        "  " + "-" * 60,
    ]
    for a in xai_report.attributions:
        arrow = "▲ RISK" if a.direction == "risk" else "▼ SAFE"
        lines.append(f"  {a.human_label:<40} {a.shap_value:>+8.4f}  {arrow}")
    lines += [
        "",
        "── LIME EXPLANATION ───────────────────────────────────────────────",
        xai_report.lime_summary,
        "",
        "── SAR FILINGS ────────────────────────────────────────────────────",
    ]
    for sar in final_state.get("sar_filings", []):
        lines.append(f"  [{sar['jurisdiction']}]  {sar['tracking_id']}  Filed: {sar['filed_at']}")
    lines.append("=" * 72)

    with open(txt_path, "w") as f:
        f.write("\n".join(lines))
    return txt_path


# ─────────────────────────────────────────────────────────────────────────────
# PDF generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_report(
    final_state:  dict,
    xai_report:   XAIReport,
    output_dir:   str = "reports",
) -> str:
    """
    Generate a PDF (or TXT fallback) audit report.

    Returns:
        Absolute path to the generated file.
    """
    os.makedirs(output_dir, exist_ok=True)
    ts   = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    txn  = xai_report.transaction_id.replace("/", "_")
    path = os.path.join(output_dir, f"CCFA_Report_{txn}_{ts}.pdf")

    if not REPORTLAB_AVAILABLE:
        print("  [WARN] ReportLab not installed — generating TXT report instead.")
        return _generate_text_report(final_state, xai_report, path)

    # ── Document setup ─────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()

    H1 = ParagraphStyle("H1", fontSize=18, textColor=DARK_NAVY,
                         fontName="Helvetica-Bold", spaceAfter=6, alignment=TA_CENTER)
    H2 = ParagraphStyle("H2", fontSize=13, textColor=DARK_NAVY,
                         fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=4)
    H3 = ParagraphStyle("H3", fontSize=11, textColor=DARK_NAVY,
                         fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3)
    BODY = ParagraphStyle("BODY", fontSize=9, leading=14, spaceAfter=4)
    META = ParagraphStyle("META", fontSize=8, textColor=colors.HexColor("#666666"))
    VERDICT = ParagraphStyle("VERDICT", fontSize=9, leading=13, spaceAfter=6,
                              leftIndent=12, borderPad=6)
    BREACH = ParagraphStyle("BREACH", fontSize=8, textColor=ACCENT_RED, leading=12)
    SAFE   = ParagraphStyle("SAFE",   fontSize=8, textColor=SAFE_GREEN, leading=12)

    story = []

    # ── Cover header ───────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("COGNITIVE COMPLIANCE &amp; FORENSIC AUDITOR", H1))
    story.append(Paragraph("Multi-Agent Courtroom — Audit Report", 
                            ParagraphStyle("sub", fontSize=11, textColor=MID_GRAY,
                                           alignment=TA_CENTER, spaceAfter=4)))
    story.append(HRFlowable(width="100%", thickness=2, color=DARK_NAVY))
    story.append(Spacer(1, 0.4*cm))

    # Meta table
    txn_data = final_state["transaction"]
    meta = [
        ["Transaction ID",  xai_report.transaction_id,
         "Prediction",      xai_report.model_prediction],
        ["Amount",          f"${txn_data['amount_usd']:,.2f} ({txn_data['currency_pair']})",
         "Confidence",      f"{xai_report.model_confidence:.0%}"],
        ["Timestamp",       txn_data["timestamp"],
         "Frozen",          str(final_state.get("transaction_frozen", False))],
        ["Run ID",          final_state.get("run_id", "—"),
         "SARs Filed",      str(len(final_state.get("sar_filings", [])))],
        ["Report Generated", xai_report.generated_at, "", ""],
    ]
    meta_tbl = Table(meta, colWidths=[3.5*cm, 6*cm, 3*cm, 4*cm])
    risk_color = ACCENT_RED if xai_report.model_prediction == "HIGH RISK" else SAFE_GREEN
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LIGHT_GRAY),
        ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",   (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LIGHT_GRAY, WHITE]),
        ("TEXTCOLOR",  (1,0), (1,0), risk_color),
        ("FONTNAME",   (1,0), (1,0), "Helvetica-Bold"),
        ("GRID",       (0,0), (-1,-1), 0.25, MID_GRAY),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 0.5*cm))

    # ── Section 1: Final Verdict ───────────────────────────────────────────
    story.append(Paragraph("1. AUDITOR FINAL VERDICT", H2))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    for line in final_state.get("final_verdict", "").split("\n"):
        if line.strip():
            story.append(Paragraph(line.replace("•", "&#8226;"), BODY))
    story.append(Spacer(1, 0.3*cm))

    # ── Section 2: Expert Verdicts ─────────────────────────────────────────
    story.append(Paragraph("2. JURISDICTIONAL EXPERT VERDICTS", H2))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    for label, key in [
        ("India Expert (RBI)",          "india_expert_verdict"),
        ("EU Expert (AMLD-6 / AI Act)", "eu_expert_verdict"),
    ]:
        story.append(Paragraph(label, H3))
        verdict_text = final_state.get(key, "—")
        for line in verdict_text.split("\n"):
            if line.strip():
                story.append(Paragraph(line, BODY))
        story.append(Spacer(1, 0.2*cm))

    # ── Section 3: Regulatory Breaches ────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("3. REGULATORY BREACH SUMMARY", H2))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))

    breach_rows = [["Rule ID", "Status", "Reason", "Penalty Cap"]]
    for r in xai_report.regulatory_links:
        status = "BREACH ✗" if r["breach"] else "COMPLIANT ✓"
        breach_rows.append([r["rule_id"], status, r["reason"][:80], r["penalty"][:50]])

    breach_tbl = Table(breach_rows, colWidths=[3.8*cm, 2.2*cm, 8*cm, 3*cm])
    breach_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), DARK_NAVY),
        ("TEXTCOLOR",   (0,0), (-1,0), WHITE),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 7.5),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT_GRAY]),
        ("GRID",        (0,0), (-1,-1), 0.25, MID_GRAY),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("WORDWRAP",    (0,0), (-1,-1), True),
    ]))
    # Color BREACH rows red
    for i, r in enumerate(xai_report.regulatory_links, start=1):
        if r["breach"]:
            breach_tbl.setStyle(TableStyle([
                ("TEXTCOLOR", (1,i), (1,i), ACCENT_RED),
                ("FONTNAME",  (1,i), (1,i), "Helvetica-Bold"),
            ]))
        else:
            breach_tbl.setStyle(TableStyle([
                ("TEXTCOLOR", (1,i), (1,i), SAFE_GREEN),
                ("FONTNAME",  (1,i), (1,i), "Helvetica-Bold"),
            ]))
    story.append(breach_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Section 4: SHAP Attributions ──────────────────────────────────────
    story.append(Paragraph("4. SHAP FEATURE ATTRIBUTIONS (XAI)", H2))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Paragraph(
        f"Base value (population average risk): {xai_report.base_value:.3f}  |  "
        f"Final model output: {xai_report.model_confidence:.3f}  |  "
        f"Model: {xai_report.explainer_versions.get('gnn_model','GraphSAGE')}",
        META,
    ))
    story.append(Spacer(1, 0.2*cm))

    shap_rows = [["Feature", "SHAP Value", "LIME Weight", "Direction", "Raw Value"]]
    for a in xai_report.attributions:
        arrow = "▲ RISK" if a.direction == "risk" else "▼ SAFE"
        shap_rows.append([
            a.human_label,
            f"{a.shap_value:+.4f}",
            f"{a.lime_weight:.4f}",
            arrow,
            str(a.raw_value)[:20],
        ])
    shap_tbl = Table(shap_rows, colWidths=[7*cm, 2.2*cm, 2.5*cm, 2*cm, 3.3*cm])
    shap_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), DARK_NAVY),
        ("TEXTCOLOR",   (0,0), (-1,0), WHITE),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 7.5),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT_GRAY]),
        ("GRID",        (0,0), (-1,-1), 0.25, MID_GRAY),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    for i, a in enumerate(xai_report.attributions, start=1):
        color = ACCENT_RED if a.direction == "risk" else SAFE_GREEN
        shap_tbl.setStyle(TableStyle([("TEXTCOLOR", (3,i), (3,i), color)]))
    story.append(shap_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── Section 5: LIME Narrative ──────────────────────────────────────────
    story.append(Paragraph("5. LIME LOCAL EXPLANATION", H2))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    for line in xai_report.lime_summary.split("\n"):
        if line.strip():
            story.append(Paragraph(line, BODY))
    story.append(Spacer(1, 0.4*cm))

    # ── Section 6: SAR Filing Receipts ────────────────────────────────────
    story.append(Paragraph("6. SAR / STR FILING RECEIPTS", H2))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    sar_list = final_state.get("sar_filings", [])
    if sar_list:
        sar_rows = [["Jurisdiction", "Tracking ID", "Filed At", "Review Days"]]
        for s in sar_list:
            sar_rows.append([s["jurisdiction"], s["tracking_id"], s["filed_at"], str(s["estimated_review_days"])])
        sar_tbl = Table(sar_rows, colWidths=[3*cm, 6*cm, 6*cm, 2*cm])
        sar_tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), DARK_NAVY),
            ("TEXTCOLOR",   (0,0), (-1,0), WHITE),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, LIGHT_GRAY]),
            ("GRID",        (0,0), (-1,-1), 0.25, MID_GRAY),
            ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",  (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ]))
        story.append(sar_tbl)
    else:
        story.append(Paragraph("No SARs filed for this transaction.", BODY))

    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_NAVY))
    story.append(Paragraph(
        "This report was auto-generated by the CCFA system. "
        "It is intended for internal compliance use only and does not constitute legal advice. "
        "All SAR filings are subject to review by a qualified compliance officer.",
        META,
    ))

    doc.build(story)
    return path
