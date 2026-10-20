# Neurotype

Type freely without caring about spelling; an AI reconstructs what you meant.

This repo is a teaching demo for managing an AI the way you would manage a person:
define what "done" means, build an evaluation, make the system observable, coach it from
failure patterns, write the coaching down as an SOP, and then let the AI improve itself
by following that SOP while a human decides when to stop.

## Setup

```bash
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env        # then put your AI Builder Space token in .env
```

The model runs on [AI Builder Space](https://space.ai-builders.com) (OpenAI-compatible).
The token is read from `AI_BUILDER_TOKEN` in `.env` or the environment. It is never sent to
the browser and never committed. The default model is `deepseek`; set `NEUROTYPE_MODEL` to
try another.

## The pieces

| Piece | Where | What it does |
|---|---|---|
| App | `server.py`, `app/index.html` | Type garbled text, get the reconstruction and the model's rationale. |
| Dataset | `data/dataset.json`, built by `dataset/generate.py` | 82 short messages: what was typed and what was meant. |
| Writer context | `data/glossary.md` | Names and projects the writer mentions often. |
| Metric | `neurotype/metric.py` | Character error rate (CER): edit distance divided by the length of the ground truth. **Lower is better.** |
| Baseline | version `v0` | Echoes the input unchanged. Any real corrector must beat it. |
| Correctors | `prompts/v1.md`, `v2.md`, ... | One prompt file per version, with notes on what changed and why. |
| Runner | `run_eval.py` | Runs a version over the whole dataset concurrently and saves the result. |
| Results | `results/<version>/<run>.json`, `results/index.json` | Every run, every case, with output and rationale. |

## Run it

```bash
python server.py                 # the app at http://127.0.0.1:8000

python run_eval.py v0            # baseline, no API calls
python run_eval.py v1            # one full benchmark run of prompts/v1.md
python run_eval.py v1 --runs 3   # the same version three times: how much does the score move by itself?
python run_eval.py v1 --pattern casual_voice   # quick smoke test on one slice, not saved
python run_eval.py --compare     # table of every version: mean CER, spread, CER per pattern
```

A full benchmark run takes about 17 to 25 seconds (82 items, 32 parallel calls).

## Live-demo checkpoints

The demo is built live, one step at a time. Each step has a git tag so a presenter can reset to a
known good state before it:

| Tag | State |
|---|---|
| `checkpoint-a` | Dataset, metric, baseline (v0) and the naive prompt (v1, three recorded runs). |
| `checkpoint-b` | Plus the two-layer dashboard with rationales. |
| `checkpoint-c` | Plus v2 (the first coached fix) and `SOP.md`, ready for the self-improvement step. |

```bash
git stash -u                      # park any live changes
git switch -C live checkpoint-b   # (re)create a scratch branch at the checkpoint
```
