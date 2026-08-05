from __future__ import annotations

from typing import Any

from agents.base import BaseAgent


class OrderProductAgent(BaseAgent):
    agent_name = "Order & Product Agent"
    system_prompt = (
        "You are the Order & Product Agent. Infer affected items, sellers, "
        "products, categories, and order structure from Olist evidence. Return only JSON."
    )

    def reason(self, prompt: dict[str, Any]) -> dict[str, Any]:
        order_id = prompt["order_id"]
        items = prompt.get("items") or []
        products = prompt.get("products") or []
        translations = prompt.get("category_translations") or {}

        item_ids = [f"{order_id}:{item['order_item_id']}" for item in items]
        seller_ids = _unique([item["seller_id"] for item in items if item.get("seller_id")])
        product_ids = _unique([item["product_id"] for item in items if item.get("product_id")])

        category_names: list[str] = []
        for product in products:
            category = product.get("product_category_name")
            if not category:
                continue
            category_names.append(translations.get(category, category))
        category_names = _unique(category_names)

        return {
            "item_ids": item_ids[:5],
            "seller_ids": seller_ids[:3],
            "all_seller_ids": seller_ids,
            "product_ids": product_ids[:5],
            "category_names": category_names[:5],
            "multi_item_order": len(items) >= 2,
            "multi_seller_order": len(seller_ids) >= 2,
            "multiple_categories": len(category_names) >= 2,
        }

    def normalize(self, prompt: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
        normalized = self.reason(prompt)
        normalized.update({key: value for key, value in response.items() if value is not None})
        normalized["item_ids"] = normalized["item_ids"][:5]
        normalized["seller_ids"] = normalized["seller_ids"][:3]
        normalized["product_ids"] = normalized["product_ids"][:5]
        normalized["category_names"] = normalized["category_names"][:5]
        normalized["multi_item_order"] = len(prompt.get("items") or []) >= 2
        normalized["multi_seller_order"] = len(normalized.get("all_seller_ids") or normalized["seller_ids"]) >= 2
        normalized["multiple_categories"] = len(normalized["category_names"]) >= 2
        return normalized


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values
