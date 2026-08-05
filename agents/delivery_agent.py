from typing import Any

from tools.llm_client import ask_llm


DELIVERY_AGENT_PROMPT = """
You are the Delivery Investigation Agent for an Olist complaint.
Use only timestamps and item rows supplied in JSON. Calculate hour differences
when both values exist, rounded to two decimals. A seller handoff analysis
must use each seller's shipping_limit_date and the order's
order_delivered_carrier_date.

Return exactly this JSON object:
{
  "delivered_at": "timestamp or null",
  "estimated_delivery_at": "timestamp or null",
  "carrier_handoff_at": "timestamp or null",
  "delivery_variance_hours": "number or null",
  "seller_handoff_analysis": [
    {
      "seller_id": "string",
      "shipping_limit_at": "timestamp or null",
      "handoff_variance_hours": "number or null",
      "late_handoff": "boolean or null"
    }
  ],
  "late_handoff_seller_ids": ["seller_id"],
  "evidence_summary": ["fact grounded in supplied data"]
}

Do not decide the final issue, responsibility, refund, or action.
"""


def run_delivery_agent(case_context: dict[str, Any]) -> dict[str, Any]:
    """Ask the LLM to analyse delivery timestamps and handoff facts."""
    payload = {
        "case": case_context["case"],
        "order": case_context["order"],
        "items": case_context["items"],
    }
    return ask_llm(DELIVERY_AGENT_PROMPT, payload)
