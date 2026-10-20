# Failure patterns in the curated dataset

The dataset (`data/dataset.json`, 82 items) is built by `dataset/generate.py` with a fixed seed.
Every item belongs to one pattern. The patterns were chosen, and then tuned by actually running
the corrector, so that each targeted fix moves the total score a visible step and no single round
solves everything.

The patterns fall into four kinds, and the kind decides who can fix them:

- **Policy**: the model makes a defensible choice that is not ours. A human decides what counts as
  correct; the prompt then states the rule.
- **Context**: the answer needs information that is not in the typed text. The fix is to give the
  model that information.
- **Ability**: the model knows what is wanted but does it unreliably. A described procedure helps,
  partly.
- **Data**: the answer cannot be recovered from anything the system has. No prompt fixes it; a human
  has to fix the data.

## The table

CER is the character error rate (lower is better). "Share" is the pattern's contribution to the
total CER, that is pattern CER times item count divided by 82. Numbers are means of three full runs
with `deepseek` (pass 1, 2026-10-20).

| Pattern | Kind | What it looks like | Items | Fixed by | v1 CER (share) | Before fix → after fix | Total CER step |
|---|---|---|---:|---|---|---|---|
| `plain_typos` | none | Ordinary slips: neighbor keys, dropped, swapped, doubled letters, missing spaces. `Teh quarterly repport is dueon Fiday` | 28 | v1 (any prompt) | 0.002 (0.001) | 0.103 → 0.002 | part of v0 → v1 |
| `casual_voice` | Policy | Slang, chat abbreviations, nonstandard grammar, all lowercase. v1 turns `tbh i dunno` into `To be honest, I don't know`. | 13 | v2: keep the writer's voice | 0.196 (0.031) | 0.196 → 0.004 | 0.079 → 0.051 |
| `glossary_names` | Context | People, projects and places typed by sound: `shivon`, `wakeen`, `kestrel` for Siobhan, Joaquin, Kestrl. | 12 | v3: inline `data/glossary.md` | 0.081 (0.012) | 0.116 → 0.003 | 0.051 → 0.037 |
| `pasted_verbatim` | Policy | Pasted text that must stay byte for byte: quoted UI strings with typos, code in backticks, URLs, emails, hashtags. `"Paymnet faild, plase try agian"` | 18 | v4: never touch pasted spans | 0.063 (0.014) | 0.047 → 0.006 | 0.037 → 0.028 |
| `shifted_hands` | Ability | The last 2 or 3 words typed with both hands one key to the right: `text me later` became `yrcy ,r ;syrt`. | 5 | v5: describe the drift and how to decode it | 0.268 (0.016) | 0.299 → 0.161 | 0.028 → 0.021 |
| `unknown_names` | Data | Like `glossary_names`, but the person or project is new and missing from the glossary: `keeva` for Caoimhe. | 6 | Nothing in the prompt. A human updates the glossary. | 0.078 (0.006) | stays 0.08 to 0.09 | the floor |

The full curve, with three runs per version: v0 0.109, v1 0.079, v2 0.051, v3 0.037, v4 0.028,
v5 0.021. The range between repeated runs of the same version is at most 0.007 (v2), so every step
from v1 to v5 is larger than the noise, and the run ranges of neighboring versions never overlap.

## What each fix teaches

**v1 is worse than doing nothing on two patterns.** On `casual_voice` the echo baseline scores 0.075
and v1 scores 0.196; on `pasted_verbatim` 0.042 against 0.063. A naive prompt does not only fail to
help, it damages what was already right. Only the per-pattern view shows this; the total improved.

**v2 has a side effect.** Keeping the writer's capitalization also kept typed names lowercase, so
`glossary_names` went from 0.081 to 0.116. The fix for one pattern hurt another.

**v3 has a side effect too.** With a glossary in the prompt the model starts seeing names
everywhere: `me and hmi` became `me and Niamh`, `who aye my yogurt` became `who Aoife is`.
`casual_voice` rose from 0.004 to between 0.008 and 0.025 in later versions. More context is not free.

**v5 is only a partial fix.** Even with the keyboard rows spelled out, the pattern's CER falls by
about half (0.299 to 0.161), not to zero. The remaining words are guesses (`start without me`
became `dusty tonight me`). Coach-written prompts in `docs/sessions/` decode better, so this is the
limit of one prompt, not of the model.

**The floor is a data problem.** After v5 the largest remaining slice is `unknown_names`. From v3
on, the glossary pulls unknown names toward known ones: `osheen` (Oisin) becomes Siobhan in every
run, and in some runs `dervela` (Dervla) becomes Siobhan too. No prompt can know a name nobody
wrote down. The right next step is outside the prompt, and it is a human's call.

## Tuning history

The dataset went through four drafts before the steps came out even. What was dropped and why is
in `docs/working.md`: a pattern of requests addressed to the AI (the model never fell for them), a
British spelling pattern (the model kept British spelling on its own), and fully shifted messages
(too noisy and too dominant).

## Known label issue

Case 66 (`pasted_verbatim`) was typed as `Tje menu offerd "expresso" annd "cappucino" adn nobody cared.`
and its ground truth ends in "nobody cares". The random typo turned one real word into another, so
"cared" is a fair reading. The Codex session flagged it for human review instead of bending the
prompt toward the label. It is left in place on purpose: it costs about 0.0006 of total CER and is a
live example of an agent auditing the data rather than gaming it.
