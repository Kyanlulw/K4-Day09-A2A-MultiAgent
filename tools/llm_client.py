"""
LLM Client - OpenRouter API integration for LLM-based agents.

Uses OpenRouter with nvidia/nemotron-nano-9b-v2:free for:
- Coordinator Agent
- Policy Agent
- Verifier Agent
- Customer Agent
- Order & Product Agent
- Payment Agent
- Delivery Agent

Includes automatic retry with exponential backoff for rate limiting.
"""

import json
import os
import time
import re
from typing import Optional

from openai import OpenAI


# Model configuration
MODEL_NAME = "nvidia/nemotron-nano-9b-v2:free"
MODEL_PARAMETER_SIZE = "9B"

# Rate limit settings
MAX_RETRIES = 5
BASE_WAIT_SECONDS = 3.0


def get_client() -> OpenAI:
    """Get OpenAI client configured for OpenRouter."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY not found in environment. "
            "Set it in .env file or export OPENROUTER_API_KEY=..."
        )
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def _extract_retry_after(error_msg: str) -> float:
    """Extract the retry-after seconds if present."""
    match = re.search(r"Please try again in (\d+\.?\d*)s", str(error_msg))
    if match:
        return float(match.group(1)) + 0.5
    return BASE_WAIT_SECONDS


def llm_call(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,
) -> str:
    """
    Make a single LLM call to OpenRouter with automatic retry.
    """
    client = get_client()

    kwargs = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                pass 

            response = client.chat.completions.create(**kwargs)
            time.sleep(BASE_WAIT_SECONDS)
            content = response.choices[0].message.content
            if content is None:
                print(f"\n[DEBUG LLM response]: {response.model_dump_json(indent=2)}\n")
                raise Exception("LLM returned None content")
            return content

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate_limit" in error_str:
                wait_time = _extract_retry_after(error_str)
                wait_time = max(wait_time, BASE_WAIT_SECONDS * (attempt + 1))
                print(f"    [LLM] Rate limited, waiting {wait_time:.1f}s (attempt {attempt+1}/{MAX_RETRIES})...")
                time.sleep(wait_time)
            else:
                raise

    raise Exception(f"Max retries ({MAX_RETRIES}) exceeded for LLM call")


def llm_json_call(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 4096,
) -> dict:
    """
    Make an LLM call expecting JSON response, with retry.
    """
    raw = llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to find JSON block using regex or basic string extraction
        try:
            start_idx = raw.find('{')
            end_idx = raw.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = raw[start_idx:end_idx+1]
                return json.loads(json_str)
        except Exception:
            pass
        raise Exception(f"Failed to parse JSON from LLM response: {raw[:100]}...")
