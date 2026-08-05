from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


class OlistDataStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.data_dir = root / "data"
        self.inputs_dir = root / "input"
        self.orders = self._read_csv("olist_orders_dataset.csv")
        self.customers = self._read_csv("olist_customers_dataset.csv")
        self.items = self._read_csv("olist_order_items_dataset.csv")
        self.payments = self._read_csv("olist_order_payments_dataset.csv")
        self.products = self._read_csv("olist_products_dataset.csv")
        self.sellers = self._read_csv("olist_sellers_dataset.csv")
        self.reviews = self._read_csv("olist_order_reviews_dataset.csv")
        self.geolocation = self._read_csv("olist_geolocation_dataset.csv")
        self.category_translations = self._read_csv("product_category_name_translation.csv")

        self.orders_by_id = {row["order_id"]: row for row in self.orders}
        self.customers_by_id = {row["customer_id"]: row for row in self.customers}
        self.items_by_order = self._group_by(self.items, "order_id")
        self.payments_by_order = self._group_by(self.payments, "order_id")
        self.products_by_id = {row["product_id"]: row for row in self.products}
        self.sellers_by_id = {row["seller_id"]: row for row in self.sellers}
        self.translation_by_category = {
            row["product_category_name"]: row.get("product_category_name_english") or row["product_category_name"]
            for row in self.category_translations
        }
        self.orders_by_customer_unique = self._index_orders_by_customer_unique()

    def load_cases(self) -> list[dict[str, Any]]:
        cases = []
        for path in sorted(self.inputs_dir.glob("EC_*.json")):
            with path.open("r", encoding="utf-8") as handle:
                cases.append(json.load(handle))
        return cases

    def retrieve_case_evidence(self, case: dict[str, Any]) -> dict[str, Any]:
        order_id = case["customer_request"]["claimed_order_id"]
        order = self.orders_by_id.get(order_id)
        items = self.items_by_order.get(order_id, [])
        payments = self.payments_by_order.get(order_id, [])
        customer = self.customers_by_id.get(order["customer_id"], {}) if order else {}
        products = [self.products_by_id.get(item["product_id"], {}) for item in items]
        sellers = [self.sellers_by_id.get(item["seller_id"], {}) for item in items]
        related_order_ids: list[str] = []
        if customer:
            unique_id = customer.get("customer_unique_id")
            related_order_ids = [
                oid
                for oid in self.orders_by_customer_unique.get(unique_id, [])
                if oid != order_id
            ]

        return {
            "case": case,
            "order": order,
            "customer": customer,
            "items": items,
            "payments": payments,
            "products": products,
            "sellers": sellers,
            "related_order_ids": related_order_ids,
            "category_translations": self.translation_by_category,
        }

    def _read_csv(self, name: str) -> list[dict[str, str]]:
        path = self.data_dir / name
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def _group_by(self, rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            grouped[row[key]].append(row)
        return dict(grouped)

    def _index_orders_by_customer_unique(self) -> dict[str, list[str]]:
        by_unique: dict[str, list[str]] = defaultdict(list)
        for order in self.orders:
            customer = self.customers_by_id.get(order["customer_id"])
            if customer:
                by_unique[customer["customer_unique_id"]].append(order["order_id"])
        return dict(by_unique)

