from typing import Any


REQUIRED_TOP_LEVEL = {
    "case_id",
    "case_assessment",
    "affected_entities",
    "customer_context",
    "product_context",
    "delivery_analysis",
    "payment_reconciliation",
    "root_cause_analysis",
    "evidence_ids",
    "financial_resolution",
    "resolution_actions",
}


def validate_output(output: dict[str, Any], expected_case_id: str) -> None:
    """Validate output shape only; policy decisions remain LLM-owned."""
    missing = REQUIRED_TOP_LEVEL.difference(output)
    if missing:
        raise ValueError(f"Missing top-level fields: {sorted(missing)}")
    if output["case_id"] != expected_case_id:
        raise ValueError("case_id does not match the input case")

    assessment = output["case_assessment"]
    if not isinstance(assessment, dict):
        raise ValueError("case_assessment must be an object")
    for field in ("primary_issue", "secondary_issues", "case_status", "confidence"):
        if field not in assessment:
            raise ValueError(f"case_assessment.{field} is required")

    entities = output["affected_entities"]
    for field in ("order_ids", "item_ids", "seller_ids", "payment_ids"):
        if field not in entities or not isinstance(entities[field], list):
            raise ValueError(f"affected_entities.{field} must be a list")

    for field in ("ranked_causes", "responsible_parties"):
        if field not in output["root_cause_analysis"]:
            raise ValueError(f"root_cause_analysis.{field} is required")

    list_limits = {
        "order_ids": 5,
        "item_ids": 5,
        "seller_ids": 3,
        "payment_ids": 5,
    }
    for field, maximum in list_limits.items():
        if len(entities[field]) > maximum:
            raise ValueError(f"affected_entities.{field} exceeds {maximum}")
    if len(output["evidence_ids"]) > 20 or len(output["resolution_actions"]) > 5:
        raise ValueError("evidence_ids or resolution_actions exceeds its limit")
