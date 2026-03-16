"""
agents.py
─────────
Defines the four specialized agents of the Multi-Agent Courtroom.

Each agent is a plain Python class that:
  1. Receives a shared State dict (passed through the LangGraph graph).
  2. Executes its analysis using its tool-set.
  3. Returns a partial state update.

The LangGraph orchestrator (orchestrator.py) wires these together into a
directed, stateful graph.

LLM calls are mocked here using deterministic prompt-response stubs so the
code runs without an API key.  To switch to a real LLM, replace the
`_mock_llm()` calls with:
    client.chat.completions.create(model="gpt-4o", messages=[...])
"""

import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.tools import (
    neo4j_query_tool,
    pinecone_search_tool,
    account_lookup_tool,
    sar_filing_tool,
)
from data.context_package import CONTEXT_PACKAGE


# ─────────────────────────────────────────────────────────────────────────────
# Shared LLM stub  (replace with real LLM in production)
# ─────────────────────────────────────────────────────────────────────────────

def _mock_llm(system_prompt: str, user_message: str, agent_name: str) -> str:
    """
    Deterministic mock that returns pre-defined expert verdicts.
    In production: call OpenAI / Gemini / Anthropic SDK here.
    """
    verdicts = {
        "IndiaExpert": (
            "VERDICT: HIGH RISK – NON-COMPLIANT\n\n"
            "Under RBI jurisdiction I find three critical breaches:\n"
            "1. [RBI-KYC-2016-§38] Amount $47,500 exceeds ₹25 lakh EDD threshold. "
            "No source-of-funds declaration is on file. BREACH.\n"
            "2. [RBI-FEMA-2013-§6(3)] Two intermediary hops (Singapore, UAE) within "
            "72 hours trigger mandatory FIU-IND reporting. BREACH.\n"
            "3. [RBI-AML-2023-§12] Sender account age = 94 days. Transaction exceeds "
            "₹15 lakh monthly cap for unverified new accounts. BREACH.\n"
            "Sender KYC status: PENDING. Beneficial owner: UNVERIFIED.\n"
            "RECOMMENDATION: Freeze transaction. File STR with FIU-IND within 24 hours."
        ),
        "EUExpert": (
            "VERDICT: HIGH RISK – PARTIAL BREACH\n\n"
            "Under EU/AMLD-6 and EU AI Act jurisdiction:\n"
            "1. [AMLD6-Art3(4)] GNN shell-company probability = 87%, exceeding the 80% "
            "threshold. A SAR must be filed with GoAML within 24 hours. BREACH.\n"
            "2. [EUAIA-2024-Art22] The CCFA system is generating this XAI report, "
            "satisfying the explainability obligation. COMPLIANT.\n"
            "Intermediary account ACC-AE-0077 (UAE) has a SANCTIONS HIT and PEP flag "
            "in KYC database — this is an aggravating factor under AMLD-6 Art 18.\n"
            "RECOMMENDATION: Freeze transaction. Mandatory SAR via GoAML. "
            "Escalate ACC-AE-0077 to sanctions compliance team."
        ),
        "Auditor": (
            "AUDITOR FINAL RULING: TRANSACTION FROZEN\n\n"
            "Both jurisdictional experts are in agreement: this transaction is "
            "HIGH RISK and NON-COMPLIANT across RBI (India) and EU/AMLD-6 frameworks.\n\n"
            "KEY AGGRAVATING FACTORS:\n"
            "• GNN cycle motif CYCLE-A detected — textbook smurfing pattern.\n"
            "• Shell company probability 87% (above both RBI and EU thresholds).\n"
            "• Sanctions hit on intermediary ACC-AE-0077 (UAE).\n"
            "• Both end-point accounts have PENDING KYC and unverified beneficial owners.\n"
            "• 94-day and 61-day old accounts — both below the 180-day safe-harbour.\n\n"
            "ACTIONS ORDERED:\n"
            "1. Immediately freeze TXN-2026-XB-004821.\n"
            "2. File STR with FIU-IND (India) within 24 hours.\n"
            "3. File SAR with GoAML (EU) within 24 hours.\n"
            "4. Escalate ACC-AE-0077 to the Sanctions Compliance team.\n"
            "5. Place a 90-day monitoring hold on cluster CLUSTER-SHELL-07.\n\n"
            "CONFIDENCE: 94%\n"
            "XAI REPORT: Attached."
        ),
    }
    return verdicts.get(agent_name, "VERDICT: UNABLE TO DETERMINE")


# ─────────────────────────────────────────────────────────────────────────────
# Base Agent
# ─────────────────────────────────────────────────────────────────────────────

class BaseAgent:
    name: str = "BaseAgent"
    jurisdiction: str = "GLOBAL"
    system_prompt_template: str = ""

    def __init__(self):
        self.ctx = CONTEXT_PACKAGE

    def _build_system_prompt(self) -> str:
        return (
            f"You are the {self.name} compliance expert in a Multi-Agent Courtroom. "
            f"Your jurisdiction is {self.jurisdiction}. "
            "Analyse the provided transaction and graph data against current regulations. "
            "Be precise, cite rule IDs, and give a clear VERDICT."
        )

    def _build_user_message(self, state: dict) -> str:
        return (
            f"Transaction: {json.dumps(state['transaction'], indent=2)}\n\n"
            f"Graph Analysis: {json.dumps(state['graph_analysis'], indent=2)}\n\n"
            f"Regulatory Experts for {self.jurisdiction}: "
            f"{json.dumps(state['regulatory_experts'].get(self.jurisdiction, {}), indent=2)}"
        )

    def run(self, state: dict) -> dict:
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
# Agent 1 – India Expert (RBI)
# ─────────────────────────────────────────────────────────────────────────────

class IndiaExpertAgent(BaseAgent):
    name = "IndiaExpert"
    jurisdiction = "RBI"

    def run(self, state: dict) -> dict:
        print(f"\n[{self.name}] Starting analysis...")

        # Tool call 1 — check graph for cycle motifs
        graph_result = neo4j_query_tool(
            "MATCH (a)-[:TRANSFER*2..5]->(a) RETURN a.id AS cycle_id, count(*) as length"
        )
        print(f"  ↳ Neo4j (cycles): {graph_result['rows']}")

        # Tool call 2 — sender KYC
        sender_kyc = account_lookup_tool(state["transaction"]["sender"]["account_id"])
        print(f"  ↳ KYC sender: kyc_status={sender_kyc['kyc_status']}")

        # Tool call 3 — regulatory search
        reg = pinecone_search_tool("cross-border wire EDD threshold India", "RBI", top_k=3)
        print(f"  ↳ RAG rules retrieved: {[r['rule_id'] for r in reg['results']]}")

        verdict = _mock_llm(self._build_system_prompt(), self._build_user_message(state), self.name)

        return {
            "india_expert_verdict": verdict,
            "india_tool_calls": {
                "neo4j": graph_result,
                "sender_kyc": sender_kyc,
                "rag_rules": reg,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 2 – EU Expert (AMLD-6 + EU AI Act)
# ─────────────────────────────────────────────────────────────────────────────

class EUExpertAgent(BaseAgent):
    name = "EUExpert"
    jurisdiction = "EU_AI_ACT"

    def run(self, state: dict) -> dict:
        print(f"\n[{self.name}] Starting analysis...")

        # Tool call — intermediary KYC (sanctions check)
        intermediary_results = []
        for hop in state["transaction"].get("intermediary_hops", []):
            kyc = account_lookup_tool(hop["account_id"])
            intermediary_results.append(kyc)
            print(f"  ↳ KYC {hop['account_id']}: sanctions={kyc['sanctions_hit']}, pep={kyc['pep_flag']}")

        # Tool call — EU regulatory search
        reg = pinecone_search_tool("shell company SAR AMLD-6 beneficial ownership", "EU", top_k=2)
        print(f"  ↳ RAG rules retrieved: {[r['rule_id'] for r in reg['results']]}")

        verdict = _mock_llm(self._build_system_prompt(), self._build_user_message(state), self.name)

        return {
            "eu_expert_verdict": verdict,
            "eu_tool_calls": {
                "intermediary_kyc": intermediary_results,
                "rag_rules": reg,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 3 – The Auditor (Judge)
# ─────────────────────────────────────────────────────────────────────────────

class AuditorAgent(BaseAgent):
    name = "Auditor"
    jurisdiction = "GLOBAL"

    def run(self, state: dict) -> dict:
        print(f"\n[{self.name}] Deliberating on all expert verdicts...")

        # Count how many experts flagged the transaction (India + EU only)
        flags = sum([
            "HIGH RISK" in state.get("india_expert_verdict", ""),
            "HIGH RISK" in state.get("eu_expert_verdict", ""),
        ])
        print(f"  ↳ Expert flags (HIGH RISK): {flags}/2")

        # File SARs if ≥2 experts agree
        sar_filings = []
        if flags >= 2:
            for jur in ["RBI", "EU"]:
                receipt = sar_filing_tool(
                    transaction_id=state["transaction"]["id"],
                    jurisdiction=jur,
                    reason=f"Automated SAR by CCFA Multi-Agent Courtroom. "
                           f"Anomaly score: {state['graph_analysis']['anomaly_score']}. "
                           f"Cycle motifs detected. Shell company probability: "
                           f"{state['graph_analysis']['shell_company_probability']}.",
                    filed_by_agent=self.name,
                )
                sar_filings.append(receipt)
                print(f"  ↳ SAR filed [{jur}]: {receipt['tracking_id']}")

        final_verdict = _mock_llm(
            self._build_system_prompt(),
            (
                f"India Expert:\n{state.get('india_expert_verdict','N/A')}\n\n"
                f"EU Expert:\n{state.get('eu_expert_verdict','N/A')}"
            ),
            self.name,
        )

        return {
            "final_verdict": final_verdict,
            "transaction_frozen": flags >= 2,
            "sar_filings": sar_filings,
            "expert_agreement_flags": flags,
            "auditor_confidence": 0.94,
        }
