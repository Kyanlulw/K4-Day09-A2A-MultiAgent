from typing import Any

from tools.llm_client import ask_llm


ORDER_PRODUCT_AGENT_PROMPT = """
You are the Order and Product Investigation Agent for an Olist complaint.

Use only the supplied JSON data. Do not invent facts or IDs.

Your job is to extract verifiable facts about the current order:
- order_id
- item IDs in the exact format "<order_id>:<order_item_id>"
- seller IDs found in item rows
- product IDs found in item rows
- product category names found in supplied product records
- concise evidence summaries grounded in the supplied data

Do not decide a primary issue, responsibility, refund, policy action, or
whether the order is late. Those decisions belong to a later Policy Agent.

Return exactly one JSON object with this schema:
{
  "order_id": "string or null",
  "item_ids": ["order_id:item_id"],
  "seller_ids": ["seller_id"],
  "product_ids": ["product_id"],
  "category_names": ["category_name"],
  "evidence_summary": ["fact grounded in the supplied data"]
}
"""


def run_order_product_agent(
    case_context: dict[str, Any],
) -> dict[str, Any]:
    """Send order, item, and product facts to the LLM for extraction."""
    payload = {
        "case": case_context["case"],
        "order": case_context["order"],
        "items": case_context["items"],
        "products": case_context["products"],
    }

    return ask_llm(ORDER_PRODUCT_AGENT_PROMPT, payload)
