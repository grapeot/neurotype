# Auto-improve session 2026-10-20 14:57
Start: v2 (mean CER 0.0513), coach gpt-5, corrector deepseek, noise floor 0.007

## Iteration 1: v3
- Pattern: glossary_names (context)
- Diagnosis: The model leaves misspelled or phonetically typed glossary names unchanged and preserves their incorrect casing because v2 tells it to keep capitalization and provides no authoritative spelling context. This affects people and product names in cases #42, #43, #44, #45, #46, #47, #48, #49, #50, #51, #52, and #53.
- Hypothesis: Inline data/glossary.md and instruct the model to use its canonical spelling and capitalization when a typed term clearly refers to a glossary entry. This should substantially reduce glossary_names CER while retaining v2's voice-preservation policy for text not covered by the glossary.
- Smoke test (12 cases): 0.113 -> 0.003
- Full run: 0.0513 -> 0.0352 (20261020-145737-auto)
- Verdict: KEEP: v3 improves CER by 0.0161
- Time: 34s

## Iteration 2: v4
- Pattern: shifted_hands (ability)
- Diagnosis: The model treats text produced with the typist's hands shifted one key to the right as unrelated gibberish or guesses ordinary words instead of reversing the systematic keyboard offset. In cases 78, 79, and 81 it leaves most or all of the shifted passage unchanged; in cases 80 and 82 it guesses abbreviations or shortened wording rather than decoding every character using the QWERTY layout.
- Hypothesis: Add a step-by-step procedure for detecting contiguous right-shifted QWERTY text and decoding each character to the key immediately to its left, with original worked examples. This should sharply reduce shifted_hands CER while preserving other text because the transformation is restricted to garbled spans that decode into coherent context.
- Smoke test (5 cases): 0.250 -> 0.113
- Full run: 0.0340 -> 0.0256 (20261020-145850-auto)
- Verdict: KEEP: v4 improves CER by 0.0084
- Time: 72s

## Iteration 3: v5
- Pattern: pasted_verbatim (policy)
- Diagnosis: The model corrects typos inside text being quoted, displayed, or referenced verbatim instead of preserving the literal content; the ground truth expects corrections only in the surrounding narration. This occurs in quoted messages and labels (cases 60, 62, 61, 71, 65, and 64), code and identifiers (cases 73, 77, and 72), and other reproduced text such as signs or logs.
- Hypothesis: Explicitly protect quoted text, code spans, URLs, hashtags, identifiers, and other content presented as a literal transcription, while still correcting typos in the surrounding prose. This should substantially reduce pasted_verbatim CER without changing behavior on ordinary unquoted text.
- Smoke test (12 cases): 0.058 -> 0.000
- Full run: 0.0258 -> 0.0190 (20261020-150005-auto)
- Verdict: KEEP: v5 improves CER by 0.0067 (three-run mean) (patterns that got worse: shifted_hands)
- Time: 113s

## Iteration 4: v6
- Pattern: shifted_hands (ability)
- Diagnosis: The model recognizes shifted-hands spans but substitutes contextually plausible phrases instead of applying the deterministic key-left mapping character by character. In #81, #78, and #82, its claimed decodings do not match the supplied QWERTY mapping; for example, #81 mechanically decodes to “thursday afternoon,” but the model invents “the conference room.”
- Hypothesis: Strengthen the shifted-hands procedure with a mandatory mechanical pass, an explicit prohibition on contextual guessing, and character-by-character verification that preserves span length and spaces. This should sharply reduce shifted_hands CER without affecting other patterns because the added procedure applies only after a span has been identified as consistently right-shifted.
- Smoke test (5 cases): 0.150 -> 0.116
- Full run: 0.0190 -> 0.0134 (20261020-150133-auto)
- Verdict: KEEP: v6 improves CER by 0.0056 (three-run mean)
- Time: 85s

Session time: 305s. Best version now: v6 (mean CER 0.0134).

Next decision belongs to a human: continue, change the model, fix the data, or stop.
