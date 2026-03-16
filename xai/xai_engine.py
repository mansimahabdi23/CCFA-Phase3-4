"""
xai_engine.py
─────────────
Phase 4 – Explainable AI (XAI) module.

Produces SHAP-style feature attributions and a structured explanation
that is both legally defensible and human-readable.

In production:
  • Replace _mock_shap_values() with a real shap.TreeExplainer or
    shap.KernelExplainer on the trained GNN model outputs.
  • Replace _mock_lime_explanation() with lime.tabular.LimeTabularExplainer.

The public function explain() returns an XAIReport dataclass that is
consumed by the PDF report generator and the Streamlit dashboard.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FeatureAttribution:
    feature_name:    str
    shap_value:      float       # positive = pushes toward HIGH RISK
    lime_weight:     float
    raw_value:       Any
    human_label:     str         # plain-English label for the report
    direction:       str         # "risk" | "safe"


@dataclass
class XAIReport:
    transaction_id:         str
    model_prediction:       str          # "HIGH RISK" | "LOW RISK"
    model_confidence:       float        # 0–1
    base_value:             float        # SHAP baseline
    attributions:           list[FeatureAttribution]
    top_risk_factors:       list[str]    # plain-English top 3
    top_mitigating_factors: list[str]
    lime_summary:           str          # one-paragraph narrative
    regulatory_links:       list[dict]   # {rule_id, breach, reason}
    generated_at:           str
    explainer_versions:     dict


# ─────────────────────────────────────────────────────────────────────────────
# Mock SHAP values  (replace with real shap library in production)
# ─────────────────────────────────────────────────────────────────────────────

def _mock_shap_values(graph_analysis: dict) -> dict[str, float]:
    """
    Returns SHAP values keyed by feature name.
    Positive = contributes to HIGH RISK classification.
    Negative = contributes against HIGH RISK classification.

    In production:
        explainer = shap.TreeExplainer(gnn_model)
        shap_values = explainer.shap_values(feature_vector)
    """
    fi = graph_analysis.get("feature_importances", {})
    # Convert raw importance [0,1] to signed SHAP-style values
    shap_map = {
        "cycle_motifs_detected":        +fi.get("cycle_motifs_detected", 0.94) * 0.45,
        "anomaly_score":                +fi.get("anomaly_score", 0.91) * 0.38,
        "shell_company_probability":    +fi.get("shell_company_probability", 0.87) * 0.32,
        "known_bad_actors_in_cluster":  +fi.get("known_bad_actors_in_cluster", 0.83) * 0.28,
        "velocity_spike":               +fi.get("velocity_spike", 0.85) * 0.25,
        "intermediary_hops":            +fi.get("intermediary_hops", 0.79) * 0.22,
        "account_age_days_sender":      +fi.get("account_age_days_sender", 0.72) * 0.18,
        "account_age_days_receiver":    +fi.get("account_age_days_receiver", 0.68) * 0.16,
        "smurfing_variance":            +fi.get("smurfing_variance", 0.76) * 0.20,
        "device_fingerprint_match":     -fi.get("device_fingerprint_match", 0.61) * 0.10,
        # mitigating factors
        "stated_purpose_provided":      -0.05,
        "sender_bank_tier":             -0.03,
    }
    return shap_map


# ─────────────────────────────────────────────────────────────────────────────
# Mock LIME explanation
# ─────────────────────────────────────────────────────────────────────────────

def _mock_lime_explanation(transaction: dict, graph_analysis: dict) -> str:
    """
    Returns a LIME-style neighbourhood explanation narrative.

    In production:
        explainer = lime.tabular.LimeTabularExplainer(training_data, ...)
        exp = explainer.explain_instance(sample, predict_fn)
        exp.as_list()
    """
    return (
        f"LIME local approximation (neighbourhood size=500 perturbations):\n"
        f"The GNN classifier assigned HIGH RISK to transaction "
        f"{transaction['id']} primarily because similar transactions "
        f"in its neighbourhood (±15% amount, ±30 days) with cycle motifs "
        f"AND sender account age <120 days were classified HIGH RISK in "
        f"98.2% of cases. The most influential boundary feature is the "
        f"presence of a confirmed cycle motif (CYCLE-A): removing it "
        f"reduces the risk score from 0.91 to 0.43. "
        f"The velocity spike (3× 48h baseline) adds an independent +0.18 "
        f"to the risk logit. Beneficiary account age <90 days adds +0.14. "
        f"These three features together account for 79% of the decision."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Human-readable labels map
# ─────────────────────────────────────────────────────────────────────────────

FEATURE_LABELS = {
    "cycle_motifs_detected":       "Circular money flow (smurfing cycle) detected",
    "anomaly_score":               "Overall graph anomaly score from GNN",
    "shell_company_probability":   "Probability that sender/receiver is a shell company",
    "known_bad_actors_in_cluster": "Number of known bad actors in same cluster",
    "velocity_spike":              "Transaction velocity spike (3× 48-hr baseline)",
    "intermediary_hops":           "Suspicious intermediary routing hops",
    "account_age_days_sender":     "Sender account is very new (< 180 days)",
    "account_age_days_receiver":   "Receiver account is very new (< 180 days)",
    "smurfing_variance":           "Amounts vary slightly to evade filters (smurfing)",
    "device_fingerprint_match":    "Device fingerprint matches known good device",
    "stated_purpose_provided":     "Sender provided a stated purpose for transfer",
    "sender_bank_tier":            "Sender bank is a recognised Tier-1 institution",
}


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────

def explain(final_state: dict) -> XAIReport:
    """
    Generate a full XAI report from the final pipeline state.

    Args:
        final_state: The CCFAState dict returned by orchestrator.run_pipeline()

    Returns:
        XAIReport dataclass ready for PDF and dashboard rendering.
    """
    txn      = final_state["transaction"]
    graph    = final_state["graph_analysis"]
    reg      = final_state["regulatory_excerpts"]
    verdict  = final_state.get("final_verdict", "")
    conf     = final_state.get("auditor_confidence", 0.0)

    # ── SHAP attributions ──────────────────────────────────────────────────
    shap_vals = _mock_shap_values(graph)
    base_value = 0.35   # SHAP baseline: base rate for high-risk in population

    attributions: list[FeatureAttribution] = []
    for feature, shap_val in sorted(shap_vals.items(), key=lambda x: abs(x[1]), reverse=True):
        raw_val = (
            graph.get(feature)
            or txn.get(feature)
            or ("True" if shap_val > 0 else "False")
        )
        attributions.append(FeatureAttribution(
            feature_name  = feature,
            shap_value    = round(shap_val, 4),
            lime_weight   = round(abs(shap_val) * 1.05, 4),   # mock LIME ≈ SHAP
            raw_value     = raw_val,
            human_label   = FEATURE_LABELS.get(feature, feature.replace("_", " ").title()),
            direction     = "risk" if shap_val > 0 else "safe",
        ))

    # ── Top risk / mitigating factors ─────────────────────────────────────
    risk_attrs = [a for a in attributions if a.direction == "risk"][:3]
    safe_attrs = [a for a in attributions if a.direction == "safe"][:2]

    top_risk = [
        f"{a.human_label} (SHAP +{a.shap_value:.3f})"
        for a in risk_attrs
    ]
    top_mitigating = [
        f"{a.human_label} (SHAP {a.shap_value:.3f})"
        for a in safe_attrs
    ]

    # ── Regulatory breach summary ──────────────────────────────────────────
    reg_links = []
    for jur_key, jur_data in reg.items():
        for rule in jur_data.get("relevant_rules", []):
            reg_links.append({
                "rule_id":   rule["rule_id"],
                "breach":    rule["breach_detected"],
                "reason":    rule["reason"],
                "penalty":   jur_data.get("penalty_range", ""),
            })

    # ── LIME narrative ─────────────────────────────────────────────────────
    lime_summary = _mock_lime_explanation(txn, graph)

    return XAIReport(
        transaction_id          = txn["id"],
        model_prediction        = "HIGH RISK" if conf >= 0.75 else "LOW RISK",
        model_confidence        = conf,
        base_value              = base_value,
        attributions            = attributions,
        top_risk_factors        = top_risk,
        top_mitigating_factors  = top_mitigating,
        lime_summary            = lime_summary,
        regulatory_links        = reg_links,
        generated_at            = datetime.now(timezone.utc).isoformat(),
        explainer_versions      = {
            "shap_version":  "0.44.0-mock",
            "lime_version":  "0.2.0.1-mock",
            "gnn_model":     graph.get("gnn_model", "GraphSAGE"),
        },
    )
