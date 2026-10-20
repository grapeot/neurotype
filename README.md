# Neurotype

Type freely without caring about spelling; an AI reconstructs what you meant.

This repo is a teaching demo for managing an AI the way you would manage a person:
define what "done" means, build an evaluation, make the system observable, coach it from
failure patterns, write the coaching down as an SOP, and then let the AI improve itself
by following that SOP while a human decides when to stop.

**Project site, with the story and the dashboard on recorded results:** https://grapeot.github.io/neurotype/
(source: `docs/`; repository: https://github.com/grapeot/neurotype)

## Setup

```bash
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env        # then put your AI Builder Space token in .env
```

The model runs on [AI Builder Space](https://space.ai-builders.com) (OpenAI-compatible).
The token is read from `AI_BUILDER_TOKEN` in `.env` or the environment. It is never sent to
the browser and never committed. The corrector model is `deepseek` (temperature 0); set
`NEUROTYPE_MODEL` to try another. The self-improvement coach is `gpt-5`.

## The pieces

| Piece | Where | What it does |
|---|---|---|
| App | `server.py`, `app/index.html` | Type garbled text, get the reconstruction and the model's rationale. |
| Dataset | `data/dataset.json`, built by `dataset/generate.py` | 82 short messages: what was typed and what was meant. Seeded, so it rebuilds byte for byte. |
| Failure patterns | `dataset/PATTERNS.md` | The six patterns, their kind (policy, context, ability, data), the fix for each and its measured effect. |
| Writer context | `data/glossary.md` | Names and projects the writer mentions often. |
| Metric | `neurotype/metric.py` | Character error rate (CER): edit distance divided by the length of the ground truth. **Lower is better.** Exact-match rate as a secondary metric. |
| Baseline | version `v0` | Echoes the input unchanged. Any real corrector must beat it. |
| Correctors | `prompts/v1.md` … `v5.md` | One prompt file per version. The notes at the top say which failure pattern it fixes and what the human decided. |
| Runner | `run_eval.py` | Runs a version over the whole dataset, 32 calls in parallel, and saves every case. |
| Results | `results/<version>/<run>.json`, `results/index.json` | Every run, every case, with output and rationale. |
| Dashboard | `app/dashboard.html` | Layer 1 (what): versions, repeated runs, range, CER per pattern. Layer 2 (why): each case with diff and rationale, compared with another run. |
| SOP | `SOP.md` | The coaching session written down as a repeatable procedure. |
| Self-improvement | `IMPROVE.md`, `auto_improve.py` | The one-line meta-prompt for a coding agent, and the same loop as a script. |
| Site | `docs/` | The static story page and a copy of the dashboard with recorded results. |
| Log | `docs/working.md` | How the dataset and corrector were tuned together, with every measurement. |

## Run it

```bash
python server.py                 # the app at http://127.0.0.1:8000, dashboard at /dashboard.html

python run_eval.py v0            # baseline, no API calls
python run_eval.py v1            # one full benchmark run of prompts/v1.md
python run_eval.py v1 --runs 3   # the same version three times: how much does the score move by itself?
python run_eval.py v3 --pattern glossary_names   # smoke test on one pattern, a few seconds, not saved
python run_eval.py --compare     # every version: mean CER, spread, CER per pattern

python auto_improve.py --iterations 2   # the self-improvement loop, scripted
```

## Measured results

Means of three full runs, `deepseek`, 2026-10-20. Two independent passes from a clean state.

| Version | What changed | Pass 1 CER (runs) | Pass 2 CER | Exact |
|---|---|---|---|---:|
| v0 | echo baseline | 0.109 | 0.109 | 0% |
| v1 | naive prompt | 0.079 (0.081, 0.077, 0.080) | 0.080 | 34% |
| v2 | keep the writer's voice | 0.051 (0.054, 0.047, 0.053) | 0.053 | 52% |
| v3 | inline the glossary | 0.037 (0.038, 0.034, 0.038) | 0.035 | 60% |
| v4 | never touch pasted text | 0.028 (0.029, 0.027, 0.028) | 0.028 | 75% |
| v5 | decode drifted hands | 0.021 (0.020, 0.022, 0.022) | 0.021 | 75% |

The largest range between repeated runs of one version is 0.007. Every step from v1 to v5 is larger,
and the run ranges of neighboring versions never overlap. What remains after v5 is mostly names that
are not in the glossary, which no prompt can fix. Details per pattern: `dataset/PATTERNS.md`.

**Time and cost.** A full benchmark run takes 17 to 25 seconds (82 calls) and 75,000 to 135,000
tokens, about $0.03 (v1) to $0.05 (v5) of platform credit. A two-iteration self-improvement session
takes about 105 seconds and $0.32 with `auto_improve.py`; Codex CLI with the one-line meta-prompt
took 103 seconds. Recorded sessions are in `docs/sessions/`.

## Live-demo checkpoints

The demo is built live, one step at a time. Each step has a git tag so a presenter can reset to a
known good state before it:

| Tag | State | Next live step |
|---|---|---|
| `checkpoint-a` | Dataset, metric, baseline (v0) and the naive prompt (v1) with three recorded runs. | Build the dashboard. |
| `checkpoint-b` | Plus the two-layer dashboard with rationales and repeated runs. | Diagnose v1's failure patterns, coach v2. |
| `checkpoint-c` | Plus v2 (the first coached fix), `SOP.md`, `IMPROVE.md`, `auto_improve.py`. | "Consult SOP.md and run two improvement iterations on the current prompt." |
| `main` | Plus the reference path v3 to v5, the pattern table, the site and the session records. | |

To reset before a live step, park any live changes and (re)create a scratch branch at the checkpoint:

```bash
git stash -u && git switch -C live checkpoint-a   # before building the dashboard
git stash -u && git switch -C live checkpoint-b   # before the coaching session (v2)
git stash -u && git switch -C live checkpoint-c   # before the self-improvement step
git switch main                                    # back to the full reference state
```

## Running the live step with Codex

The self-improvement step is one line to a coding agent opened in the repo:

```
Consult SOP.md and run two improvement iterations on the current prompt. Use .venv/bin/python to run the scripts.
```

What we learned running it with Codex CLI (two iterations took 103 seconds):

- Tell the agent to use `.venv/bin/python`. Otherwise it may reach for a system Python without `openai`.
- Codex strips environment variables that look like secrets (anything with TOKEN or KEY in the name)
  from the commands it runs, so an exported `AI_BUILDER_TOKEN` does not reach `run_eval.py`. Put the
  token in `.env` instead; the code reads it from there.
- If Codex rejects its default model ("model is not supported"), pass one explicitly, for example
  `codex exec -m gpt-6-astra ...`.
- Network access must be allowed for the sandbox, for example
  `codex exec -s workspace-write -c sandbox_workspace_write.network_access=true "<the line above>"`.

If no coding agent is at hand, `python auto_improve.py --iterations 2` runs the same loop (about 105 s).

## Publish the site

```bash
python scripts/build_site.py      # copies the dashboard, assets and results/ into docs/
python -m http.server -d docs 8080   # preview at http://127.0.0.1:8080
```

Then enable GitHub Pages for the `docs/` folder of the main branch. The published pages read
recorded results only. No key, no model call.
