import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from groq import Groq, RateLimitError


# Load GROQ_API_KEY from .env; never place the secret in source code.
load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY was not found. "
        "Create a .env file containing GROQ_API_KEY=..."
    )

# The model name is intentionally public in code for the course requirement.
# Llama 3.1 8B meets the <= 10B parameter constraint.
MODEL_NAME = "llama-3.1-8b-instant"
MAX_RATE_LIMIT_RETRIES = 8

client = Groq(api_key=API_KEY)


def _retry_after_seconds(error: RateLimitError) -> float:
    """Read Groq's suggested retry delay, with a safe one-second fallback."""
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", {})
    retry_after = headers.get("retry-after", "1")

    try:
        return max(1.0, float(retry_after))
    except (TypeError, ValueError):
        return 1.0


def ask_llm(
    system_prompt: str,
    user_payload: dict[str, Any],
) -> dict[str, Any]:
    """Send a JSON-compatible payload to Groq and return the JSON response."""
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": json.dumps(
                user_payload,
                ensure_ascii=False,
                default=str,
            ),
        },
    ]

    for attempt in range(1, MAX_RATE_LIMIT_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                temperature=0,
                max_tokens=250,
                response_format={"type": "json_object"},
                messages=messages,
            )
            break
        except RateLimitError as error:
            if attempt == MAX_RATE_LIMIT_RETRIES:
                raise

            wait_seconds = _retry_after_seconds(error)
            print(
                "Groq rate limit reached. "
                f"Waiting {wait_seconds:.1f}s before retry "
                f"({attempt}/{MAX_RATE_LIMIT_RETRIES})..."
            )
            time.sleep(wait_seconds)

    content = response.choices[0].message.content

    if not content:
        raise ValueError("LLM returned an empty response.")

    return json.loads(content)
