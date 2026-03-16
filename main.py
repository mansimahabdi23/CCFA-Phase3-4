"""
main.py
───────
Entry point for the CCFA Phase 3 + Phase 4 pipeline.

Usage:
    python main.py                  # run pipeline + generate report
    streamlit run dashboard/dashboard.py   # interactive dashboard
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator import run_pipeline
from xai.xai_engine import explain
from reports.report_generator import generate_report


def main():
    print("\n" + "━" * 70)
    print("  CCFA — Cognitive Compliance & Forensic Auditor")
    print("  Phase 3: Multi-Agent Courtroom  +  Phase 4: XAI Output")
    print("━" * 70 + "\n")

    # ── Phase 3: Run the multi-agent courtroom ────────────────────────────
    final_state = run_pipeline()

    # ── Phase 4a: Generate XAI report ─────────────────────────────────────
    print("\n[Phase 4] Generating XAI report...")
    xai_report = explain(final_state)

    print(f"\n  Top Risk Factors:")
    for f in xai_report.top_risk_factors:
        print(f"    • {f}")

    print(f"\n  Mitigating Factors:")
    for f in xai_report.top_mitigating_factors:
        print(f"    • {f}")

    print(f"\n  LIME: {xai_report.lime_summary[:120]}...")

    # ── Phase 4b: Generate PDF ─────────────────────────────────────────────
    print("\n[Phase 4] Generating PDF report...")
    report_dir = os.path.join(os.path.dirname(__file__), "output_reports")
    report_path = generate_report(final_state, xai_report, output_dir=report_dir)
    print(f"  ✓ Report saved: {report_path}")

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n" + "━" * 70)
    print("  PIPELINE SUMMARY")
    print("━" * 70)
    print(f"  Transaction ID  : {final_state['transaction']['id']}")
    print(f"  Prediction      : {xai_report.model_prediction}")
    print(f"  Confidence      : {xai_report.model_confidence:.0%}")
    print(f"  Route           : {final_state.get('route', '—')}")
    print(f"  Frozen          : {final_state.get('transaction_frozen', False)}")
    print(f"  Expert flags    : {final_state.get('expert_agreement_flags', 0)}/3")
    print(f"  SARs filed      : {len(final_state.get('sar_filings', []))}")
    for s in final_state.get("sar_filings", []):
        print(f"    [{s['jurisdiction']}] {s['tracking_id']}")
    print(f"  Report          : {report_path}")
    print("━" * 70)
    print("\n  To launch the interactive dashboard:")
    print("    streamlit run dashboard/dashboard.py\n")

    return final_state, xai_report, report_path


if __name__ == "__main__":
    main()
