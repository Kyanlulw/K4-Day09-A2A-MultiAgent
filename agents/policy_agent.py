from typing import Any

from tools.llm_client import ask_llm


POLICY_PROMPT = """
You are the final Policy Agent. Apply EC_POLICY_V2 by reasoning from supplied
agent evidence only. Never invent an ID, timestamp, seller, payment, or event.
Return one JSON object ONLY, with every field below. No markdown.

{
 "case_id":"EC_XXX",
 "case_assessment":{"primary_issue":"string","secondary_issues":[],"case_status":"action_required or no_action","confidence":0.0},
 "affected_entities":{"order_ids":[],"item_ids":[],"seller_ids":[],"payment_ids":[]},
 "customer_context":{"customer_unique_id":"string or null","related_order_ids":[]},
 "product_context":{"product_ids":[],"category_names":[]},
 "delivery_analysis":{"delivered_at":"timestamp or null","estimated_delivery_at":"timestamp or null","carrier_handoff_at":"timestamp or null","delivery_variance_hours":"number or null","seller_handoff_analysis":[],"late_handoff_seller_ids":[]},
 "payment_reconciliation":{"currency":"BRL","item_total_brl":"number or null","freight_total_brl":"number or null","expected_total_brl":"number or null","payment_total_brl":"number","difference_brl":"number or null","reconciled":"boolean or null","payment_types":[]},
 "root_cause_analysis":{"ranked_causes":[],"responsible_parties":[]},
 "evidence_ids":[],
 "financial_resolution":{"currency":"BRL","recommended_refund_brl":0.0},
 "resolution_actions":[]
}

Allowed primary issues: canceled_order_paid, unavailable_order_paid,
late_delivery_seller, late_delivery_logistics, valid_split_payment,
unsupported_late_claim. Only use evidence IDs: order:<order>, item:<order>:<item>,
payment:<order>:<sequential>, seller:<seller>, policy:<cause>. Keep limits from
the assignment. EC_POLICY_V2 priority is canceled paid, unavailable paid, seller
late handoff delivery, logistics late delivery, reconciled split payment, then
unsupported late claim. Secondary ordering is multi_item_order, multi_seller_order,
split_payment, repeat_customer, multiple_categories.
"""


def run_policy_agent(context: dict[str, Any], customer: dict[str, Any], order_product: dict[str, Any], payment: dict[str, Any], delivery: dict[str, Any]) -> dict[str, Any]:
    return ask_llm(POLICY_PROMPT, {"context": context, "customer_agent": customer, "order_product_agent": order_product, "payment_agent": payment, "delivery_agent": delivery})
