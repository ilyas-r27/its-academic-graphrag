"""Single entry point for every LLM call, so the provider can be swapped via .env."""
import json
import re

from kg import config

_client = None


def _get_client():
    global _client
    if _client is None:
        if not config.LLM_MODEL:
            raise RuntimeError("LLM_MODEL is empty. Fill LLM_* in .env first.")
        from openai import OpenAI

        _client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY or "none")
    return _client


def chat(prompt: str, system: str | None = None, temperature: float = 0.0) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = _get_client().chat.completions.create(
        model=config.LLM_MODEL, messages=messages, temperature=temperature
    )
    return resp.choices[0].message.content or ""


def chat_json(prompt: str, system: str | None = None) -> dict:
    """Ask for JSON and parse the first {...} block. Works with providers without JSON mode."""
    text = chat(prompt, system)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON in LLM output: {text[:200]}")
    return json.loads(m.group(0))
