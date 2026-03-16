"""
tools.py
────────
Defines the concrete "tools" that each LangGraph agent can call.

In production:
  • neo4j_query_tool      → queries a live Neo4j AuraDB instance
  • pinecone_search_tool  → semantic search over regulatory vectors
  • sar_filing_tool       → calls FinCEN / FIU-IND REST APIs
  • account_lookup_tool   → calls a KYC data-provider API

Here every tool is MOCKED but has the correct signatures and return shapes
so the orchestration code works without any external services.
"""

import json
import random
from datetime import datetime, timezone
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1 – Neo4j Graph Query
# ─────────────────────────────────────────────────────────────────────────────

def neo4j_query_tool(cypher: str, params: dict | None = None) -> dict[str, Any]:
    """
    Execute a Cypher query against Neo4j (mocked).

    Production signature would be:
        driver.session().run(cypher, params or {})

    Returns:
        {
            "status": "ok" | "error",
            "rows": list[dict],
            "query_time_ms": float,
        }
    """
    # Simulate results for known query patterns
    if "CYCLE" in cypher.upper() or "cycle" in cypher:
        rows = [
            {"cycle_id": "CYCLE-A", "length": 4, "total_usd": 143200, "span_hrs": 72},
        ]
    elif "ACCOUNT" in cypher.upper() or "account" in cypher:
        rows = [
            {"account_id": "ACC-IN-9921", "flags": 1, "age_days": 94},
            {"account_id": "ACC-US-3301", "flags": 2, "age_days": 61},
        ]
    elif "CLUSTER" in cypher.upper():
        rows = [{"cluster_id": "CLUSTER-SHELL-07", "bad_actors": 3, "size": 18}]
    else:
        rows = []

    return {
        "status": "ok",
        "rows": rows,
        "query_time_ms": round(random.uniform(4.2, 22.7), 2),
        "executed_at": _timestamp(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2 – Pinecone Regulatory RAG Search
# ─────────────────────────────────────────────────────────────────────────────

def pinecone_search_tool(query: str, jurisdiction: str, top_k: int = 3) -> dict[str, Any]:
    """
    Semantic search over the regulatory vector store (mocked).

    Returns:
        {
            "status": "ok",
            "results": list[{"rule_id", "score", "text"}],
        }
    """
    MOCK_RULES = {
        "RBI": [
            ("RBI-KYC-2016-§38",   0.94, "EDD required for cross-border >₹25 lakh."),
            ("RBI-FEMA-2013-§6(3)",0.89, ">2 intermediary hops must be FIU-IND reported."),
            ("RBI-AML-2023-§12",   0.85, "New accounts (<180d) capped at ₹15 lakh/month."),
        ],
        "EU": [
            ("AMLD6-Art3(4)",      0.91, "Shell probability >80 % → SAR within 24 hrs."),
            ("EUAIA-2024-Art22",   0.88, "High-risk AI must produce human-readable explanation."),
        ],
        "FinCEN": [
            ("FINCEN-SAR-§1020.320(a)(2)", 0.96, "SAR required for ≥$5k suspected laundering."),
            ("FINCEN-CDD-2018-§1010.230",  0.90, "Beneficial ownership verification mandatory >$10k."),
        ],
    }
    jur_key = jurisdiction.upper().replace("_AI_ACT", "").replace("EU_", "EU").strip()
    rules = MOCK_RULES.get(jur_key, MOCK_RULES["FinCEN"])
    results = [
        {"rule_id": r[0], "score": r[1], "text": r[2]}
        for r in rules[:top_k]
    ]
    return {
        "status": "ok",
        "results": results,
        "jurisdiction": jurisdiction,
        "query": query,
        "retrieved_at": _timestamp(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool 3 – Account KYC Lookup
# ─────────────────────────────────────────────────────────────────────────────

def account_lookup_tool(account_id: str) -> dict[str, Any]:
    """
    Fetch KYC and risk metadata for a given account (mocked).

    Returns:
        {
            "account_id": str,
            "kyc_status": "verified" | "pending" | "failed",
            "beneficial_owner_verified": bool,
            "pep_flag": bool,      # Politically Exposed Person
            "sanctions_hit": bool,
        }
    """
    KYC_DB = {
        "ACC-IN-9921": {
            "kyc_status": "pending",
            "beneficial_owner_verified": False,
            "pep_flag": False,
            "sanctions_hit": False,
            "ubo_name": None,
        },
        "ACC-US-3301": {
            "kyc_status": "pending",
            "beneficial_owner_verified": False,
            "pep_flag": False,
            "sanctions_hit": False,
            "ubo_name": None,
        },
        "ACC-SG-1122": {
            "kyc_status": "verified",
            "beneficial_owner_verified": True,
            "pep_flag": False,
            "sanctions_hit": False,
            "ubo_name": "Chan Wei Lin",
        },
        "ACC-AE-0077": {
            "kyc_status": "failed",
            "beneficial_owner_verified": False,
            "pep_flag": True,
            "sanctions_hit": True,
            "ubo_name": None,
        },
    }
    record = KYC_DB.get(account_id, {
        "kyc_status": "unknown",
        "beneficial_owner_verified": False,
        "pep_flag": False,
        "sanctions_hit": False,
        "ubo_name": None,
    })
    return {"account_id": account_id, **record, "fetched_at": _timestamp()}


# ─────────────────────────────────────────────────────────────────────────────
# Tool 4 – SAR / STR Filing
# ─────────────────────────────────────────────────────────────────────────────

def sar_filing_tool(
    transaction_id: str,
    jurisdiction: str,
    reason: str,
    filed_by_agent: str,
) -> dict[str, Any]:
    """
    Submit a Suspicious Activity Report (SAR) / Suspicious Transaction Report (STR).

    In production this would call:
      FinCEN BSA E-Filing API  → FinCEN
      FIU-IND portal API       → RBI
      GoAML REST API           → EU / FATF

    Returns a filing confirmation with a tracking number.
    """
    tracking_prefix = {
        "FinCEN": "SAR-FINCEN",
        "RBI":    "STR-FIUIND",
        "EU":     "SAR-GOAML",
    }.get(jurisdiction, "SAR-GENERIC")

    tracking_id = f"{tracking_prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{random.randint(10000,99999)}"

    return {
        "status": "filed",
        "tracking_id": tracking_id,
        "transaction_id": transaction_id,
        "jurisdiction": jurisdiction,
        "reason_summary": reason[:200],
        "filed_by": filed_by_agent,
        "filed_at": _timestamp(),
        "estimated_review_days": 3,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool Registry  (easy import for agents)
# ─────────────────────────────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "neo4j_query":     neo4j_query_tool,
    "pinecone_search": pinecone_search_tool,
    "account_lookup":  account_lookup_tool,
    "sar_filing":      sar_filing_tool,
}
