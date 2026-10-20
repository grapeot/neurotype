# Auto-improve session 2026-10-20 14:53
Start: v2 (mean CER 0.0513), coach gpt-5, corrector deepseek, noise floor 0.007

## Iteration 1: v3
- Pattern: glossary_names (context)
- Diagnosis: The model leaves recognizable names and project terms misspelled or lowercased because it lacks authoritative spellings and interprets v2's casing rule too broadly. This affects at least cases #42, #43, #45, #46, #48, #50, #51, #52, #53 and #44: their rationales explicitly say names or product names were left as written, while the ground truth expects the canonical glossary spelling and capitalization.
- Hypothesis: Inline data/glossary.md and instruct the model to use its canonical spelling and capitalization when a typed token clearly refers to a glossary entry. This should substantially reduce glossary_names CER while retaining v2's voice-preservation behavior elsewhere.
- Smoke test (10 cases): 0.123 -> 0.001
- Full run: 0.0513 -> 0.0342 (20261020-145404-auto)
- Verdict: KEEP: v3 improves CER by 0.0171
- Time: 32s

## Iteration 2: v4
- Pattern: shifted_hands (ability)
- Diagnosis: The model treats right-shifted QWERTY text as unrecoverable gibberish instead of reversing the systematic keyboard offset. In cases #78, #79, #80, and #81 it leaves most or all shifted spans unchanged, while in #82 it recognizes the offset but restyles the decoded words as chat abbreviations. The ground truth expects each affected character to be mapped to the key immediately to its left, with the resulting wording preserved.
- Hypothesis: Add a step-by-step procedure for detecting and reversing one-key-right QWERTY hand shifts, including punctuation keys, and instruct the model not to abbreviate the decoded result. This should sharply reduce shifted_hands CER without changing behavior on ordinary typos or other patterns.
- Smoke test (5 cases): 0.276 -> 0.079
- Full run: 0.0344 -> 0.0235 (20261020-145519-auto)
- Verdict: KEEP: v4 improves CER by 0.0109
- Time: 76s

Session time: 107s. Best version now: v4 (mean CER 0.0235).

Next decision belongs to a human: continue, change the model, fix the data, or stop.
