from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents.base import LLMClient
from agents.coordinator import CoordinatorAgent
from tools.data_loader import OlistDataStore
from trace_writer import TraceWriter


ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the multi-agent Olist dispute pipeline.")
    parser.add_argument("--case", help="Run only one case ID, for example EC_001.")
    parser.add_argument("--root", default=str(ROOT), help="Project root.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    data_store = OlistDataStore(root)
    llm_client = LLMClient()
    coordinator = CoordinatorAgent(llm_client)
    trace_writer = TraceWriter(root / "logging" / "trace.jsonl", reset=not bool(args.case))
    output_dir = root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    cases = data_store.load_cases()
    if args.case:
        cases = [case for case in cases if case["case_id"] == args.case]
        if not cases:
            raise SystemExit(f"Case not found: {args.case}")

    for case in cases:
        evidence = data_store.retrieve_case_evidence(case)
        output, agent_results = coordinator.process(evidence)
        output_path = output_dir / f"{case['case_id']}.json"
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(output, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        order_id = case["customer_request"]["claimed_order_id"]
        trace_writer.write_case(case["case_id"], order_id, agent_results, output)

    print(f"Processed {len(cases)} case(s). Output directory: {output_dir}")
    print(f"Trace file: {root / 'logging' / 'trace.jsonl'}")
    print(f"LLM provider: {llm_client.provider}; model: {llm_client.model}; enabled: {llm_client.enabled}")


if __name__ == "__main__":
    main()
