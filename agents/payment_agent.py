"""
Payment Agent (LLM-based) - Reconciles payments with expected totals.

Responsibilities:
- Provide raw payment data and expected_total to LLM.
- LLM extracts payment_ids, payment_types, and determines if reconciled (with hints).
"""

import json
from typing import Optional
from tools.data_loader import OlistDataLoader
from tools.llm_client import llm_json_call


PAYMENT_SYSTEM_PROMPT = """You are a Payment Agent for an E-commerce Dispute Resolution System.
Your job is to analyze raw payment rows and reconcile them against an expected total.

You will be given:
1. Raw payment data.
2. The expected total.
3. A pre-calculated payment total hint (use this to avoid float addition errors).

Output a JSON object exactly matching this schema:
{
  "payment_count": <int, number of payment rows>,
  "payment_ids": ["<list of payment IDs like order_id:payment_sequential>"],
  "payment_types": ["<list of unique payment types>"],
  "payment_total_brl": <float, sum of payment values, use hint>,
  "expected_total_brl": <float, the provided expected total>,
  "difference_brl": <float, payment_total_brl - expected_total_brl>,
  "reconciled": <boolean, true if abs(difference_brl) <= 0.10, else false>
}

Rules:
- limit payment_ids to 5.
"""


def run_payment_agent(order_id: str, data: OlistDataLoader, expected_total: Optional[float] = None) -> dict:
    """
    Analyze payments and reconcile with expected total using LLM.
    """
    result = {
        "payment_count": 0,
        "payment_ids": [],
        "payment_total_brl": 0.0,
        "payment_types": [],
        "expected_total_brl": expected_total,
        "difference_brl": None,
        "reconciled": False,
    }

    payments = data.get_payments(order_id)
    if not payments:
        print(f"  [PaymentAgent-LLM] No payments found for order {order_id}")
        return result

    # Pre-calculations for hints
    calc_payment_total = sum(float(p.get("payment_value", 0) or 0) for p in payments)
    calc_diff = round(calc_payment_total - (expected_total or 0), 2)
    calc_reconciled = abs(calc_diff) <= 0.10 if expected_total is not None else False

    user_prompt = (
        f"Order ID: {order_id}\n\n"
        f"Raw Payments: {json.dumps(payments)}\n\n"
        f"Expected Total: {expected_total}\n\n"
        f"HINTS (Use these to avoid math errors):\n"
        f"payment_total_brl = {calc_payment_total:.2f}\n"
        f"difference_brl = {calc_diff:.2f}\n"
        f"reconciled = {str(calc_reconciled).lower()}\n"
    )

    print(f"  [PaymentAgent-LLM] Calling LLM...")
    try:
        llm_result = llm_json_call(
            system_prompt=PAYMENT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=256
        )
        
        result.update({
            "payment_count": llm_result.get("payment_count", len(payments)),
            "payment_ids": llm_result.get("payment_ids", [])[:5],
            "payment_types": llm_result.get("payment_types", []),
            "payment_total_brl": round(float(llm_result.get("payment_total_brl", calc_payment_total)), 2),
            "expected_total_brl": expected_total,
            "difference_brl": round(float(llm_result.get("difference_brl", calc_diff)), 2) if expected_total is not None else None,
            "reconciled": bool(llm_result.get("reconciled", calc_reconciled)),
        })
    except Exception as e:
        print(f"  [PaymentAgent-LLM] LLM call failed: {e}. Falling back to deterministic.")
        result["payment_count"] = len(payments)
        result["payment_ids"] = [f"{order_id}:{p.get('payment_sequential')}" for p in payments][:5]
        result["payment_types"] = list(set([p.get("payment_type") for p in payments if p.get("payment_type")]))
        result["payment_total_brl"] = round(calc_payment_total, 2)
        result["difference_brl"] = calc_diff if expected_total is not None else None
        result["reconciled"] = calc_reconciled

    print(f"  [PaymentAgent-LLM] payments={result['payment_count']}, "
          f"total={result['payment_total_brl']}, "
          f"types={result['payment_types']}, "
          f"reconciled={result['reconciled']}")

    return result
