"""
Trace Writer - Records execution trace for all 50 cases.

Writes trace.jsonl with one JSON line per case.
"""

import json
import os
from datetime import datetime


class TraceWriter:
    """Writes execution traces to trace.jsonl."""

    def __init__(self, output_path: str):
        self.output_path = output_path
        # Overwrite on start (per README: "không append, chỉ cần lượt chạy mới nhất")
        if os.path.exists(self.output_path):
            os.remove(self.output_path)
        self.start_time = datetime.now().isoformat()

    def write_trace(self, case_id: str, order_id: str, trace_steps: list, output: dict):
        """Append one trace entry for a case."""
        entry = {
            "case_id": case_id,
            "order_id": order_id,
            "timestamp": datetime.now().isoformat(),
            "steps": trace_steps,
            "output_summary": {
                "primary_issue": output.get("case_assessment", {}).get("primary_issue"),
                "case_status": output.get("case_assessment", {}).get("case_status"),
                "refund": output.get("financial_resolution", {}).get("recommended_refund_brl"),
            },
        }
        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
