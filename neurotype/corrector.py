"""Correctors. v0 echoes the input; every other version is a prompt file.

A prompt file lives at prompts/<version>.md and looks like:

    # v2: one-line title
    Notes for humans (what changed and why). Ignored by the model.

    ## System
    ...system prompt...

    ## User
    ...user message template, with {{text}} where the typed text goes...

Inside either section, {{file:path/to/file}} inlines a file from the repo.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import llm

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"


@dataclass
class Prompt:
    version: str
    title: str
    notes: str
    system: str
    user: str
    source: str

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.source.encode()).hexdigest()[:12]


def _inline_files(text: str) -> str:
    return re.sub(
        r"\{\{file:([^}]+)\}\}",
        lambda m: (ROOT / m.group(1).strip()).read_text().strip(),
        text,
    )


def load_prompt(version: str) -> Prompt:
    path = PROMPTS / f"{version}.md"
    source = path.read_text()
    title_m = re.match(r"#\s*(.+)", source)
    title = title_m.group(1).strip() if title_m else version
    parts = re.split(r"^##\s+(System|User)\s*$", source, flags=re.M)
    notes = parts[0].split("\n", 1)[1].strip() if "\n" in parts[0] else ""
    sections = {parts[i].lower(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
    system = _inline_files(sections.get("system", ""))
    user = _inline_files(sections.get("user", "{{text}}"))
    return Prompt(version, title, notes, system, user, source)


def list_versions() -> list[str]:
    vs = ["v0"] + sorted(
        (p.stem for p in PROMPTS.glob("v*.md")),
        key=lambda v: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", v)],
    )
    return list(dict.fromkeys(vs))


def parse_output(raw: str) -> tuple[str, str, bool]:
    """Extract (corrected, rationale, parse_error) from a model reply."""
    text = raw.strip()
    # Collect every JSON object in the reply; models sometimes answer twice
    # ("Wait, let me reconsider...") and the last answer is the final one.
    decoder = json.JSONDecoder()
    found: list[dict] = []
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("corrected"), str):
            found.append(obj)
    if found:
        obj = found[-1]
        return obj["corrected"], str(obj.get("rationale", "")), False
    return text, "(the reply was not valid JSON; scored as plain text)", True


def correct(version: str, text: str, prompt: Prompt | None = None) -> dict:
    """Run one corrector on one input. Returns output, rationale and usage."""
    if version == "v0":
        return {"output": text, "rationale": "Baseline: returns the input unchanged.",
                "raw": text, "parse_error": False, "usage": {}}
    prompt = prompt or load_prompt(version)
    messages = []
    if prompt.system:
        messages.append({"role": "system", "content": prompt.system})
    messages.append({"role": "user", "content": prompt.user.replace("{{text}}", text)})
    raw, usage = llm.chat(messages)
    output, rationale, err = parse_output(raw)
    return {"output": output, "rationale": rationale, "raw": raw,
            "parse_error": err, "usage": usage}
