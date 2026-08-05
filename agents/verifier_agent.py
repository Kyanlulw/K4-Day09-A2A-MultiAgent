from __future__ import annotations

import re
from typing import Any

from agents.base import BaseAgent


class VerifierAgent(BaseAgent):
    agent_name = "Verifier Agent"
    system_prompt = (
        "You are the Verifier Agent. Validate final Olist dispute JSON against "
        "schema limits, evidence format, and field consistency. Return only JSON."
    )

    def reason(self, prompt: dict[str, Any]) -> dict[str, Any]:
        output = prompt["output"]
        issues: list[str] = []

        assessment = output.get("case_assessment", {})
        confidence = assessment.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            issues.append("confidence_out_of_range")

        limits = {
            ("affected_entities", "order_ids"): 5,
            ("affected_entities", "item_ids"): 5,
            ("affected_entities", "seller_ids"): 3,
            ("affected_entities", "payment_ids"): 5,
            ("customer_context", "related_order_ids"): 5,
            ("product_context", "product_ids"): 5,
            ("product_context", "category_names"): 5,
            ("root_cause_analysis", "ranked_causes"): 3,
            ("root_cause_analysis", "responsible_parties"): 3,
            ("", "evidence_ids"): 20,
            ("", "resolution_actions"): 5,
        }
        for (section, field), limit in limits.items():
            value = output[field] if section == "" else output[section][field]
            if len(value) > limit:
                issues.append(f"{field}_over_limit")

        for evidence_id in output.get("evidence_ids", []):
            if not _valid_evidence_id(evidence_id):
                issues.append(f"invalid_evidence_id:{evidence_id}")

        expected_status = (
            "action_required"
            if output["financial_resolution"]["recommended_refund_brl"] > 0
            else "no_action"
        )
        if output["case_assessment"]["case_status"] != expected_status:
            issues.append("case_status_refund_mismatch")

        return {"valid": not issues, "issues": issues, "checked_by": self.agent_name}

    def normalize(self, prompt: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
        baseline = self.reason(prompt)
        return {
            "valid": baseline["valid"],
            "issues": baseline["issues"],
            "checked_by": self.agent_name,
            "llm_review": response,
        }


def _valid_evidence_id(evidence_id: str) -> bool:
    patterns = [
        r"^order:[0-9a-f]+$",
        r"^item:[0-9a-f]+:\d+$",
        r"^payment:[0-9a-f]+:\d+$",
        r"^seller:[0-9a-f]+$",
        r"^policy:[A-Z_]+$",
    ]
    return any(re.match(pattern, evidence_id) for pattern in patterns)
