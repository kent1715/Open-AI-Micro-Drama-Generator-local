import json
import os
import re
from typing import Optional


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:8b"


class LocalLLM:
    """Calls a local Ollama chat model and returns plain text completions."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or os.environ.get("LOCAL_LLM_MODEL", DEFAULT_MODEL)
        self.base_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        self.chat_url = f"{self.base_url}/api/chat"
        print(f"[LLM] Using local Ollama model: {self.model}")
        print(f"[LLM] Ollama base URL: {self.base_url}")

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: int = 120,
        fallback: Optional[str] = None,
    ) -> str:
        """Return a completion using Ollama's local /api/chat endpoint.

        The MuAPI LLM adapter returns a string, so this keeps the same contract.
        For JSON-only prompts, it strips common model wrappers and extracts the
        first JSON object so existing pipeline parsers can keep using json.loads.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,
            },
        }

        import httpx

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(self.chat_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("message", {}).get("content", "")
        if not content:
            if fallback is not None:
                return fallback
            raise ValueError(f"Ollama returned no message content: {data}")

        content = self._strip_reasoning(content).strip()

        if self._expects_json(prompt, system_prompt):
            try:
                return self._extract_json_object(content)
            except ValueError:
                if fallback is not None:
                    return fallback
                raise

        return content

    def _expects_json(self, prompt: str, system_prompt: Optional[str]) -> bool:
        text = f"{system_prompt or ''}\n{prompt}".lower()
        return "valid json" in text or "respond only with json" in text

    def _strip_reasoning(self, text: str) -> str:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text.strip())
        return text.strip()

    def _extract_json_object(self, text: str) -> str:
        text = self._strip_reasoning(text)
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"No JSON object found in Ollama response: {text}")

        candidate = text[start : end + 1]
        json.loads(candidate)
        return candidate
