from typing import Any

from tools.llm_client import ask_llm


PAYMENT_AGENT_PROMPT = """
You are the Payment Investigation Agent for an Olist complaint.
Use only supplied data. Calculate sums from item price, freight_value, and
payment_value. Round BRL values to two decimals. Do not invent any payment.

Return exactly this JSON object:
{
  "currency": "BRL",
  "item_total_brl": "number or null",
  "freight_total_brl": "number or null",
  "expected_total_brl": "number or null",
  "payment_total_brl": "number",
  "difference_brl": "number or null",
  "reconciled": "boolean or null",
  "payment_types": ["payment_type"],
  "payment_ids": ["order_id:payment_sequential"],
  "evidence_summary": ["fact grounded in supplied data"]
}

If there are no item rows, item_total_brl, freight_total_brl,
expected_total_brl, difference_brl and reconciled must be null.
Do not decide the issue, responsibility, refund, or action.
"""


def run_payment_agent(case_context: dict[str, Any]) -> dict[str, Any]:
    """Ask the LLM to reconcile the supplied payment and item facts."""
    payload = {
        "case": case_context["case"],
        "order": case_context["order"],
        "items": case_context["items"],
        "payments": case_context["payments"],
    }
    return ask_llm(PAYMENT_AGENT_PROMPT, payload)
