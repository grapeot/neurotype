# Auto-improve session 2026-10-20 14:55
Start: v2 (mean CER 0.0513), coach gpt-5, corrector deepseek, noise floor 0.007

## Iteration 1: v3
- Pattern: glossary_names (context)
- Diagnosis: The model leaves phonetically typed names and project terms unchanged and preserves their typed lowercase form because it lacks authoritative spellings and interprets v2's voice-preservation rule too broadly. The ground truth expects glossary spellings and capitalization, as shown by cases #50, #43, #52, #53, #48, #45, #51, #42, #49, #46, #44, and #47.
- Hypothesis: Inline data/glossary.md and explicitly require its canonical spelling and capitalization when a token clearly refers to a glossary entry. This should substantially reduce glossary_names CER while retaining v2's voice-preservation behavior for ordinary text.
- Smoke test (12 cases): 0.113 -> 0.003
- Full run: 0.0513 -> 0.0357 (20261020-145552-auto)
- Verdict: KEEP: v3 improves CER by 0.0156
- Time: 33s

## Iteration 2: v4
- Pattern: shifted_hands (ability)
- Diagnosis: The model treats text produced with the typist's hands shifted one key to the right on a QWERTY keyboard as unrecognizable or ambiguously misspelled instead of reversing the systematic offset. This leaves shifted spans unchanged in cases 79 and 81, makes only an ordinary-word correction in case 78, and guesses abbreviations or altered wording in cases 80 and 82.
- Hypothesis: Add a step-by-step QWERTY offset-decoding procedure with original examples. The model should recognize contiguous right-shifted spans, map each character to the key immediately to its left, and validate the result in sentence context. This should sharply reduce shifted_hands CER without changing the established voice-preservation or glossary policies.
- Smoke test (5 cases): 0.250 -> 0.108
- Full run: 0.0346 -> 0.0245 (20261020-145703-auto)
- Verdict: KEEP: v4 improves CER by 0.0101
- Time: 71s

Session time: 103s. Best version now: v4 (mean CER 0.0245).

Next decision belongs to a human: continue, change the model, fix the data, or stop.
