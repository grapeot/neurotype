# The self-improvement step

This is the meta-prompt for the last live step of the demo. Paste it into a coding agent
(Codex, Claude Code, Cursor) opened in this repo:

```
Consult SOP.md and run two improvement iterations on the current prompt.
```

That one line is the whole instruction. Everything the agent needs is already in the repo:
SOP.md says how to diagnose and what counts as an improvement, `run_eval.py` measures,
the dashboard shows what and why, and `data/` holds the context a prompt may use.

If the agent needs more structure, use this longer version:

```
Consult SOP.md and run two improvement iterations on the current prompt.
- Start from the best version in `python run_eval.py --compare`.
- Each iteration: pick one failure pattern, write the next prompts/vN.md with the
  header notes filled in, smoke test with --pattern, then run the full benchmark once.
- Keep a version only if its CER beats the best mean by more than the noise floor in SOP.md.
- Do not edit the dataset, the metric, or run_eval.py, and never copy dataset cases into a prompt.
- When done, show me a table: version, CER, change, kept or reverted, and what you would try next.
```

## Without a coding agent

`auto_improve.py` does the same loop with a coach model on AI Builder Space:

```
python auto_improve.py --iterations 2
```

It writes the new prompt versions to `prompts/`, the runs to `results/`, and a decision log to
`results/auto/`.

## What to expect

Two iterations usually produce one clear gain. Sometimes a change helps the pattern it targets
and hurts another one, so the total gets worse; sometimes the change is smaller than the noise.
Both outcomes are the evaluation system doing its job. The agent stops after two iterations and
the next decision is yours: continue, switch the model, fix the data, or stop.
