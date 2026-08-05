from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from agents.base import BaseAgent


class PaymentAgent(BaseAgent):
    agent_name = "Payment Agent"
    system_prompt = (
        "You are the Payment Agent. Calculate Olist payment reconciliation: "
        "item total, freight total, expected total, payment total, difference, "
        "and whether abs(difference) <= 0.10 BRL. Return only JSON."
    )

    def reason(self, prompt: dict[str, Any]) -> dict[str, Any]:
        order_id = prompt["order_id"]
        items = prompt.get("items") or []
        payments = prompt.get("payments") or []
        payment_ids = [f"{order_id}:{payment['payment_sequential']}" for payment in payments]
        payment_types = _unique([payment["payment_type"] for payment in payments if payment.get("payment_type")])
        payment_total = _sum_money(payment.get("payment_value") for payment in payments)

        if not items:
            item_total = freight_total = expected_total = difference = None
            reconciled = None
        else:
            item_total = _sum_money(item.get("price") for item in items)
            freight_total = _sum_money(item.get("freight_value") for item in items)
            expected_total = _round_money(Decimal(str(item_total)) + Decimal(str(freight_total)))
            difference = _round_money(Decimal(str(payment_total)) - Decimal(str(expected_total)))
            reconciled = abs(Decimal(str(difference))) <= Decimal("0.10")

        return {
            "currency": "BRL",
            "item_total_brl": item_total,
            "freight_total_brl": freight_total,
            "expected_total_brl": expected_total,
            "payment_total_brl": payment_total,
            "difference_brl": difference,
            "reconciled": reconciled,
            "payment_types": payment_types[:5],
            "payment_ids": payment_ids[:5],
            "split_payment": len(payments) >= 2,
            "payment_row_count": len(payments),
        }

    def normalize(self, prompt: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
        normalized = self.reason(prompt)
        normalized["llm_assessment"] = response
        return normalized


def _sum_money(values: Any) -> float:
    total = Decimal("0")
    for value in values:
        if value not in (None, ""):
            total += Decimal(str(value))
    return _round_money(total)


def _round_money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
