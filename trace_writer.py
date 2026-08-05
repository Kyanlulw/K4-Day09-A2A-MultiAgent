from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.base import AgentResult


class TraceWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def write_case(
        self,
        case_id: str,
        order_id: str,
        agent_results: list[AgentResult],
        output: dict[str, Any],
    ) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            for index, result in enumerate(agent_results, start=1):
                event = {
                    "case_id": case_id,
                    "order_id": order_id,
                    "step": index,
                    "agent": result.agent_name,
                    "model_used": result.model_used,
                    "llm_enabled": result.llm_enabled,
                    "input": result.prompt,
                    "output": result.response,
                }
                handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.write(
                json.dumps(
                    {
                        "case_id": case_id,
                        "order_id": order_id,
                        "step": len(agent_results) + 1,
                        "agent": "Coordinator Agent",
                        "event": "write_output",
                        "output_file": f"output/{case_id}.json",
                        "primary_issue": output["case_assessment"]["primary_issue"],
                        "recommended_refund_brl": output["financial_resolution"][
                            "recommended_refund_brl"
                        ],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )

