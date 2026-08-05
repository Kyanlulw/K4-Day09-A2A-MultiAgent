"""
Data Loader - Load and index all 9 Olist CSV files.
Provides O(1) lookup by order_id for all datasets.
"""

import pandas as pd
import os
from typing import Optional


class OlistDataLoader:
    """Singleton-style data loader for all Olist CSV datasets."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self._load_all()

    def _load_all(self):
        """Load all 9 CSV files and build indexes."""
        print("[DataLoader] Loading CSV files...")

        # Load raw DataFrames
        self.orders = pd.read_csv(
            os.path.join(self.data_dir, "olist_orders_dataset.csv"),
            dtype=str,
            keep_default_na=False
        )
        self.order_items = pd.read_csv(
            os.path.join(self.data_dir, "olist_order_items_dataset.csv"),
            dtype={"order_item_id": int},
            keep_default_na=False
        )
        self.order_payments = pd.read_csv(
            os.path.join(self.data_dir, "olist_order_payments_dataset.csv"),
            dtype={"payment_sequential": int, "payment_installments": int},
            keep_default_na=False
        )
        self.customers = pd.read_csv(
            os.path.join(self.data_dir, "olist_customers_dataset.csv"),
            dtype=str
        )
        self.products = pd.read_csv(
            os.path.join(self.data_dir, "olist_products_dataset.csv"),
            dtype=str
        )
        self.sellers = pd.read_csv(
            os.path.join(self.data_dir, "olist_sellers_dataset.csv"),
            dtype=str
        )
        self.reviews = pd.read_csv(
            os.path.join(self.data_dir, "olist_order_reviews_dataset.csv"),
            dtype=str
        )
        self.category_translation = pd.read_csv(
            os.path.join(self.data_dir, "product_category_name_translation.csv"),
            dtype=str
        )

        # Convert numeric columns properly
        for col in ["price", "freight_value"]:
            self.order_items[col] = pd.to_numeric(self.order_items[col], errors="coerce")
        self.order_payments["payment_value"] = pd.to_numeric(
            self.order_payments["payment_value"], errors="coerce"
        )

        # Build indexes for O(1) lookup
        self._build_indexes()
        print(f"[DataLoader] Loaded {len(self.orders)} orders, "
              f"{len(self.order_items)} items, "
              f"{len(self.order_payments)} payments, "
              f"{len(self.customers)} customers, "
              f"{len(self.products)} products")

    def _build_indexes(self):
        """Build dictionary indexes for fast lookup."""
        # Order by order_id
        self.orders_by_id = {}
        for _, row in self.orders.iterrows():
            oid = row["order_id"]
            self.orders_by_id[oid] = row.to_dict()

        # Items by order_id (list)
        self.items_by_order = {}
        for _, row in self.order_items.iterrows():
            oid = row["order_id"]
            if oid not in self.items_by_order:
                self.items_by_order[oid] = []
            self.items_by_order[oid].append(row.to_dict())

        # Payments by order_id (list)
        self.payments_by_order = {}
        for _, row in self.order_payments.iterrows():
            oid = row["order_id"]
            if oid not in self.payments_by_order:
                self.payments_by_order[oid] = []
            self.payments_by_order[oid].append(row.to_dict())

        # Customer by customer_id
        self.customer_by_id = {}
        for _, row in self.customers.iterrows():
            cid = row["customer_id"]
            self.customer_by_id[cid] = row.to_dict()

        # Customer_id list by customer_unique_id
        self.customers_by_unique_id = {}
        for _, row in self.customers.iterrows():
            uid = row["customer_unique_id"]
            if uid not in self.customers_by_unique_id:
                self.customers_by_unique_id[uid] = []
            self.customers_by_unique_id[uid].append(row["customer_id"])

        # Orders by customer_id
        self.orders_by_customer = {}
        for _, row in self.orders.iterrows():
            cid = row["customer_id"]
            if cid not in self.orders_by_customer:
                self.orders_by_customer[cid] = []
            self.orders_by_customer[cid].append(row["order_id"])

        # Product by product_id
        self.product_by_id = {}
        for _, row in self.products.iterrows():
            pid = row["product_id"]
            self.product_by_id[pid] = row.to_dict()

        # Category translation
        self.category_translation_map = {}
        for _, row in self.category_translation.iterrows():
            name = row["product_category_name"]
            self.category_translation_map[name] = row["product_category_name_english"]

    def get_order(self, order_id: str) -> Optional[dict]:
        """Get order data by order_id."""
        return self.orders_by_id.get(order_id)

    def get_items(self, order_id: str) -> list:
        """Get all item rows for an order."""
        return self.items_by_order.get(order_id, [])

    def get_payments(self, order_id: str) -> list:
        """Get all payment rows for an order."""
        return self.payments_by_order.get(order_id, [])

    def get_customer(self, customer_id: str) -> Optional[dict]:
        """Get customer data by customer_id."""
        return self.customer_by_id.get(customer_id)

    def get_product(self, product_id: str) -> Optional[dict]:
        """Get product data by product_id."""
        return self.product_by_id.get(product_id)

    def get_related_orders(self, customer_unique_id: str, exclude_order_id: str) -> list:
        """Get all order_ids for a customer_unique_id, excluding the current order."""
        customer_ids = self.customers_by_unique_id.get(customer_unique_id, [])
        related = []
        for cid in customer_ids:
            for oid in self.orders_by_customer.get(cid, []):
                if oid != exclude_order_id:
                    related.append(oid)
        return related

    def get_category_english(self, category_name: str) -> str:
        """Translate category name to English, or return original if no translation."""
        if not category_name or category_name == "nan":
            return ""
        return self.category_translation_map.get(category_name, category_name)
