"""
Main Entry Point - Process all 50 E-commerce dispute cases.

Loads .env for API keys, loads data once, then runs each case through the LangGraph workflow.
Uses Groq Llama 3.1-8B for Coordinator, Policy, and Verifier agents.
"""

import json
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Load .env file BEFORE importing agents that use API keys
load_dotenv()

from tools.data_loader import OlistDataLoader
from tools.llm_client import MODEL_NAME
from graph import compile_graph
from trace_writer import TraceWriter


def load_case(input_dir: str, case_id: str) -> dict:
    """Load a case JSON from the input directory."""
    filepath = os.path.join(input_dir, f"{case_id}.json")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    input_dir = os.path.join(base_dir, "input")
    output_dir = os.path.join(base_dir, "output")
    trace_path = os.path.join(base_dir, "trace.jsonl")

    # Load all CSV data once
    print("=" * 60)
    print("Multi-Agent E-commerce Dispute Resolution System")
    print(f"LLM: Groq {MODEL_NAME}")
    print("=" * 60)
    start_time = time.time()

    data_loader = OlistDataLoader(data_dir)
    load_time = time.time() - start_time
    print(f"\nData loaded in {load_time:.2f}s\n")

    # Compile LangGraph workflow
    workflow = compile_graph()
    print("[Main] LangGraph workflow compiled\n")

    # Initialize trace writer
    trace_writer = TraceWriter(trace_path)

    # Process all 50 cases
    case_ids = [f"EC_{i:03d}" for i in range(1, 51)]
    total_cases = len(case_ids)
    success_count = 0
    error_cases = []

    for idx, case_id in enumerate(case_ids, 1):
        try:
            # Load case input
            case_input = load_case(input_dir, case_id)
            order_id = case_input["customer_request"]["claimed_order_id"]

            # Run the LangGraph workflow
            initial_state = {
                "case_id": case_id,
                "order_id": order_id,
                "data_loader": data_loader,
                "output_dir": output_dir,
                "trace_steps": [],
            }

            # Execute graph
            final_state = workflow.invoke(initial_state)

            # Write trace
            trace_writer.write_trace(
                case_id=case_id,
                order_id=order_id,
                trace_steps=final_state.get("trace_steps", []),
                output=final_state.get("output", {}),
            )

            success_count += 1
            print(f"  [{idx}/{total_cases}] [OK] {case_id} completed")

        except Exception as e:
            print(f"  [{idx}/{total_cases}] [FAIL] {case_id} ERROR: {e}")
            error_cases.append(case_id)
            import traceback
            traceback.print_exc()

    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"COMPLETED: {success_count}/{total_cases} cases in {elapsed:.2f}s")
    if error_cases:
        print(f"ERRORS: {error_cases}")
    print(f"Output directory: {output_dir}")
    print(f"Trace file: {trace_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
