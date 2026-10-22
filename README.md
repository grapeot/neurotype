# Neurotype

Type freely without caring about spelling; an AI reconstructs what you meant.

This is the starting point of a live demo. The task for this step is to build an evaluation for
the corrector, so we can tell whether any version of it is getting better.

## What is here

`data/dataset.json` holds 82 pairs of what someone typed (`messy_text`) and what they meant
(`ground_truth`).

The corrector runs on AI Builder Space (OpenAI-compatible) with the `deepseek` model at
temperature 0. The AI Builder Coach MCP has the API details: base URL and authentication.

## Setup

```bash
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env        # then put your AI Builder Space token in .env
```
