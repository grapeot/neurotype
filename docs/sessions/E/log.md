# Auto-improve session 2026-10-20 15:15
Start: v2 (mean CER 0.0513), coach gpt-5, corrector deepseek, noise floor 0.007

## Iteration 1: v3
- Pattern: glossary_names (context)
- Diagnosis: The model leaves recoverable names and product terms misspelled or incorrectly lowercased because v2 tells it to preserve capitalization but gives it no authoritative spelling context. The ground truth expects canonical glossary spellings and capitalization, as shown in cases 42, 43, 45, 48, 50, 51, 52, and 53.
- Hypothesis: Inline data/glossary.md and explicitly make its canonical spelling and capitalization override the general casing-preservation rule when a token is a plausible typo or phonetic rendering of a glossary entry. This should substantially reduce glossary_names CER without changing ordinary wording or style.
- Smoke test (8 cases): 0.139 -> 0.002
- Full run: 0.0513 -> 0.0370 (20261020-151543-auto)
- Verdict: KEEP: v3 improves CER by 0.0143
- Time: 31s

## Iteration 2: v4
- Pattern: pasted_verbatim (policy)
- Diagnosis: The model corrects misspellings inside text that is being quoted, displayed, or referenced verbatim, while the ground truth expects only the surrounding prose to be repaired. It rewrites quoted messages in cases 60, 61, 62, 64, 65, 66, 67, 68, 69, 70, and 71, and similarly alters literal email addresses, code, hashtags, and identifiers in cases 73, 75, and 77.
- Hypothesis: Explicitly make quoted text and literal strings immutable—including text in quotation marks or backticks, email addresses, hashtags, and identifiers—while continuing to repair surrounding prose. This should substantially reduce pasted_verbatim CER without affecting ordinary typo correction or glossary matching.
- Smoke test (11 cases): 0.068 -> 0.006
- Full run: 0.0356 -> 0.0219 (20261020-151654-auto)
- Verdict: KEEP: v4 improves CER by 0.0137
- Time: 72s

Session time: 103s. Best version now: v4 (mean CER 0.0219).

Next decision belongs to a human: continue, change the model, fix the data, or stop.
