# Two prompt improvement iterations

Followed SOP.md using the existing .venv, activated before invoking .venv/bin/python. Starting best version: v2, three full runs, mean CER 0.05133, observed max-minus-min 0.0066. Used the SOP noise threshold 0.007.

## Iteration 1: v2 to v3 — glossary context

Read the worst failures and rationales, including cases 42, 43, 45, 50, 52 and 53. The model preserves phonetic names; ground truth expects canonical glossary names. Classification: context. Inlined only the existing data/glossary.md and gave matched names a scoped spelling/capitalization exception. This is a bounded, recoverable cluster; keyboard-shift failures were deferred to the second iteration.

Result: KEPT. glossary_names smoke CER 0.0011 versus parent mean 0.1159. First full CER 0.0344; three-run mean 0.03383 versus v2 0.05133 (gain 0.01750). No per-pattern mean regression exceeds 0.02. Three runs, range 0.0011, zero parse errors.

The first full run improved by 0.01693, exceeding 0.007. Two additional full runs established the three-run baseline required before iteration 2. Full-run CERs: 0.0344, 0.0333, 0.0338.

## Iteration 2: v3 to v4 — shifted hands

Read the latest parent failures and rationales for all five shifted cases (78–82), as well as the other worst failures. The model guesses words or abbreviations or leaves garbling unchanged; ground truth expects character-by-character decoding. Classification: ability. This pattern contributes the most remaining error. Added one scoped QWERTY decoding procedure with two original examples, retaining all parent instructions.

Result: KEPT. shifted_hands smoke CER 0.1936 versus parent mean 0.2629 (latest parent run 0.2759). Full CER 0.02660 versus v3 three-run mean 0.03383 (gain 0.00723, exceeding SOP 0.007). No per-pattern regression exceeds 0.02. One full run, zero parse errors; gain only narrowly clears the single-run threshold.

No additional full runs were required by the SOP because the single-run improvement exceeded 0.007. This is a narrow pass, not a three-run estimate of v4's mean.

## All-pattern review

| Pattern | v2 mean (3 runs) | v3 mean (3 runs) | v4 (1 run) |
|---|---:|---:|---:|
| plain_typos | 0.0028 | 0.0028 | 0.0023 |
| casual_voice | 0.0035 | 0.0063 | 0.0057 |
| glossary_names | 0.1159 | 0.0026 | 0.0011 |
| unknown_names | 0.1118 | 0.0799 | 0.0721 |
| pasted_verbatim | 0.0425 | 0.0437 | 0.0493 |
| shifted_hands | 0.2514 | 0.2629 | 0.1413 |

No mean pattern regression exceeds 0.02. All new full runs have zero parse errors. The glossary and keyboard examples pass the repository's benchmark-leak checker; no benchmark sentence or answer-only name was introduced into the prompts. Dataset, evaluation code, metric and model settings were not changed. Saved evaluation snapshots retain the prompt notes as they were at run time; final verdicts are in the current prompt files.

## Handoff

Best retained prompt: v4, full-run CER 0.0266, about 48.2% lower than the starting v2 mean. Both iterations are complete. Remaining issues include unreliable keyboard decoding, rewriting pasted/verbatim strings, and names whose canonical spellings are absent from repository context. Do not invent the missing names from expected answers. Case 66 also admits a plausible past-tense reading while its label expects present tense; flag it for human review rather than tailoring the prompt to the label.

Recommendation: confirm v4 with two further full runs before relying on its narrow margin; if further improvement is authorized, target preservation of pasted/verbatim spans. Ask the dataset owner to supply authentic context for unknown names and review ambiguous labels.

## Saved runs

- v3: 20261020-150818, CER 0.0344
- v3: 20261020-150837, CER 0.0333
- v3: 20261020-150854, CER 0.0338
- v4: 20261020-150912, CER 0.0266
