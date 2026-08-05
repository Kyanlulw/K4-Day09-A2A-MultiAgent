import json
import os
import time
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY was not found. "
        "Add it to the local .env file."
    )

# Public model identifier: Qwen 2.5 7B, which meets the <= 10B requirement.
MODEL_NAME = "qwen/qwen-2.5-7b-instruct"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_RATE_LIMIT_RETRIES = 8


def ask_llm(system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
    """Call OpenRouter and return the model's JSON object."""
    body = {
        "model": MODEL_NAME,
        "temperature": 0,
        "max_tokens": 2200,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False, default=str),
            },
        ],
    }

    for attempt in range(1, MAX_RATE_LIMIT_RETRIES + 1):
        request = Request(
            API_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
            content = payload["choices"][0]["message"]["content"]
            return json.loads(content)
        except HTTPError as error:
            if error.code != 429 or attempt == MAX_RATE_LIMIT_RETRIES:
                details = error.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"OpenRouter API error {error.code}: {details}") from error

            wait_seconds = max(1.0, float(error.headers.get("Retry-After", "1")))
            print(f"Rate limit reached; waiting {wait_seconds:.1f}s before retry.")
            time.sleep(wait_seconds)

    raise RuntimeError("OpenRouter request did not complete.")
