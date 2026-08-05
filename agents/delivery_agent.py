from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from agents.base import BaseAgent


class DeliveryAgent(BaseAgent):
    agent_name = "Delivery Agent"
    system_prompt = (
        "You are the Delivery Agent. Calculate delivery variance and seller "
        "handoff variance in hours from Olist timestamps. Return only JSON."
    )

    def reason(self, prompt: dict[str, Any]) -> dict[str, Any]:
        order = prompt.get("order") or {}
        items = prompt.get("items") or []
        delivered_at = _none_if_empty(order.get("order_delivered_customer_date"))
        estimated_at = _none_if_empty(order.get("order_estimated_delivery_date"))
        carrier_handoff_at = _none_if_empty(order.get("order_delivered_carrier_date"))

        delivery_variance_hours = _hours_between(delivered_at, estimated_at)
        by_seller: dict[str, list[str]] = {}
        for item in items:
            by_seller.setdefault(item["seller_id"], []).append(item["shipping_limit_date"])

        seller_handoff_analysis = []
        late_handoff_seller_ids = []
        for seller_id in _stable_keys(by_seller):
            shipping_limit_at = min(by_seller[seller_id])
            variance = _hours_between(carrier_handoff_at, shipping_limit_at)
            late_handoff = bool(variance is not None and variance > 0)
            if late_handoff:
                late_handoff_seller_ids.append(seller_id)
            seller_handoff_analysis.append(
                {
                    "seller_id": seller_id,
                    "shipping_limit_at": shipping_limit_at,
                    "handoff_variance_hours": variance,
                    "late_handoff": late_handoff,
                }
            )

        return {
            "delivered_at": delivered_at,
            "estimated_delivery_at": estimated_at,
            "carrier_handoff_at": carrier_handoff_at,
            "delivery_variance_hours": delivery_variance_hours,
            "seller_handoff_analysis": seller_handoff_analysis[:3],
            "late_handoff_seller_ids": late_handoff_seller_ids[:3],
            "late_delivery": bool(delivery_variance_hours is not None and delivery_variance_hours > 0),
        }

    def normalize(self, prompt: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
        normalized = self.reason(prompt)
        normalized.update({key: value for key, value in response.items() if value is not None})
        normalized["seller_handoff_analysis"] = normalized["seller_handoff_analysis"][:3]
        normalized["late_handoff_seller_ids"] = normalized["late_handoff_seller_ids"][:3]
        variance = normalized.get("delivery_variance_hours")
        normalized["late_delivery"] = bool(variance is not None and variance > 0)
        return normalized


def _none_if_empty(value: str | None) -> str | None:
    return value if value else None


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def _hours_between(left: str | None, right: str | None) -> float | None:
    left_dt = _parse(left)
    right_dt = _parse(right)
    if left_dt is None or right_dt is None:
        return None
    hours = Decimal(str((left_dt - right_dt).total_seconds())) / Decimal("3600")
    return float(hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _stable_keys(mapping: dict[str, Any]) -> list[str]:
    return list(mapping.keys())
