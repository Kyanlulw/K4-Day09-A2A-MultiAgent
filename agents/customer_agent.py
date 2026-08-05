from __future__ import annotations

from typing import Any

from agents.base import BaseAgent


class CustomerAgent(BaseAgent):
    agent_name = "Customer Agent"
    system_prompt = (
        "You are the Customer Agent. Infer customer identity and repeat-customer "
        "context from the provided Olist evidence. Return only JSON."
    )

    def reason(self, prompt: dict[str, Any]) -> dict[str, Any]:
        customer = prompt.get("customer") or {}
        related_order_ids = prompt.get("related_order_ids") or []
        return {
            "customer_unique_id": customer.get("customer_unique_id"),
            "related_order_ids": related_order_ids[:5],
            "repeat_customer": len(related_order_ids) > 0,
        }

    def normalize(self, prompt: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
        normalized = self.reason(prompt)
        normalized["llm_assessment"] = response
        return normalized
