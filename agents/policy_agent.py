from __future__ import annotations

from typing import Any

from agents.base import BaseAgent


class PolicyAgent(BaseAgent):
    agent_name = "Policy Agent"
    system_prompt = (
        "You are the Policy Agent. Apply EC_POLICY_V2 in priority order and "
        "return primary issue, secondary issues, root cause, responsible parties, "
        "refund, actions, and evidence IDs. Return only JSON."
    )

    def reason(self, prompt: dict[str, Any]) -> dict[str, Any]:
        order = prompt["order"] or {}
        order_product = prompt["order_product"]
        payment = prompt["payment"]
        delivery = prompt["delivery"]
        order_id = prompt["order_id"]

        order_status = order.get("order_status")
        payment_total = payment["payment_total_brl"]
        freight_total = payment["freight_total_brl"] or 0
        late_delivery = delivery["late_delivery"]
        late_sellers = delivery["late_handoff_seller_ids"]
        split_payment = payment["split_payment"]
        reconciled = payment["reconciled"]

        if order_status == "canceled" and payment_total > 0:
            primary_issue = "canceled_order_paid"
            root_cause = "ORDER_CANCELED_AFTER_PAYMENT"
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            refund = payment_total
            main_action = "issue_full_refund"
        elif order_status == "unavailable" and payment_total > 0:
            primary_issue = "unavailable_order_paid"
            root_cause = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            refund = payment_total
            main_action = "issue_full_refund"
        elif late_delivery and late_sellers:
            primary_issue = "late_delivery_seller"
            root_cause = "SELLER_HANDOFF_AFTER_LIMIT"
            responsible_parties = [
                {"party_type": "seller", "party_id": seller_id} for seller_id in late_sellers[:3]
            ]
            refund = freight_total
            main_action = "refund_freight"
        elif late_delivery and not late_sellers:
            primary_issue = "late_delivery_logistics"
            root_cause = "CARRIER_DELIVERED_AFTER_ESTIMATE"
            responsible_parties = [
                {"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}
            ]
            refund = freight_total
            main_action = "refund_freight"
        elif split_payment and reconciled is True:
            primary_issue = "valid_split_payment"
            root_cause = "MULTIPLE_PAYMENTS_RECONCILED"
            responsible_parties = []
            refund = 0
            main_action = "explain_valid_split_payment"
        else:
            primary_issue = "unsupported_late_claim"
            root_cause = "DELIVERY_WITHIN_ESTIMATE"
            responsible_parties = []
            refund = 0
            main_action = "reject_late_refund"

        secondary_issues = []
        if order_product["multi_item_order"]:
            secondary_issues.append("multi_item_order")
        if order_product["multi_seller_order"]:
            secondary_issues.append("multi_seller_order")
        if split_payment:
            secondary_issues.append("split_payment")
        if prompt["customer"]["repeat_customer"]:
            secondary_issues.append("repeat_customer")
        if order_product["multiple_categories"]:
            secondary_issues.append("multiple_categories")

        actions = [main_action]
        if primary_issue == "late_delivery_seller":
            actions.append("review_seller_handoff")
        elif primary_issue == "late_delivery_logistics":
            actions.append("review_carrier_delay")
        if refund > 0:
            actions.append("verify_refund_completion")
        if order_product["multi_seller_order"]:
            actions.append("coordinate_multi_seller_case")
        if split_payment and primary_issue != "valid_split_payment":
            actions.append("verify_payment_allocation")

        evidence_ids = [f"order:{order_id}"]
        evidence_ids.extend(f"item:{item_id}" for item_id in order_product["item_ids"])
        evidence_ids.extend(f"payment:{payment_id}" for payment_id in payment["payment_ids"])
        for party in responsible_parties:
            if party["party_type"] == "seller":
                evidence_ids.append(f"seller:{party['party_id']}")
        evidence_ids.append(f"policy:{root_cause}")

        return {
            "primary_issue": primary_issue,
            "secondary_issues": secondary_issues,
            "case_status": "action_required" if refund > 0 else "no_action",
            "confidence": _confidence(primary_issue, reconciled),
            "ranked_causes": [{"cause_code": root_cause, "rank": 1}],
            "responsible_parties": responsible_parties[:3],
            "recommended_refund_brl": round(float(refund), 2),
            "resolution_actions": actions[:5],
            "evidence_ids": evidence_ids[:20],
        }

    def normalize(self, prompt: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
        baseline = self.reason(prompt)
        normalized = dict(baseline)
        normalized.update({key: value for key, value in response.items() if value is not None})

        if "recommended_refund_brl" not in normalized:
            normalized["recommended_refund_brl"] = normalized.get("refund_brl", normalized.get("refund", 0))
        normalized["recommended_refund_brl"] = round(float(normalized["recommended_refund_brl"] or 0), 2)
        normalized["case_status"] = (
            normalized.get("case_status")
            or ("action_required" if normalized["recommended_refund_brl"] > 0 else "no_action")
        )
        if normalized["case_status"] not in {"action_required", "no_action"}:
            normalized["case_status"] = (
                "action_required" if normalized["recommended_refund_brl"] > 0 else "no_action"
            )

        normalized["secondary_issues"] = _ordered_subset(
            normalized.get("secondary_issues", []),
            [
                "multi_item_order",
                "multi_seller_order",
                "split_payment",
                "repeat_customer",
                "multiple_categories",
            ],
        )
        normalized["resolution_actions"] = normalized.get("resolution_actions") or normalized.get("actions") or baseline[
            "resolution_actions"
        ]
        normalized["resolution_actions"] = normalized["resolution_actions"][:5]
        normalized["ranked_causes"] = normalized.get("ranked_causes") or baseline["ranked_causes"]
        normalized["ranked_causes"] = normalized["ranked_causes"][:3]
        normalized["responsible_parties"] = normalized.get("responsible_parties") or baseline[
            "responsible_parties"
        ]
        normalized["responsible_parties"] = normalized["responsible_parties"][:3]
        normalized["evidence_ids"] = _repair_evidence_ids(
            normalized.get("evidence_ids") or baseline["evidence_ids"],
            baseline["evidence_ids"],
        )[:20]
        normalized["confidence"] = float(normalized.get("confidence", baseline["confidence"]))
        normalized["confidence"] = min(1.0, max(0.0, normalized["confidence"]))
        return normalized


def _confidence(primary_issue: str, reconciled: bool | None) -> float:
    if primary_issue in {"canceled_order_paid", "unavailable_order_paid"}:
        return 0.94
    if primary_issue in {"late_delivery_seller", "late_delivery_logistics"}:
        return 0.92
    if primary_issue == "valid_split_payment":
        return 0.91
    if reconciled is True:
        return 0.88
    return 0.78


def _ordered_subset(values: list[str], order: list[str]) -> list[str]:
    value_set = set(values)
    return [value for value in order if value in value_set]


def _repair_evidence_ids(values: list[str], baseline: list[str]) -> list[str]:
    valid_prefixes = ("order:", "item:", "payment:", "seller:", "policy:")
    repaired: list[str] = []
    baseline_by_suffix = {item.split(":", 1)[1]: item for item in baseline if ":" in item}
    for value in values:
        if value.startswith(valid_prefixes):
            candidate = value
        else:
            candidate = baseline_by_suffix.get(value)
        if candidate and candidate in baseline and candidate not in repaired:
            repaired.append(candidate)
    for value in baseline:
        if value not in repaired:
            repaired.append(value)
    return repaired
