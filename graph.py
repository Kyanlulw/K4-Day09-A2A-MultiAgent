"""
LangGraph Workflow - Multi-Agent E-commerce Dispute Resolution

Defines the StateGraph with 7 nodes:
  coordinator_start -> customer -> order_product -> payment -> delivery -> policy -> verifier

Hybrid architecture:
  - LLM Agents (Groq Llama 3.1-8B): Coordinator, Policy, Verifier
  - Deterministic Agents: Customer, Order&Product, Payment, Delivery

Each node is a LangGraph node function that reads/writes to a shared TypedDict state.
"""

import json
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END

from tools.data_loader import OlistDataLoader
from tools.llm_client import llm_call, llm_json_call, MODEL_NAME
from agents.customer_agent import run_customer_agent
from agents.order_product_agent import run_order_product_agent
from agents.payment_agent import run_payment_agent
from agents.delivery_agent import run_delivery_agent
from agents.policy_agent import run_policy_agent
from agents.verifier_agent import run_verifier_agent, save_output


# ---- Shared State ----

class CaseState(TypedDict, total=False):
    """Shared state passed between agents in the LangGraph."""
    # Input
    case_id: str
    order_id: str
    data_loader: OlistDataLoader
    output_dir: str

    # Order data (from coordinator)
    order_data: Optional[dict]

    # Agent results
    customer_result: Optional[dict]
    order_product_result: Optional[dict]
    payment_result: Optional[dict]
    delivery_result: Optional[dict]
    policy_result: Optional[dict]

    # Final output
    output: Optional[dict]

    # Trace info
    trace_steps: list


# ---- Node functions ----

COORDINATOR_SYSTEM_PROMPT = """You are a Coordinator Agent for an E-commerce Dispute Resolution System.
Your role is to receive a customer complaint case, validate the order exists, and create an investigation plan.

You will be given order data from the Olist dataset. Analyze it and provide:
1. A brief assessment of the order status
2. Key investigation areas based on the order status
3. What each downstream agent should focus on

Respond in JSON format with:
{
  "order_found": true/false,
  "order_status": "<status>",
  "investigation_plan": "<brief plan>",
  "risk_flags": ["<any immediate flags based on order status>"]
}"""


def coordinator_start_node(state: CaseState) -> dict:
    """
    Coordinator Agent (LLM-based): Validate input, lookup order, create investigation plan.
    Uses Groq Llama 3.1-8B for reasoning about the case.
    """
    case_id = state["case_id"]
    order_id = state["order_id"]
    data = state["data_loader"]

    print(f"\n{'='*60}")
    print(f"[Coordinator-LLM] Processing {case_id} (order: {order_id})")
    print(f"{'='*60}")

    order_data = data.get_order(order_id)

    # Build context for LLM
    if order_data:
        order_summary = (
            f"Order ID: {order_id}\n"
            f"Status: {order_data.get('order_status', 'unknown')}\n"
            f"Purchase date: {order_data.get('order_purchase_timestamp', 'N/A')}\n"
            f"Approved at: {order_data.get('order_approved_at', 'N/A')}\n"
            f"Delivered to carrier: {order_data.get('order_delivered_carrier_date', 'N/A')}\n"
            f"Delivered to customer: {order_data.get('order_delivered_customer_date', 'N/A')}\n"
            f"Estimated delivery: {order_data.get('order_estimated_delivery_date', 'N/A')}"
        )
    else:
        order_summary = f"Order ID: {order_id}\nSTATUS: NOT FOUND IN DATASET"

    try:
        llm_result = llm_json_call(
            system_prompt=COORDINATOR_SYSTEM_PROMPT,
            user_prompt=f"Case: {case_id}\n\n{order_summary}",
            temperature=0.0,
            max_tokens=512,
        )
        plan = llm_result.get("investigation_plan", "Standard investigation")
        flags = llm_result.get("risk_flags", [])
        print(f"  [Coordinator-LLM] Plan: {plan[:100]}")
        if flags:
            print(f"  [Coordinator-LLM] Risk flags: {flags}")
    except Exception as e:
        print(f"  [Coordinator-LLM] LLM call failed: {e}, continuing with data...")
        llm_result = {"order_found": order_data is not None, "investigation_plan": "fallback"}

    return {
        "order_data": order_data,
        "trace_steps": [{
            "agent": "coordinator",
            "model": MODEL_NAME,
            "action": "start",
            "case_id": case_id,
            "order_found": order_data is not None,
            "llm_plan": llm_result.get("investigation_plan", ""),
        }],
    }


def customer_node(state: CaseState) -> dict:
    """Customer Agent node (deterministic): analyze customer identity and history."""
    result = run_customer_agent(state["order_id"], state["data_loader"])
    steps = state.get("trace_steps", [])
    steps.append({"agent": "customer_agent", "result_summary": {
        "customer_unique_id": result.get("customer_unique_id"),
        "related_orders_count": len(result.get("related_order_ids", [])),
    }})
    return {"customer_result": result, "trace_steps": steps}


def order_product_node(state: CaseState) -> dict:
    """Order & Product Agent node (deterministic): analyze items, sellers, products."""
    result = run_order_product_agent(state["order_id"], state["data_loader"])
    steps = state.get("trace_steps", [])
    steps.append({"agent": "order_product_agent", "result_summary": {
        "items_count": len(result.get("item_ids", [])),
        "sellers_count": len(result.get("seller_ids", [])),
        "has_items": result.get("has_items"),
    }})
    return {"order_product_result": result, "trace_steps": steps}


def payment_node(state: CaseState) -> dict:
    """Payment Agent node (deterministic): reconcile payments with item + freight totals."""
    expected_total = None
    opr = state.get("order_product_result")
    if opr and opr.get("has_items"):
        expected_total = opr.get("expected_total_brl")

    result = run_payment_agent(state["order_id"], state["data_loader"], expected_total)

    # Backfill item/freight totals from order_product into payment result
    if opr:
        result["item_total_brl"] = opr.get("item_total_brl")
        result["freight_total_brl"] = opr.get("freight_total_brl")

    steps = state.get("trace_steps", [])
    steps.append({"agent": "payment_agent", "result_summary": {
        "payment_total": result.get("payment_total_brl"),
        "reconciled": result.get("reconciled"),
    }})
    return {"payment_result": result, "trace_steps": steps}


def delivery_node(state: CaseState) -> dict:
    """Delivery Agent node (deterministic): analyze delivery timing and seller handoff."""
    items_raw = None
    opr = state.get("order_product_result")
    if opr:
        items_raw = opr.get("items_raw")

    result = run_delivery_agent(state["order_id"], state["data_loader"], items_raw)
    steps = state.get("trace_steps", [])
    steps.append({"agent": "delivery_agent", "result_summary": {
        "is_late": result.get("is_late_delivery"),
        "variance_hours": result.get("delivery_variance_hours"),
        "late_sellers": result.get("late_handoff_seller_ids"),
    }})
    return {"delivery_result": result, "trace_steps": steps}


def policy_node(state: CaseState) -> dict:
    """Policy Agent node (LLM-based): classify case using EC_POLICY_V2 via Groq Llama 3.1-8B."""
    result = run_policy_agent(
        order_id=state["order_id"],
        order_data=state.get("order_data"),
        order_product_result=state.get("order_product_result", {}),
        payment_result=state.get("payment_result", {}),
        delivery_result=state.get("delivery_result", {}),
        customer_result=state.get("customer_result", {}),
    )
    steps = state.get("trace_steps", [])
    steps.append({"agent": "policy_agent", "model": MODEL_NAME, "result_summary": {
        "primary_issue": result.get("primary_issue"),
        "case_status": result.get("case_status"),
        "refund": result.get("refund_amount"),
    }})
    return {"policy_result": result, "trace_steps": steps}


VERIFIER_SYSTEM_PROMPT = """You are a Verifier Agent for an E-commerce Dispute Resolution System.
Your role is to review the final output JSON for quality and correctness.

Check for:
1. primary_issue matches the evidence (order_status, delivery dates, payment data)
2. refund_amount is correct based on the policy rules
3. evidence_ids follow the correct format (order:X, item:X:Y, payment:X:Y, seller:X, policy:X)
4. case_status matches: "action_required" if refund > 0, "no_action" if refund = 0
5. secondary_issues are properly identified
6. All arrays respect limits (5 order IDs, 5 items, 3 sellers, 5 payments, 20 evidence, 5 actions)

Respond in JSON format:
{
  "is_valid": true/false,
  "issues_found": ["<list any problems>"],
  "corrections": {
    "<field_path>": "<corrected_value>"
  },
  "quality_score": <float 0-1>
}

If the output is correct, return is_valid=true with empty issues_found and corrections."""


def verifier_node(state: CaseState) -> dict:
    """Verifier Agent node (LLM-based): validate schema, review quality, and write output."""
    # First, build the output using the deterministic verifier
    output = run_verifier_agent(
        case_id=state["case_id"],
        order_id=state["order_id"],
        order_product_result=state.get("order_product_result", {}),
        payment_result=state.get("payment_result", {}),
        delivery_result=state.get("delivery_result", {}),
        customer_result=state.get("customer_result", {}),
        policy_result=state.get("policy_result", {}),
    )

    # Then use LLM to review the output quality
    try:
        review_prompt = (
            f"Review this output JSON for case {state['case_id']}:\n\n"
            f"{json.dumps(output, indent=2, ensure_ascii=False)}\n\n"
            f"Order status from data: {state.get('order_data', {}).get('order_status', 'unknown') if state.get('order_data') else 'NOT FOUND'}\n"
            f"Payment total: {state.get('payment_result', {}).get('payment_total_brl', 'N/A')}\n"
            f"Is late delivery: {state.get('delivery_result', {}).get('is_late_delivery', 'N/A')}\n"
            f"Late sellers: {state.get('delivery_result', {}).get('late_handoff_seller_ids', [])}"
        )

        review = llm_json_call(
            system_prompt=VERIFIER_SYSTEM_PROMPT,
            user_prompt=review_prompt,
            temperature=0.0,
            max_tokens=1024,
        )

        is_valid = review.get("is_valid", True)
        quality = review.get("quality_score", 0.9)
        issues = review.get("issues_found", [])

        print(f"  [VerifierAgent-LLM] Quality: {quality}, Valid: {is_valid}")
        if issues:
            print(f"  [VerifierAgent-LLM] Issues: {issues[:3]}")

        # Apply corrections from LLM if any
        corrections = review.get("corrections", {})
        if corrections and not is_valid:
            print(f"  [VerifierAgent-LLM] Applying {len(corrections)} corrections...")
            for field_path, corrected_value in corrections.items():
                _apply_correction(output, field_path, corrected_value)

    except Exception as e:
        print(f"  [VerifierAgent-LLM] Review failed: {e}, saving output as-is")

    # Save to file
    save_output(output, state["output_dir"], state["case_id"])

    steps = state.get("trace_steps", [])
    steps.append({"agent": "verifier_agent", "model": MODEL_NAME, "action": "output_saved"})

    return {"output": output, "trace_steps": steps}


def _apply_correction(output: dict, field_path: str, value):
    """Apply a single field correction using dot notation path."""
    try:
        parts = field_path.split(".")
        obj = output
        for part in parts[:-1]:
            if isinstance(obj, dict):
                obj = obj.get(part, {})
            else:
                return
        if isinstance(obj, dict) and parts[-1] in obj:
            obj[parts[-1]] = value
    except Exception:
        pass


# ---- Build Graph ----

def build_graph() -> StateGraph:
    """
    Build the LangGraph StateGraph for the multi-agent workflow.

    Flow:
      START -> coordinator_start -> customer -> order_product -> payment -> delivery -> policy -> verifier -> END

    LLM Nodes: coordinator_start, policy, verifier (Groq Llama 3.1-8B)
    Deterministic Nodes: customer, order_product, payment, delivery
    """
    graph = StateGraph(CaseState)

    # Add nodes
    graph.add_node("coordinator_start", coordinator_start_node)
    graph.add_node("customer", customer_node)
    graph.add_node("order_product", order_product_node)
    graph.add_node("payment", payment_node)
    graph.add_node("delivery", delivery_node)
    graph.add_node("policy", policy_node)
    graph.add_node("verifier", verifier_node)

    # Add edges (sequential flow with data dependencies)
    graph.add_edge(START, "coordinator_start")
    graph.add_edge("coordinator_start", "customer")
    graph.add_edge("customer", "order_product")
    graph.add_edge("order_product", "payment")      # payment needs expected_total from order_product
    graph.add_edge("payment", "delivery")            # delivery needs items_raw from order_product
    graph.add_edge("delivery", "policy")             # policy needs all previous results
    graph.add_edge("policy", "verifier")             # verifier assembles final output
    graph.add_edge("verifier", END)

    return graph


def compile_graph():
    """Compile the graph for execution."""
    graph = build_graph()
    return graph.compile()
