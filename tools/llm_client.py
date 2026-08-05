import json
import os
import time
from typing import Any

from dotenv import load_dotenv
from groq import Groq, RateLimitError


load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise RuntimeError("GROQ_API_KEY was not found. Add it to the local .env file.")


MODEL_NAME = "llama-3.1-8b-instant"
MAX_RATE_LIMIT_RETRIES = 8
client = Groq(api_key=API_KEY)


def ask_llm(system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
    """Call Groq through its official SDK and return a JSON object."""
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False, default=str),
        },
    ]

    for attempt in range(1, MAX_RATE_LIMIT_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                temperature=0,
                max_tokens=2200,
                response_format={"type": "json_object"},
                messages=messages,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Groq returned an empty response.")
            return json.loads(content)
        except RateLimitError as error:
            if attempt == MAX_RATE_LIMIT_RETRIES:
                raise
            retry_after = getattr(error.response, "headers", {}).get("retry-after", "1")
            wait_seconds = max(1.0, float(retry_after))
            print(f"Rate limit reached; waiting {wait_seconds:.1f}s before retry.")
            time.sleep(wait_seconds)

    raise RuntimeError("Groq request did not complete.")
