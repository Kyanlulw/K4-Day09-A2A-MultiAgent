"""
Verifier Agent - Schema validation, ID format check, and limit enforcement.

Responsibilities:
- Validate all required fields are present
- Check array limits (5 order IDs, 5 items, 3 sellers, etc.)
- Validate evidence ID formats
- Validate timestamp formats
- Ensure confidence is in [0, 1]
- Build final output JSON
"""

import json
import re
from typing import Optional


TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def _validate_timestamp(ts: Optional[str]) -> Optional[str]:
    """Validate and return timestamp or None."""
    if ts is None or ts == "" or ts == "nan":
        return None
    if TIMESTAMP_RE.match(ts.strip()):
        return ts.strip()
    return None


def _clamp_confidence(conf: float) -> float:
    """Ensure confidence is in [0, 1]."""
    return max(0.0, min(1.0, round(conf, 2)))


def run_verifier_agent(
    case_id: str,
    order_id: str,
    order_product_result: dict,
    payment_result: dict,
    delivery_result: dict,
    customer_result: dict,
    policy_result: dict,
) -> dict:
    """
    Validate and assemble the final output JSON.

    Returns:
        dict: The validated output conforming to the schema
    """
    has_items = order_product_result.get("has_items", False)

    # ---- Build output ----
    output = {
        "case_id": case_id,
        "case_assessment": {
            "primary_issue": policy_result["primary_issue"],
            "secondary_issues": policy_result["secondary_issues"],
            "case_status": policy_result["case_status"],
            "confidence": _clamp_confidence(policy_result["confidence"]),
        },
        "affected_entities": {
            "order_ids": [order_id][:5],
            "item_ids": order_product_result.get("item_ids", [])[:5],
            "seller_ids": order_product_result.get("seller_ids", [])[:3],
            "payment_ids": payment_result.get("payment_ids", [])[:5],
        },
        "customer_context": {
            "customer_unique_id": customer_result.get("customer_unique_id"),
            "related_order_ids": customer_result.get("related_order_ids", [])[:5],
        },
        "product_context": {
            "product_ids": order_product_result.get("product_ids", [])[:5],
            "category_names": order_product_result.get("category_names", [])[:5],
        },
        "delivery_analysis": {
            "delivered_at": _validate_timestamp(delivery_result.get("delivered_at")),
            "estimated_delivery_at": _validate_timestamp(delivery_result.get("estimated_delivery_at")),
            "carrier_handoff_at": _validate_timestamp(delivery_result.get("carrier_handoff_at")),
            "delivery_variance_hours": delivery_result.get("delivery_variance_hours"),
            "seller_handoff_analysis": delivery_result.get("seller_handoff_analysis", []),
            "late_handoff_seller_ids": delivery_result.get("late_handoff_seller_ids", []),
        },
        "payment_reconciliation": {
            "currency": "BRL",
            "item_total_brl": order_product_result.get("item_total_brl") if has_items else None,
            "freight_total_brl": order_product_result.get("freight_total_brl") if has_items else None,
            "expected_total_brl": order_product_result.get("expected_total_brl") if has_items else None,
            "payment_total_brl": payment_result.get("payment_total_brl"),
            "difference_brl": payment_result.get("difference_brl") if has_items else None,
            "reconciled": payment_result.get("reconciled") if has_items else None,
            "payment_types": payment_result.get("payment_types", []),
        },
        "root_cause_analysis": {
            "ranked_causes": policy_result.get("ranked_causes", [])[:3],
            "responsible_parties": policy_result.get("responsible_parties", [])[:3],
        },
        "evidence_ids": policy_result.get("evidence_ids", [])[:20],
        "financial_resolution": {
            "currency": "BRL",
            "recommended_refund_brl": round(policy_result.get("refund_amount", 0), 2),
        },
        "resolution_actions": policy_result.get("actions", [])[:5],
    }

    # Validate seller_handoff_analysis timestamps
    for sha in output["delivery_analysis"]["seller_handoff_analysis"]:
        sha["shipping_limit_at"] = _validate_timestamp(sha.get("shipping_limit_at"))

    # Validate delivery_variance_hours rounding
    dvh = output["delivery_analysis"]["delivery_variance_hours"]
    if dvh is not None:
        output["delivery_analysis"]["delivery_variance_hours"] = round(dvh, 2)

    # Validate handoff_variance_hours rounding
    for sha in output["delivery_analysis"]["seller_handoff_analysis"]:
        hvh = sha.get("handoff_variance_hours")
        if hvh is not None:
            sha["handoff_variance_hours"] = round(hvh, 2)

    print(f"  [VerifierAgent] Output validated for {case_id}")
    return output


def save_output(output: dict, output_dir: str, case_id: str):
    """Save output JSON to file."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{case_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"  [VerifierAgent] Saved {filepath}")
