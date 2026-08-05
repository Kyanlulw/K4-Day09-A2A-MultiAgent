"""
Policy Agent (LLM-based) - Applies EC_POLICY_V2 using Groq Llama 3.1-8B.

Uses LLM reasoning to:
- Classify primary_issue from evidence
- Determine responsible parties
- Calculate refund amount
- Build evidence_ids and resolution_actions
"""

import json
from tools.llm_client import llm_json_call


POLICY_SYSTEM_PROMPT = """You are an E-commerce Dispute Resolution Policy Agent. You apply EC_POLICY_V2 rules to classify customer complaints.

## EC_POLICY_V2 Rules (STRICT priority order - check from top to bottom, first match wins):

| # | Primary issue             | Condition                                                                          | Responsible party                           | Refund         | Action                        |
|---|---------------------------|------------------------------------------------------------------------------------|---------------------------------------------|----------------|-------------------------------|
| 1 | canceled_order_paid       | order_status = canceled AND total_payment > 0                                      | platform / OLIST_PLATFORM                   | Total payment  | issue_full_refund             |
| 2 | unavailable_order_paid    | order_status = unavailable AND total_payment > 0                                   | platform / OLIST_PLATFORM                   | Total payment  | issue_full_refund             |
| 3 | late_delivery_seller      | Delivered AFTER estimated date AND carrier received goods AFTER at least one seller's shipping_limit_date | seller / the violating seller(s)            | Total freight  | refund_freight                |
| 4 | late_delivery_logistics   | Delivered AFTER estimated date AND NO seller handed off late                        | logistics_provider / LOGISTICS_PROVIDER     | Total freight  | refund_freight                |
| 5 | valid_split_payment       | 2+ payment rows AND abs(payment_total - expected_total) <= 0.10 BRL                | None                                        | 0              | explain_valid_split_payment   |
| 6 | unsupported_late_claim    | Delivery NOT late AND payment reconciled                                           | None                                        | 0              | reject_late_refund            |

## Secondary issues (add ALL that apply, in this order):
1. multi_item_order: 2+ item rows
2. multi_seller_order: 2+ distinct sellers
3. split_payment: 2+ payment rows
4. repeat_customer: customer has other orders
5. multiple_categories: 2+ distinct product categories

## Root-cause codes (use the one matching the primary issue):
- SELLER_HANDOFF_AFTER_LIMIT (for late_delivery_seller)
- CARRIER_DELIVERED_AFTER_ESTIMATE (for late_delivery_logistics)
- ORDER_CANCELED_AFTER_PAYMENT (for canceled_order_paid)
- ORDER_UNAVAILABLE_AFTER_PAYMENT (for unavailable_order_paid)
- MULTIPLE_PAYMENTS_RECONCILED (for valid_split_payment)
- DELIVERY_WITHIN_ESTIMATE (for unsupported_late_claim)

## Additional actions (add after main action, in this order, if conditions met):
- review_seller_handoff (if primary is late_delivery_seller)
- review_carrier_delay (if primary is late_delivery_logistics)
- verify_refund_completion (if refund > 0)
- coordinate_multi_seller_case (if multi_seller_order secondary)
- verify_payment_allocation (UNLESS primary is valid_split_payment)

## case_status:
- "action_required": if refund > 0
- "no_action": if refund = 0

## Evidence ID formats:
- order:<order_id>
- item:<order_id>:<order_item_id>
- payment:<order_id>:<payment_sequential>
- seller:<seller_id> (only for responsible sellers)
- policy:<root_cause_code>

You MUST respond with valid JSON only. Round all money values to 2 decimal places. Confidence should be between 0.85 and 0.99."""


def _build_evidence_context(
    order_id: str,
    order_data: dict,
    order_product_result: dict,
    payment_result: dict,
    delivery_result: dict,
    customer_result: dict,
) -> str:
    """Build a structured evidence summary for the LLM."""
    lines = []

    # Order info
    lines.append("## ORDER DATA")
    if order_data:
        lines.append(f"- order_id: {order_id}")
        lines.append(f"- order_status: {order_data.get('order_status', 'unknown')}")
    else:
        lines.append("- ORDER NOT FOUND IN DATASET")

    # Items & sellers
    lines.append("\n## ITEMS & PRODUCTS")
    items_raw = order_product_result.get("items_raw", [])
    lines.append(f"- item_count: {len(items_raw)}")
    lines.append(f"- item_ids: {order_product_result.get('item_ids', [])}")
    lines.append(f"- seller_ids: {order_product_result.get('seller_ids', [])}")
    lines.append(f"- unique_seller_count: {len(order_product_result.get('seller_ids', []))}")
    lines.append(f"- product_ids: {order_product_result.get('product_ids', [])}")
    lines.append(f"- category_names: {order_product_result.get('category_names', [])}")
    lines.append(f"- item_total_brl: {order_product_result.get('item_total_brl')}")
    lines.append(f"- freight_total_brl: {order_product_result.get('freight_total_brl')}")
    lines.append(f"- expected_total_brl: {order_product_result.get('expected_total_brl')}")
    lines.append(f"- has_items: {order_product_result.get('has_items')}")

    # Payment
    lines.append("\n## PAYMENT DATA")
    lines.append(f"- payment_count: {payment_result.get('payment_count', 0)}")
    lines.append(f"- payment_ids: {payment_result.get('payment_ids', [])}")
    lines.append(f"- payment_total_brl: {payment_result.get('payment_total_brl')}")
    lines.append(f"- payment_types: {payment_result.get('payment_types', [])}")
    lines.append(f"- difference_brl: {payment_result.get('difference_brl')}")
    lines.append(f"- reconciled: {payment_result.get('reconciled')}")

    # Delivery
    lines.append("\n## DELIVERY DATA")
    lines.append(f"- delivered_at: {delivery_result.get('delivered_at')}")
    lines.append(f"- estimated_delivery_at: {delivery_result.get('estimated_delivery_at')}")
    lines.append(f"- carrier_handoff_at: {delivery_result.get('carrier_handoff_at')}")
    lines.append(f"- delivery_variance_hours: {delivery_result.get('delivery_variance_hours')}")
    lines.append(f"- is_late_delivery: {delivery_result.get('is_late_delivery')}")
    lines.append(f"- seller_handoff_analysis: {json.dumps(delivery_result.get('seller_handoff_analysis', []))}")
    lines.append(f"- late_handoff_seller_ids: {delivery_result.get('late_handoff_seller_ids', [])}")

    # Customer
    lines.append("\n## CUSTOMER DATA")
    lines.append(f"- customer_unique_id: {customer_result.get('customer_unique_id')}")
    lines.append(f"- related_order_ids: {customer_result.get('related_order_ids', [])}")
    lines.append(f"- is_repeat_customer: {len(customer_result.get('related_order_ids', [])) > 0}")

    return "\n".join(lines)


def run_policy_agent(
    order_id: str,
    order_data: dict,
    order_product_result: dict,
    payment_result: dict,
    delivery_result: dict,
    customer_result: dict,
) -> dict:
    """
    Use LLM to apply EC_POLICY_V2 rules and classify the case.

    Returns:
        dict with policy classification results
    """
    evidence = _build_evidence_context(
        order_id, order_data, order_product_result,
        payment_result, delivery_result, customer_result,
    )

    user_prompt = f"""Analyze this e-commerce dispute case and classify it according to EC_POLICY_V2.

{evidence}

Based on the evidence above, respond with a JSON object containing:
{{
  "primary_issue": "<one of: canceled_order_paid, unavailable_order_paid, late_delivery_seller, late_delivery_logistics, valid_split_payment, unsupported_late_claim>",
  "secondary_issues": ["<list of applicable secondary issues in order>"],
  "case_status": "<action_required or no_action>",
  "confidence": <float between 0.85-0.99>,
  "responsible_parties": [
    {{"party_type": "<seller|platform|logistics_provider>", "party_id": "<ID>"}}
  ],
  "ranked_causes": [
    {{"cause_code": "<ROOT_CAUSE_CODE>", "rank": 1}}
  ],
  "evidence_ids": ["<list of evidence IDs>"],
  "refund_amount": <float>,
  "actions": ["<list of resolution actions in order>"],
  "reasoning": "<brief explanation of your classification>"
}}"""

    print(f"  [PolicyAgent-LLM] Calling Groq Llama 3.1-8B...")

    try:
        llm_result = llm_json_call(
            system_prompt=POLICY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=2048,
        )

        # Validate and normalize required fields
        result = {
            "primary_issue": llm_result.get("primary_issue", "unsupported_late_claim"),
            "secondary_issues": llm_result.get("secondary_issues", []),
            "case_status": llm_result.get("case_status", "no_action"),
            "confidence": max(0.0, min(1.0, float(llm_result.get("confidence", 0.90)))),
            "responsible_parties": llm_result.get("responsible_parties", [])[:3],
            "ranked_causes": llm_result.get("ranked_causes", [])[:3],
            "evidence_ids": llm_result.get("evidence_ids", [])[:20],
            "refund_amount": round(float(llm_result.get("refund_amount", 0)), 2),
            "actions": llm_result.get("actions", [])[:5],
        }

        reasoning = llm_result.get("reasoning", "")
        print(f"  [PolicyAgent-LLM] Result: primary={result['primary_issue']}, "
              f"status={result['case_status']}, "
              f"refund={result['refund_amount']}")
        if reasoning:
            print(f"  [PolicyAgent-LLM] Reasoning: {reasoning[:120]}...")

        return result

    except Exception as e:
        print(f"  [PolicyAgent-LLM] ERROR: {e}")
        print(f"  [PolicyAgent-LLM] Falling back to rule-based classification...")
        return _fallback_rule_based(
            order_id, order_data, order_product_result,
            payment_result, delivery_result, customer_result,
        )


def _fallback_rule_based(
    order_id, order_data, order_product_result,
    payment_result, delivery_result, customer_result,
):
    """Fallback to deterministic rules if LLM call fails."""
    order_status = order_data.get("order_status", "") if order_data else ""
    payment_total = payment_result.get("payment_total_brl", 0) or 0
    payment_count = payment_result.get("payment_count", 0)
    is_late = delivery_result.get("is_late_delivery", False)
    late_sellers = delivery_result.get("late_handoff_seller_ids", [])
    freight_total = order_product_result.get("freight_total_brl", 0) or 0
    reconciled = payment_result.get("reconciled")
    items_raw = order_product_result.get("items_raw", [])
    item_ids = order_product_result.get("item_ids", [])
    seller_ids = order_product_result.get("seller_ids", [])
    payment_ids = payment_result.get("payment_ids", [])
    category_names = order_product_result.get("category_names", [])

    primary_issue = None
    responsible_parties = []
    cause_code = None
    refund_amount = 0.0
    case_status = "no_action"
    actions = []

    if order_status == "canceled" and payment_total > 0:
        primary_issue = "canceled_order_paid"
        responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
        cause_code = "ORDER_CANCELED_AFTER_PAYMENT"
        refund_amount = payment_total
        case_status = "action_required"
        actions.append("issue_full_refund")
    elif order_status == "unavailable" and payment_total > 0:
        primary_issue = "unavailable_order_paid"
        responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
        cause_code = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
        refund_amount = payment_total
        case_status = "action_required"
        actions.append("issue_full_refund")
    elif is_late and len(late_sellers) > 0:
        primary_issue = "late_delivery_seller"
        responsible_parties = [{"party_type": "seller", "party_id": sid} for sid in late_sellers[:3]]
        cause_code = "SELLER_HANDOFF_AFTER_LIMIT"
        refund_amount = freight_total
        case_status = "action_required"
        actions.append("refund_freight")
    elif is_late and len(late_sellers) == 0:
        primary_issue = "late_delivery_logistics"
        responsible_parties = [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
        cause_code = "CARRIER_DELIVERED_AFTER_ESTIMATE"
        refund_amount = freight_total
        case_status = "action_required"
        actions.append("refund_freight")
    elif payment_count >= 2 and reconciled is True:
        primary_issue = "valid_split_payment"
        cause_code = "MULTIPLE_PAYMENTS_RECONCILED"
        actions.append("explain_valid_split_payment")
    else:
        primary_issue = "unsupported_late_claim"
        cause_code = "DELIVERY_WITHIN_ESTIMATE"
        actions.append("reject_late_refund")

    secondary_issues = []
    if len(items_raw) >= 2:
        secondary_issues.append("multi_item_order")
    all_sellers_set = list({item.get("seller_id", "") for item in items_raw if item.get("seller_id", "")})
    if len(all_sellers_set) >= 2:
        secondary_issues.append("multi_seller_order")
    if payment_count >= 2:
        secondary_issues.append("split_payment")
    if len(customer_result.get("related_order_ids", [])) > 0:
        secondary_issues.append("repeat_customer")
    if len(category_names) >= 2:
        secondary_issues.append("multiple_categories")

    if primary_issue == "late_delivery_seller":
        actions.append("review_seller_handoff")
    elif primary_issue == "late_delivery_logistics":
        actions.append("review_carrier_delay")
    if refund_amount > 0:
        actions.append("verify_refund_completion")
    if "multi_seller_order" in secondary_issues:
        actions.append("coordinate_multi_seller_case")
    if primary_issue != "valid_split_payment":
        actions.append("verify_payment_allocation")

    evidence_ids = [f"order:{order_id}"]
    for iid in item_ids:
        evidence_ids.append(f"item:{iid}")
    for pid in payment_ids:
        evidence_ids.append(f"payment:{pid}")
    for rp in responsible_parties:
        if rp["party_type"] == "seller":
            evidence_ids.append(f"seller:{rp['party_id']}")
    evidence_ids.append(f"policy:{cause_code}")

    return {
        "primary_issue": primary_issue,
        "secondary_issues": secondary_issues,
        "case_status": case_status,
        "confidence": 0.95,
        "responsible_parties": responsible_parties[:3],
        "ranked_causes": [{"cause_code": cause_code, "rank": 1}],
        "evidence_ids": evidence_ids[:20],
        "refund_amount": round(refund_amount, 2),
        "actions": actions[:5],
    }
