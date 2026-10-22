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
| `checkpoint-0` | Only the dataset (typed/meant pairs, no pattern labels), `requirements.txt`, `.env.example` and a task README. No metric, runner, client or prompts. A separate root commit. | Build the evaluation live (the ask below). |
| `checkpoint-a` | Dataset, metric, baseline (v0) and the naive prompt (v1) with three recorded runs. | Build the dashboard. |
| `checkpoint-b` | Plus the two-layer dashboard with rationales and repeated runs. | Diagnose v1's failure patterns, coach v2. |
| `checkpoint-c` | Plus v2 (the first coached fix), `SOP.md`, `IMPROVE.md`, `auto_improve.py`. | "Consult SOP.md and run two improvement iterations on the current prompt." |
| `main` | Plus the reference path v3 to v5, the pattern table, the site and the session records. | |

### The live flow

1. **Build the evaluation live from `checkpoint-0`.** Open a coding agent in the repo and paste:

   ```
   Build an evaluation for the corrector. Done means: messy/clean pairs in data/; a script that scores any version with normalized edit distance (edit distance divided by the length of the clean text; lower is better); a baseline that returns the input unchanged; then a first prompt v1: a plain prompt that asks the model to fix all spelling and typing errors, not tuned to the dataset, and returns JSON with the corrected text and a one-sentence rationale; and run the baseline and v1 on the full dataset.
   ```

   The agent gets the API details (base URL, authentication) from the AI Builder Coach MCP and
   writes the client itself. Measured with Codex CLI from a clean checkout, four runs: 63 to 141 s
   end to end; the baseline scored 0.1087 every time and v1 scored 0.064 to 0.068.
2. **Switch to `checkpoint-a`: the same ask, prepared earlier.** It has the reference evaluation
   (`run_eval.py`, CER, v0, v1 with three recorded runs; v1 is 0.079 there because its prompt is
   worded slightly differently). Continue with the dashboard, coaching and self-improvement steps
   from `checkpoint-a`, `-b` and `-c`.

Why the ask is worded this way: with only "a first prompt v1", the agent read the dataset and wrote
a v1 that already handled every failure pattern (0.038), which leaves nothing to coach. Without the
JSON output requirement, `deepseek` sometimes answered the typed text as if it were a request
("I can't send messages to Shivon for you"), and v1 scored 0.61 to 0.75, worse than doing nothing.
Naming the length of the clean text as the denominator makes the baseline match the reference
(0.1087); dividing by the longer string gives 0.1084.

### Reset commands

Park any live changes and (re)create a scratch branch at the checkpoint:

```bash
git stash -u && git switch -C live checkpoint-0   # before building the evaluation
git stash -u && git switch -C live checkpoint-a   # the same evaluation, prepared earlier; before building the dashboard
git stash -u && git switch -C live checkpoint-b   # before the coaching session (v2)
git stash -u && git switch -C live checkpoint-c   # before the self-improvement step
git switch main                                    # back to the full reference state
```

## Running the live steps with Codex

The `.venv` and `.env` are untracked, so they survive every switch between checkpoints. Set them up
once on `main` before class.

For the evaluation build at `checkpoint-0`, the agent needs the AI Builder Coach MCP
(`@aibuilders/mcp-coach-server`, configured under `[mcp_servers.ai-builders-coach]` in
`~/.codex/config.toml`). In the interactive Codex UI, approve its three calls when asked
(`get_base_url`, `explain_authentication_model`, `get_api_specification`); they add about two
seconds. With `codex exec` the calls fail unless the tools are pre-approved, because exec never asks:

```toml
[mcp_servers.ai-builders-coach.tools.get_base_url]
approval_mode = "approve"
[mcp_servers.ai-builders-coach.tools.get_api_specification]
approval_mode = "approve"
[mcp_servers.ai-builders-coach.tools.explain_authentication_model]
approval_mode = "approve"
```

Without them Codex fell back to fetching the public API documentation, which worked in our test
but skips the MCP you want to show.

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
