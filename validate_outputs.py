from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"


REQUIRED_TOP_LEVEL = {
    "case_id",
    "case_assessment",
    "affected_entities",
    "customer_context",
    "product_context",
    "delivery_analysis",
    "payment_reconciliation",
    "root_cause_analysis",
    "evidence_ids",
    "financial_resolution",
    "resolution_actions",
}


def main() -> None:
    files = sorted(OUTPUT_DIR.glob("EC_*.json"))
    if len(files) != 50:
        raise SystemExit(f"Expected 50 output JSON files, found {len(files)}")

    primary_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    for path in files:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        missing = REQUIRED_TOP_LEVEL - set(data)
        if missing:
            raise SystemExit(f"{path.name} missing fields: {sorted(missing)}")
        confidence = data["case_assessment"]["confidence"]
        if not 0 <= confidence <= 1:
            raise SystemExit(f"{path.name} invalid confidence: {confidence}")
        refund = data["financial_resolution"]["recommended_refund_brl"]
        expected_status = "action_required" if refund > 0 else "no_action"
        if data["case_assessment"]["case_status"] != expected_status:
            raise SystemExit(f"{path.name} status/refund mismatch")
        primary_counter[data["case_assessment"]["primary_issue"]] += 1
        status_counter[data["case_assessment"]["case_status"]] += 1

    print("Output validation passed.")
    print("Primary issue distribution:", dict(primary_counter))
    print("Case status distribution:", dict(status_counter))


if __name__ == "__main__":
    main()

