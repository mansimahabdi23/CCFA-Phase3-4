"""
context_package.py
──────────────────
Hardcoded context package that simulates the outputs of Phase 1 (Semantic
Regulatory Brain) and Phase 2 (Forensic Network Explorer).

In production these values would come from:
  • Phase 1  →  Neo4j + Pinecone RAG pipeline / faiss vector DB
  • Phase 2  → Pytorch geometric GAT anomaly scores + cycle-motif detection

For now everything is self-contained so Phase 3 & 4 can run standalone.
"""

from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────
# 1. SUSPICIOUS TRANSACTION (flagged by Phase 2)
# ─────────────────────────────────────────────

TRANSACTION = {
    "id": "TXN-2026-XB-004821",
    "timestamp": "2026-03-15T08:42:11Z",
    "amount_usd": 47_500.00,
    "currency_pair": "INR → USD",
    "sender": {
        "account_id": "ACC-IN-9921",
        "entity_name": "Nexus Mercantile Pvt Ltd",
        "country": "India",
        "bank": "Kotak Mahindra Bank",
        "monthly_avg_txn": 12_000,         # historical average
        "account_age_days": 94,             # very new
        "prior_flags": 1,
    },
    "receiver": {
        "account_id": "ACC-US-3301",
        "entity_name": "Apex Global Ventures LLC",
        "country": "USA",
        "bank": "Silicon Valley Bank (successor)",
        "monthly_avg_txn": 8_500,
        "account_age_days": 61,             # very new
        "prior_flags": 2,
    },
    "intermediary_hops": [
        {"account_id": "ACC-SG-1122", "country": "Singapore", "hold_time_hrs": 1.2},
        {"account_id": "ACC-AE-0077", "country": "UAE",       "hold_time_hrs": 0.8},
    ],
    "transaction_type": "Cross-border wire transfer",
    "stated_purpose": "Software consultancy services",
    "device_fingerprint_match": False,      # sender device ≠ usual device
    "velocity_spike": True,                 # 3× normal in 48 hrs
}

# ─────────────────────────────────────────────
# 2. GRAPH ANALYSIS (from Phase 2 GNN)
# ─────────────────────────────────────────────

GRAPH_ANALYSIS = {
    "gnn_model": "Pytorch Geometric GAT v2.1.0-mock",
    "anomaly_score": 0.91,                  # 0–1; >0.75 is high risk
    "cycle_motifs_detected": [
        {
            "cycle_id": "CYCLE-A",
            "path": ["ACC-IN-9921", "ACC-SG-1122", "ACC-AE-0077", "ACC-US-3301", "ACC-IN-9921"],
            "total_amount_usd": 143_200,
            "num_legs": 4,
            "time_span_hours": 72,
            "smurfing_variance": 0.08,      # amounts vary <10 % to evade detection
        }
    ],
    "community_cluster": "CLUSTER-SHELL-07",
    "known_bad_actors_in_cluster": 3,
    "shell_company_probability": 0.87,
    "feature_importances": {               # used later by SHAP mock
        "anomaly_score":               0.91,
        "account_age_days_sender":     0.72,
        "account_age_days_receiver":   0.68,
        "velocity_spike":              0.85,
        "cycle_motifs_detected":       0.94,
        "intermediary_hops":           0.79,
        "known_bad_actors_in_cluster": 0.83,
        "device_fingerprint_match":    0.61,
        "smurfing_variance":           0.76,
        "shell_company_probability":   0.87,
    },
}

# ─────────────────────────────────────────────
# 3. REGULATORY EXPERTS (from Phase 1 RAG)
# ─────────────────────────────────────────────

REGULATORY_EXPERTS = {
    "RBI": {
        "jurisdiction": "India",
        "source": "RBI Master Direction – KYC, 2016 (updated Feb 2026)",
        "relevant_rules": [
            {
                "rule_id": "RBI-KYC-2016-§38",
                "summary": "Cross-border wire transfers above ₹25 lakh (≈$30k USD) require "
                           "Enhanced Due Diligence (EDD) including source-of-funds declaration.",
                "breach_detected": True,
                "reason": "Amount ≈$47,500 (>$30k threshold). No source-of-funds document present.",
            },
            {
                "rule_id": "RBI-FEMA-2013-§6(3)",
                "summary": "Transactions routed through >2 intermediary jurisdictions within 48 hrs "
                           "must be reported to the Financial Intelligence Unit – India (FIU-IND).",
                "breach_detected": True,
                "reason": "2 intermediate hops (Singapore, UAE) within 72 hrs.",
            },
            {
                "rule_id": "RBI-AML-2023-§12",
                "summary": "Entities with account age <180 days are subject to monthly transaction "
                           "cap of ₹15 lakh (≈$18k USD) unless VCIP-verified.",
                "breach_detected": True,
                "reason": "Sender account age = 94 days; transaction amount exceeds cap.",
            },
        ],
        "penalty_range": "Up to 4% of global annual turnover or ₹10 crore, whichever is higher.",
    },
    "EU_AI_ACT": {
        "jurisdiction": "European Union",
        "source": "EU AI Act 2024 – Annex III High-Risk Systems & AMLD-6",
        "relevant_rules": [
            {
                "rule_id": "EUAIA-2024-Art22",
                "summary": "High-risk AI systems used in AML decisions must provide human-readable "
                           "explanations before freezing assets.",
                "breach_detected": False,
                "reason": "CCFA system generates XAI report per this rule — compliant.",
            },
            {
                "rule_id": "AMLD6-Art3(4)",
                "summary": "Shell-company probability >80% triggers mandatory Suspicious Activity "
                           "Report (SAR) filing within 24 hours.",
                "breach_detected": True,
                "reason": "Shell company probability = 87%. SAR not yet filed.",
            },
        ],
        "penalty_range": "Up to €10 million or 2% of worldwide annual revenue.",
    },

}

# ─────────────────────────────────────────────
# 4. COMPILED CONTEXT PACKAGE (single import)
# ─────────────────────────────────────────────

CONTEXT_PACKAGE = {
    "transaction":          TRANSACTION,
    "graph_analysis":       GRAPH_ANALYSIS,
    "regulatory_excerpts":  REGULATORY_EXPERTS,
    "phase_versions": {
        "phase1_rag":  "v1.4.2-mock",
        "phase2_gnn":  "v2.1.0-mock",
    },
}
