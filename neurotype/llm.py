"""Thin client for AI Builder Space (OpenAI-compatible)."""

from __future__ import annotations

import os
import time
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_URL = "https://space.ai-builders.com/backend/v1"
DEFAULT_MODEL = "deepseek"


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()
_client: OpenAI | None = None


def model_name() -> str:
    return os.environ.get("NEUROTYPE_MODEL", DEFAULT_MODEL)


def client() -> OpenAI:
    global _client
    if _client is None:
        token = os.environ.get("AI_BUILDER_TOKEN")
        if not token:
            raise SystemExit(
                "AI_BUILDER_TOKEN is not set. Copy .env.example to .env and add your token."
            )
        _client = OpenAI(
            base_url=os.environ.get("AI_BUILDER_BASE_URL", DEFAULT_BASE_URL),
            api_key=token,
            timeout=60,
            max_retries=0,
        )
    return _client


def chat(messages: list[dict], model: str | None = None, max_tokens: int = 700,
         temperature: float = 0.0, retries: int = 3, **extra) -> tuple[str, dict]:
    """Return (text, usage). Retries transient failures with backoff."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            resp = client().chat.completions.create(
                model=model or model_name(),
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **extra,
            )
            text = resp.choices[0].message.content or ""
            usage = resp.usage.model_dump() if resp.usage else {}
            return text, usage
        except Exception as exc:  # network errors, 429, 5xx
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"model call failed after {retries} attempts: {last}")
