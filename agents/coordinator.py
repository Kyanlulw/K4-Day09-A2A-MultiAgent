from __future__ import annotations

from typing import Any

from agents.base import AgentResult, LLMClient
from agents.customer_agent import CustomerAgent
from agents.delivery_agent import DeliveryAgent
from agents.order_product_agent import OrderProductAgent
from agents.payment_agent import PaymentAgent
from agents.policy_agent import PolicyAgent
from agents.verifier_agent import VerifierAgent


class CoordinatorAgent:
    agent_name = "Coordinator Agent"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()
        self.customer_agent = CustomerAgent(self.llm)
        self.order_product_agent = OrderProductAgent(self.llm)
        self.payment_agent = PaymentAgent(self.llm)
        self.delivery_agent = DeliveryAgent(self.llm)
        self.policy_agent = PolicyAgent(self.llm)
        self.verifier_agent = VerifierAgent(self.llm)

    def process(self, evidence: dict[str, Any]) -> tuple[dict[str, Any], list[AgentResult]]:
        case = evidence["case"]
        order = evidence["order"]
        if not order:
            raise ValueError(f"Order not found for case {case['case_id']}")

        order_id = case["customer_request"]["claimed_order_id"]
        traces: list[AgentResult] = []

        customer_result = self.customer_agent.run(
            {
                "case_id": case["case_id"],
                "order_id": order_id,
                "customer": evidence["customer"],
                "related_order_ids": evidence["related_order_ids"],
            }
        )
        traces.append(customer_result)

        order_product_result = self.order_product_agent.run(
            {
                "case_id": case["case_id"],
                "order_id": order_id,
                "items": evidence["items"],
                "products": evidence["products"],
                "category_translations": {
                    product.get("product_category_name"): evidence["category_translations"].get(
                        product.get("product_category_name"), product.get("product_category_name")
                    )
                    for product in evidence["products"]
                    if product.get("product_category_name")
                },
            }
        )
        traces.append(order_product_result)

        payment_result = self.payment_agent.run(
            {
                "case_id": case["case_id"],
                "order_id": order_id,
                "items": evidence["items"],
                "payments": evidence["payments"],
            }
        )
        traces.append(payment_result)

        delivery_result = self.delivery_agent.run(
            {
                "case_id": case["case_id"],
                "order": order,
                "items": evidence["items"],
            }
        )
        traces.append(delivery_result)

        policy_result = self.policy_agent.run(
            {
                "case_id": case["case_id"],
                "order_id": order_id,
                "order": {
                    "order_id": order.get("order_id"),
                    "order_status": order.get("order_status"),
                    "order_delivered_carrier_date": order.get("order_delivered_carrier_date"),
                    "order_delivered_customer_date": order.get("order_delivered_customer_date"),
                    "order_estimated_delivery_date": order.get("order_estimated_delivery_date"),
                },
                "customer": _strip_llm_notes(customer_result.response),
                "order_product": _strip_llm_notes(order_product_result.response),
                "payment": _strip_llm_notes(payment_result.response),
                "delivery": _strip_llm_notes(delivery_result.response),
            }
        )
        traces.append(policy_result)

        output = self._compose_output(
            case,
            order_id,
            customer_result.response,
            order_product_result.response,
            payment_result.response,
            delivery_result.response,
            policy_result.response,
        )
        verifier_result = self.verifier_agent.run({"case_id": case["case_id"], "output": output})
        traces.append(verifier_result)
        if not verifier_result.response["valid"]:
            raise ValueError(f"Verifier failed for {case['case_id']}: {verifier_result.response['issues']}")
        return output, traces

    def _compose_output(
        self,
        case: dict[str, Any],
        order_id: str,
        customer: dict[str, Any],
        order_product: dict[str, Any],
        payment: dict[str, Any],
        delivery: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "case_id": case["case_id"],
            "case_assessment": {
                "primary_issue": policy["primary_issue"],
                "secondary_issues": policy["secondary_issues"],
                "case_status": policy["case_status"],
                "confidence": policy["confidence"],
            },
            "affected_entities": {
                "order_ids": [order_id],
                "item_ids": order_product["item_ids"],
                "seller_ids": order_product["seller_ids"],
                "payment_ids": payment["payment_ids"],
            },
            "customer_context": {
                "customer_unique_id": customer["customer_unique_id"],
                "related_order_ids": customer["related_order_ids"],
            },
            "product_context": {
                "product_ids": order_product["product_ids"],
                "category_names": order_product["category_names"],
            },
            "delivery_analysis": {
                "delivered_at": delivery["delivered_at"],
                "estimated_delivery_at": delivery["estimated_delivery_at"],
                "carrier_handoff_at": delivery["carrier_handoff_at"],
                "delivery_variance_hours": delivery["delivery_variance_hours"],
                "seller_handoff_analysis": delivery["seller_handoff_analysis"],
                "late_handoff_seller_ids": delivery["late_handoff_seller_ids"],
            },
            "payment_reconciliation": {
                "currency": payment["currency"],
                "item_total_brl": payment["item_total_brl"],
                "freight_total_brl": payment["freight_total_brl"],
                "expected_total_brl": payment["expected_total_brl"],
                "payment_total_brl": payment["payment_total_brl"],
                "difference_brl": payment["difference_brl"],
                "reconciled": payment["reconciled"],
                "payment_types": payment["payment_types"],
            },
            "root_cause_analysis": {
                "ranked_causes": policy["ranked_causes"],
                "responsible_parties": policy["responsible_parties"],
            },
            "evidence_ids": policy["evidence_ids"],
            "financial_resolution": {
                "currency": "BRL",
                "recommended_refund_brl": policy["recommended_refund_brl"],
            },
            "resolution_actions": policy["resolution_actions"],
        }


def _strip_llm_notes(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "llm_assessment"}
