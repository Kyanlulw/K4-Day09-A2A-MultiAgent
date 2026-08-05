from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AgentResult:
    agent_name: str
    prompt: dict[str, Any]
    response: dict[str, Any]
    model_used: str
    llm_enabled: bool


class LLMClient:
    """Small JSON-only client for Ollama or OpenAI-compatible chat endpoints.

    The pipeline can run without a configured endpoint. In that mode each agent
    still receives a prompt-shaped payload and returns a deterministic local
    analysis, which keeps development and schema verification reproducible.
    """

    def __init__(self) -> None:
        _load_dotenv(Path.cwd() / ".env")
        self.provider = os.getenv("LLM_PROVIDER", "fallback").strip().lower()
        self.model = os.getenv("LLM_MODEL", "local-rule-reasoner-0B").strip()
        self.base_url = os.getenv("LLM_BASE_URL", "").strip()
        self.api_key = os.getenv("LLM_API_KEY", "").strip()
        self.enabled = self.provider in {"ollama", "openai"} and bool(self.base_url)
        self.require_llm = os.getenv("LLM_REQUIRE", "true").strip().lower() in {"1", "true", "yes"}
        self.timeout_seconds = int(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
        self.last_error = ""

    def complete_json(self, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False, separators=(",", ":")),
            },
        ]

        if self.provider == "ollama":
            return self._complete_ollama(messages)
        if self.provider == "openai":
            return self._complete_openai(messages)
        return None

    def _complete_ollama(self, messages: list[dict[str, str]]) -> dict[str, Any] | None:
        url = self.base_url.rstrip("/") + "/api/chat"
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        return self._post_and_extract_json(url, body, ["message", "content"])

    def _complete_openai(self, messages: list[dict[str, str]]) -> dict[str, Any] | None:
        url = self.base_url.rstrip("/") + "/chat/completions"
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        return self._post_and_extract_json(url, body, ["choices", 0, "message", "content"])

    def _post_and_extract_json(
        self, url: str, body: dict[str, Any], content_path: list[str | int]
    ) -> dict[str, Any] | None:
        data = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload: Any = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            self.last_error = f"HTTP {exc.code}: {detail[:500]}"
            return None
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return None

        content: Any = payload
        try:
            for key in content_path:
                content = content[key]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            self.last_error = f"Could not parse JSON content: {type(exc).__name__}: {exc}"
            return None


class BaseAgent:
    agent_name = "BaseAgent"
    system_prompt = "Return only valid JSON."

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()

    def run(self, prompt: dict[str, Any]) -> AgentResult:
        print(f"Running {self.agent_name}...", flush=True)
        llm_response = self.llm.complete_json(self.system_prompt, prompt)
        if self.llm.enabled and self.llm.require_llm and llm_response is None:
            raise RuntimeError(
                f"{self.agent_name} could not get a valid JSON response from the LLM. "
                f"{self.llm.last_error}"
            )
        response = llm_response if llm_response is not None else self.reason(prompt)
        if llm_response is not None:
            response = self.normalize(prompt, response)
        status = "LLM" if llm_response is not None else "fallback"
        print(f"Finished {self.agent_name} ({status}).", flush=True)
        return AgentResult(
            agent_name=self.agent_name,
            prompt=prompt,
            response=response,
            model_used=self.llm.model,
            llm_enabled=llm_response is not None,
        )

    def reason(self, prompt: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def normalize(self, prompt: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
        return response


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
