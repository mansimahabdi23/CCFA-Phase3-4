"""
orchestrator.py
───────────────
LangGraph-based stateful orchestrator for the Multi-Agent Courtroom.

Graph topology:

  [START]
     │
     ▼
  india_expert_node
     │
     ▼
  eu_expert_node
     │
     ▼
  fincen_expert_node
     │
     ▼
  auditor_node  ─── (all agree) ──▶ freeze_and_report
     │                                     │
     └── (disagreement) ──▶ human_review ──┘
                                           │
                                         [END]

The graph is constructed with a TypedDict State so every node
reads / writes a well-defined set of keys.

NOTE: This uses the langgraph API but falls back gracefully to a
      sequential Python simulation if langgraph is not installed.
"""

import sys
import os
import json
from typing import TypedDict, Optional, Any
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.context_package import CONTEXT_PACKAGE
from agents.agents import (
    IndiaExpertAgent,
    EUExpertAgent,
    AuditorAgent,
)

# ─────────────────────────────────────────────────────────────────────────────
# State Schema
# ─────────────────────────────────────────────────────────────────────────────

class CCFAState(TypedDict, total=False):
    # Inputs (from context package)
    transaction:            dict
    graph_analysis:         dict
    regulatory_excerpts:    dict

    # Outputs from each expert node
    india_expert_verdict:   str
    india_tool_calls:       dict
    eu_expert_verdict:      str
    eu_tool_calls:          dict

    # Outputs from auditor node
    final_verdict:          str
    transaction_frozen:     bool
    sar_filings:            list
    expert_agreement_flags: int
    auditor_confidence:     float

    # Routing & metadata
    route:                  str        # "freeze_and_report" | "human_review"
    run_id:                 str
    started_at:             str
    completed_at:           str
    error:                  Optional[str]


# ─────────────────────────────────────────────────────────────────────────────
# Node wrappers
# ─────────────────────────────────────────────────────────────────────────────

def india_expert_node(state: CCFAState) -> CCFAState:
    agent = IndiaExpertAgent()
    updates = agent.run(state)
    return {**state, **updates}


def eu_expert_node(state: CCFAState) -> CCFAState:
    agent = EUExpertAgent()
    updates = agent.run(state)
    return {**state, **updates}


def auditor_node(state: CCFAState) -> CCFAState:
    agent = AuditorAgent()
    updates = agent.run(state)
    # Routing decision
    flags = updates.get("expert_agreement_flags", 0)
    route = "freeze_and_report" if flags >= 2 else "human_review"
    return {**state, **updates, "route": route}


def freeze_and_report_node(state: CCFAState) -> CCFAState:
    print("\n[FreezeAndReport] Transaction FROZEN. Triggering XAI report generation...")
    return {**state, "completed_at": datetime.now(timezone.utc).isoformat()}


def human_review_node(state: CCFAState) -> CCFAState:
    print("\n[HumanReview] Experts DISAGREE. Escalating to human compliance officer...")
    return {**state, "completed_at": datetime.now(timezone.utc).isoformat()}


# ─────────────────────────────────────────────────────────────────────────────
# Conditional edge (routing function)
# ─────────────────────────────────────────────────────────────────────────────

def route_after_auditor(state: CCFAState) -> str:
    return state.get("route", "human_review")


# ─────────────────────────────────────────────────────────────────────────────
# Graph construction  (LangGraph if available, else sequential fallback)
# ─────────────────────────────────────────────────────────────────────────────

def build_graph():
    """
    Returns a compiled LangGraph StateGraph.
    If langgraph is not installed, returns None and the
    run_pipeline() function falls back to sequential execution.
    """
    try:
        from langgraph.graph import StateGraph, END

        graph = StateGraph(CCFAState)

        # Add nodes
        graph.add_node("india_expert",      india_expert_node)
        graph.add_node("eu_expert",         eu_expert_node)
        graph.add_node("auditor",           auditor_node)
        graph.add_node("freeze_and_report", freeze_and_report_node)
        graph.add_node("human_review",      human_review_node)

        # Sequential expert pipeline
        graph.set_entry_point("india_expert")
        graph.add_edge("india_expert", "eu_expert")
        graph.add_edge("eu_expert",    "auditor")

        # Conditional routing after auditor
        graph.add_conditional_edges(
            "auditor",
            route_after_auditor,
            {
                "freeze_and_report": "freeze_and_report",
                "human_review":      "human_review",
            },
        )
        graph.add_edge("freeze_and_report", END)
        graph.add_edge("human_review",      END)

        return graph.compile()

    except ImportError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Sequential fallback pipeline
# ─────────────────────────────────────────────────────────────────────────────

def _run_sequential(initial_state: CCFAState) -> CCFAState:
    """Run all nodes in order without LangGraph (pure Python fallback)."""
    state = initial_state
    for node_fn in [
        india_expert_node,
        eu_expert_node,
        auditor_node,
    ]:
        state = node_fn(state)

    route = state.get("route", "human_review")
    if route == "freeze_and_report":
        state = freeze_and_report_node(state)
    else:
        state = human_review_node(state)

    return state


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(context_package: dict | None = None) -> CCFAState:
    """
    Execute the full Multi-Agent Courtroom pipeline.

    Args:
        context_package: Override the default hardcoded package for testing.

    Returns:
        Final CCFAState with all verdicts, tool calls, and SAR receipts.
    """
    pkg = context_package or CONTEXT_PACKAGE

    import uuid
    initial_state: CCFAState = {
        "transaction":          pkg["transaction"],
        "graph_analysis":       pkg["graph_analysis"],
        "regulatory_excerpts":  pkg["regulatory_excerpts"],
        "run_id":               str(uuid.uuid4()),
        "started_at":           datetime.now(timezone.utc).isoformat(),
    }

    print("=" * 70)
    print("  CCFA MULTI-AGENT COURTROOM  —  LangGraph Orchestrator")
    print(f"  Transaction: {initial_state['transaction']['id']}")
    print(f"  Run ID:      {initial_state['run_id']}")
    print("=" * 70)

    graph = build_graph()
    if graph is not None:
        print("  [INFO] LangGraph detected — using compiled StateGraph.\n")
        final_state = graph.invoke(initial_state)
    else:
        print("  [INFO] LangGraph not installed — using sequential fallback.\n")
        final_state = _run_sequential(initial_state)

    print("\n" + "=" * 70)
    print(f"  PIPELINE COMPLETE  |  Route: {final_state.get('route','—')}")
    print(f"  Transaction frozen: {final_state.get('transaction_frozen', False)}")
    print(f"  SARs filed: {len(final_state.get('sar_filings', []))}")
    print("=" * 70)

    return final_state


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = run_pipeline()
    print("\n\n── FINAL VERDICT ──────────────────────────────────────────────────")
    print(result.get("final_verdict", ""))
