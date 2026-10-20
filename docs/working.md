# Working log

Running notes from building this repo: decisions, measurements, and what changed and why.
Newest entries at the bottom of each section.

## Goal

A curated dataset plus a corrector that improve together, so that in a live class each targeted fix
moves the score a visible step: no saturation after one or two rounds, no impossible ceiling.

## Platform and model

- AI Builder Space, OpenAI-compatible, `https://space.ai-builders.com/backend/v1`.
- Candidates probed on six messages (2026-10-20):
  - `deepseek` (routed to DeepSeek V4.1 Flash): about 2 s per call, rewrites casual text heavily
    (expands "tbh", fixes "me and him"). Its defaults collide with a clear, nameable policy, which is
    what we want for teaching.
  - `grok-4-fast`: about 2.5 s, conservative (keeps slang, keeps lowercase). Fewer visible failures.
  - `gemini-3.8-flash`: 5 to 8 s per call, wraps JSON in code fences. Too slow for a live loop.
- Picked `deepseek`, temperature 0, max_tokens 700. Override with `NEUROTYPE_MODEL`.
- The platform adds about 400 prompt tokens of its own to every call (a one-word prompt reports
  416 prompt tokens). Rarely the model replies as if it were an agent with tools; the parser
  handles that by scoring the raw text.

## Dataset iterations

### Draft 1 (107 items, 7 patterns)
Patterns: plain_typos, casual_voice, lowercase_style, glossary_names, pasted_verbatim,
addressed_text, shifted_hands. v1 results (3 runs): 0.0925, 0.0881, 0.0865.

What we learned:
- `addressed_text` (messages that look like a request to the AI) never triggered: deepseek with a
  JSON instruction corrected all 12, CER 0.000. Dropped.
- One sentence about keeping the writer's voice fixed both `casual_voice` and `lowercase_style`
  (0.163 to 0.005 and 0.048 to 0.004). They are one pattern, not two. Merged.
- `shifted_hands` (10 items, half fully shifted) dominated the score (more than half of all error)
  and was most of the run-to-run noise (pattern CER 0.536, 0.475, 0.477).
- `pasted_verbatim` items were long, so each wrong "fix" cost only 1 to 3 characters (CER 0.012).

### Draft 2 (92 items, 6 patterns)
Added `british_spelling` (writer in London: colour, organise). deepseek kept British spelling on
its own (CER 0.004). Dropped. Shortened verbatim items: CER per item rose to about 0.05.

### Draft 3 (78 items, 5 patterns) and the reference path v1..v5
2 runs each: v0 0.1205, v1 0.0798, v2 0.0493, v3 0.0205, v4 0.0232 (sd 0.0065), v5 0.0106.

Problems found:
- shifted_hands before its fix was still noisy (v4 runs: 0.314 vs 0.186 on the pattern), which
  hid the verbatim step entirely.
- The glossary step was the largest (0.029) and the hint for shifted hands solved nearly everything,
  so v5 ended near perfect (82% exact). Too little headroom.
- One reply contained two JSON answers ("Wait, let me reconsider..."); the parser failed and scored
  1.0. Parser now takes the last complete JSON answer.
- Interaction worth teaching: the voice fix (v2) made glossary names worse (0.081 to 0.118),
  because "keep their capitalization" also kept "shivon" lowercase. It also made the model
  slightly too conservative ("wats" left unfixed).

### Draft 4 (80 items, 6 patterns)
- Voice items 16 to 13 and glossary items 16 to 12, to make their steps smaller.
- New `unknown_names` (6 items): people and projects that are not in the glossary yet. No prompt
  can recover them. They form the floor, and the right fix is a data fix, which is a human call.
- Verbatim items now quote UI strings and error messages with real typos
  ("Paymnet faild, plase try agian"), so a wrong fix costs more characters.
- shifted_hands down to 5 items with 2 or 3 drifted words each; dropped the least stable item.
- 4 more plain items (28) to reach 80.
- Result of draft 4 (3 runs each): v0 0.1112, v1 0.0753, v2 0.0501, v3 0.0336, v4 0.0281, v5 0.0174.
  The verbatim step (v3 to v4) was only 0.0055 because the quoted spans were inside long sentences.

### Draft 5 (final, 82 items, 6 patterns)
- Verbatim items rewritten short, each with two or more tempting spans, and 18 of them.
  Smoke test: v1 0.067, v3 0.048, v4 0.008 on the pattern.
- Dataset regenerates byte for byte from `dataset/generate.py` (checked in a clean copy).

## Final measurements

### Reference path, pass 1 (these runs are the ones committed in results/)
| Version | Runs | Mean | Range |
|---|---|---|---|
| v0 | 0.1087 | 0.1087 | deterministic |
| v1 | 0.0814, 0.0773, 0.0796 | 0.0794 | 0.0041 |
| v2 | 0.0538, 0.0472, 0.0530 | 0.0513 | 0.0066 |
| v3 | 0.0381, 0.0338, 0.0384 | 0.0368 | 0.0046 |
| v4 | 0.0291, 0.0266, 0.0284 | 0.0280 | 0.0025 |
| v5 | 0.0202, 0.0215, 0.0216 | 0.0211 | 0.0014 |

Per pattern (mean CER): see `dataset/PATTERNS.md`.
v5 was rerun after replacing one worked example (`;syrt` -> `later`) that was a token copied from
the dataset; the leak check flagged it.

### Reference path, pass 2 (clean copy, regenerated dataset, 262 s for all 16 runs)
v1 0.0794 / 0.0807 / 0.0787 (mean 0.0796), v2 0.0535 / 0.0539 / 0.0510 (0.0528),
v3 0.0331 / 0.0357 / 0.0369 (0.0352), v4 0.0285 / 0.0280 / 0.0284 (0.0283),
v5 0.0236 / 0.0197 / 0.0200 (0.0211). Same curve within noise.

### Noise floor
Largest max-min range over three runs of one version: 0.0066 (v2, pass 1). SOP.md and
`auto_improve.py` use 0.007. Smallest adjacent step on the reference path: v4 to v5, 0.0069 in pass 1
and 0.0072 in pass 2; run ranges of adjacent versions never overlap in either pass.
Main noise sources: shifted_hands (5 items whose decoding guesses change between runs) and
casual_voice after v3 (glossary names hallucinated into casual text in some runs).

### Timing and cost
- Full benchmark: 16.5 to 26.8 s per run, typically 17 to 18 s (82 calls, 32 in parallel).
- Tokens per run: v1 about 75k to 81k, v5 about 128k to 134k.
- Measured cost (platform usage delta around one v5 run, exactly 82 requests): $0.053.
  v1 is roughly $0.03.
- Two-iteration self-improvement session with `auto_improve.py`: 103 to 108 s, measured cost $0.32.
- Codex CLI (gpt-6-astra) with the one-line meta-prompt: 103 s for two iterations.

## Self-improvement sessions

All start from checkpoint-c (v2, mean 0.0513). Records in `docs/sessions/`.

Before the leak rule (development):
- Session 1: glossary kept (0.030 on one run); pasted text fixed its pattern (0.055 to 0.006 on the
  smoke test) but the total changed by only 0.002 because the parent baseline was a single lucky run
  (shifted_hands 0.204 in that run). Fix: the script now gives the parent three runs before comparing.
- Sessions 2 to 4: the coach copied benchmark cases into worked examples (shifted-hands cases
  verbatim, and once a quoted UI string). In a four-iteration session it added Caoimhe, Eamonn and
  Oisin to the prompt to "fix" unknown_names (0.082 to 0.029 on the smoke test). Fix: SOP.md now
  forbids copying cases and adding facts known only from expected outputs, and `auto_improve.py`
  rejects prompts that contain five-word chunks of expected outputs, three-word chunks or distinctive
  tokens of typed inputs, or proper names that exist only in expected outputs. The check only reads
  the `## System` and `## User` sections, since the notes never reach the model.

After the rule:
| Session | Driver | Iters | Time | Path | Best |
|---|---|---|---|---|---|
| A | script | 2 | 108 s | glossary 0.034, shifted 0.024 | 0.024 |
| B | script | 2 | 104 s | glossary 0.035, shifted 0.025 | 0.025 |
| C | script | 4 | 305 s | glossary 0.035, shifted 0.026, pasted 0.019 (three-run, shifted flagged worse), shifted 0.013 | 0.013 |
| D | Codex CLI | 2 | 103 s | glossary 0.034, shifted 0.027 (narrow single-run pass) | 0.027 |
| E | script | 2 | 103 s | glossary 0.036, pasted 0.022 | 0.022 |

No leaks after the rule. Codex also flagged case 66 as an ambiguous label ("cared" vs "cares").
No regression verdict appeared in two-iteration sessions; regressions show up inside a kept step
(C iteration 3 made shifted_hands worse) and plateaus start around iteration 4 or 5, where the
remaining error is mostly unknown names.

## Decisions taken without asking (road not taken)
- Corrector `deepseek` rather than `grok-4-fast` (too conservative, fewer visible failures) or
  `gemini-3.8-flash` (5 to 8 s per call).
- Pattern labels are visible in results and on the dashboard. The live diagnosis is therefore
  easier than a blind one; the human decision (which pattern, what policy) is still required.
- `dataset/PATTERNS.md` and the reference v3 to v5 exist only on `main`, after checkpoint-c, so an
  agent working from a checkpoint cannot read the answers.
- Server uses the Python standard library only; dashboard and site are vanilla JS, no build step.
