# Auto-improve session 2026-10-20 14:45
Start: v2 (mean CER 0.0513), coach gpt-5, corrector deepseek, noise floor 0.007

## Iteration 1: v3
- Pattern: glossary_names (context)
- Diagnosis: The model leaves misspelled or phonetic variants of known names and project terms unchanged because it lacks authoritative spellings and interprets the v2 voice-preservation rule as requiring their original casing. The ground truth expects glossary-listed terms to be restored to their canonical spelling and capitalization, as in cases #50 (Cafe Lumiere, Joaquin, Bluefynn), #43 (Joaquin, Niamh, Halcyon), #52 (Saoirse, Tadhg, Halcyon), #53 (Ngozi, Joaquin, Bluefynn), and #42 (Siobhan, Marigold).
- Hypothesis: Inline data/glossary.md and explicitly require canonical glossary spelling and capitalization when a typed token is a plausible variant. This should substantially reduce glossary_names CER while preserving v2's rule against general restyling.
- Smoke test (12 cases): 0.113 -> 0.000
- Full run: 0.0513 -> 0.0341 (20261020-144619-auto)
- Verdict: KEEP: v3 improves CER by 0.0172
- Time: 34s

## Iteration 2: v4
- Pattern: shifted_hands (ability)
- Diagnosis: The model treats text entered with the typist's hands shifted one key to the right as unrecoverable gibberish or guesses isolated corrections instead of reversing the systematic keyboard offset. In #81, "yjitdfsu sgyrtmppm" should decode to "thursday afternoon"; in #78, "dysty eoyjpiy ,r" should decode to "start without me"; and in #80, "yrcy ,r ;syrt" should decode to "text me later". In #82 it partly recognizes the offset but restyles the decoded words "you are" as "u r" rather than restoring them exactly.
- Hypothesis: Add a step-by-step QWERTY shifted-hands decoding procedure with worked examples. This should substantially reduce shifted_hands CER by making the model test a consistent one-key-left translation before guessing or leaving gibberish unchanged, while preserving the existing voice and glossary rules.
- Smoke test (5 cases): 0.220 -> 0.000
- Full run: 0.0324 -> 0.0229 (20261020-144729-auto)
- Verdict: KEEP: v4 improves CER by 0.0095
- Time: 70s

## Iteration 3: v5
- Pattern: pasted_verbatim (policy)
- Diagnosis: The model corrects typos inside text that the writer is quoting, displaying, or reproducing verbatim, while the ground truth expects only the surrounding prose to be repaired and the literal content to remain byte-for-byte unchanged. This affects quoted error messages and interface text (#60, #61, #62, #64, #65), quoted labels or reported strings (#66, #67, #68, #69, #70, #71), and literal code-like identifiers or commands (#72, #73, #77).
- Hypothesis: Add an explicit preservation rule for quoted text, backtick-delimited text, hashtags, paths, commands, identifiers, and other pasted literals. Tell the model to correct typos outside those spans but copy every character inside them exactly. This should substantially reduce pasted_verbatim CER without changing the existing typo, voice, glossary, or shifted-hands behavior.
- Smoke test (9 cases): 0.069 -> 0.007
- Full run: 0.0221 -> 0.0124 (20261020-144842-auto)
- Verdict: KEEP: v5 improves CER by 0.0097
- Time: 73s

## Iteration 4: v6
- Pattern: unknown_names (ability)
- Diagnosis: The model treats the glossary as an exhaustive list of proper nouns, leaving plausible phonetic spellings unchanged in cases #54, #55, #58, and #59, while sometimes forcing a weak glossary match instead of the contextually supported name in #56. It also inconsistently restores capitalization for inferred names and organizations in #54, #55, #57, #58, and #59.
- Hypothesis: Add a step-by-step procedure for recognizing phonetically typed proper nouns that are not in the glossary, choosing the conventional spelling supported by pronunciation and context, and restoring proper-noun capitalization. Require strong phonetic evidence before applying a glossary entry so weak matches such as "osheen"→"Siobhan" are rejected. This should substantially reduce unknown_names CER while preserving exact glossary normalization and the rule against general restyling.
- Smoke test (6 cases): 0.082 -> 0.029
- Full run: 0.0123 -> 0.0093 (20261020-144959-auto)
- Verdict: NO CLEAR GAIN: change +0.0031 (three-run mean) is within noise (0.007); keep v5
- Time: 112s

Session time: 289s. Best version now: v5 (mean CER 0.0123).

Next decision belongs to a human: continue, change the model, fix the data, or stop.
