# SOP: improving the Neurotype corrector

Distilled from the first coaching session (v1 to v2). It turns that one conversation into a
procedure anyone, or any AI, can repeat. One iteration fixes one failure pattern.

## What we learned in the coaching session

**Problem.** v1 scored CER 0.079 (mean of three runs). Its aggregate number gave no hint about what to fix.

**Diagnosis.** We sorted cases by CER and read the worst ones with their rationales. One group
stood out: casual messages. The model expanded "tbh" to "To be honest", changed "me and him" to
"He and I", capitalized lowercase messages and added periods. Its rationales said things like
"fixed grammar" and "standard written form". The model was not failing at its job; it was doing a
different job than ours. That is a **policy** question, and only a person can answer it.

**Decision (human).** Neurotype restores the words you meant. It does not restyle you. The ground
truth already said so: it keeps slang, informal grammar and lowercase.

**Fix.** v2 adds one paragraph: repair keystroke mistakes only; keep wording, slang, grammar,
capitalization and punctuation.

**Verification.** casual_voice CER fell from 0.196 to 0.004 and the total from 0.079 to
0.051, a step four times larger than the run-to-run range (0.007). We also checked every other
pattern and found a side effect: glossary names got worse (0.081 to 0.116), because "keep their
capitalization" now kept "shivon" in lowercase. A fix for one pattern can hurt another, so
always read the per-pattern table, not only the total.

## The procedure

### Step 1. Measure where you stand
Run the current best version. If it has fewer than three full runs, run it until it has three.

    python run_eval.py --compare
    python run_eval.py vN --runs 3

Read Layer 1 of the dashboard: mean CER, the spread between repeated runs, and CER per pattern.

*Verify:* you can state the noise floor. On this dataset with `deepseek`, repeated runs of the same
version differ by up to about **0.007** (max minus min of three runs). This is the noise floor.
A change smaller than that is not evidence of anything.

### Step 2. Find one failure pattern
Open Layer 2 for the latest run, show errors only, sort worst first. Read at least five failing
cases together with their rationales. Group them, and write one sentence of the form:
"The model does X; the ground truth expects Y."

*Verify:* your sentence explains at least three cases, and you can name which pattern it is.
Prefer the pattern that contributes the most error (CER times number of items), not the single
worst case.

### Step 3. Decide what kind of failure it is
| Kind | Sign | What to do |
|---|---|---|
| Policy | The model's choice is defensible, just not ours. | The ground truth is the policy. State the rule explicitly in the prompt and write the decision in the prompt notes. If the ground truth itself looks inconsistent, stop and ask a human. |
| Context | The right answer needs information that is not in the input. | Look in `data/` for it and inline it with `{{file:data/...}}`. Never invent facts the repo does not contain. |
| Ability | The model knows what is wanted but does it unreliably. | Describe the procedure step by step, with two or three worked examples. |
| Data | The right answer cannot be recovered from the input plus available context, or the label looks wrong. | Do not prompt-hack around it. Write it down and hand it to a human. |

*Verify:* you wrote the kind and the reason in one line.

### Step 4. Change one thing
Copy the current prompt to the next version and edit only what addresses this pattern.

    cp prompts/vN.md prompts/vN+1.md

Update the header: title, the failure pattern you saw, the decision, the fix. Keep the
`## System` / `## User` structure and the JSON reply format with `corrected` and `rationale`.

Examples in the prompt must be your own. Never copy a case from `data/dataset.json` into the
prompt, and never add a fact you only know from the expected outputs (a name that appears in no
file under `data/`). Both are grading your own exam: the score goes up and stops meaning anything.

*Verify:* the diff between the two files is small, every added line maps to the pattern, and no
sentence from the dataset appears in the prompt.

### Step 5. Smoke test
    python run_eval.py vN+1 --pattern <pattern>

This is fast (a few seconds) and is not saved. The targeted cases should improve.

*Verify:* the pattern's CER dropped. If it did not, go back to Step 2; your diagnosis was wrong.

### Step 6. Full benchmark
    python run_eval.py vN+1

Compare against the parent's mean CER.

*Verify:*
- **Keep** the new version if the total CER improved by more than the noise floor (0.007).
- If it improved by less than that, run it two more times and compare three-run means. Keep it
  only if the mean still improved by at least half the noise floor (0.0035).
- Check every pattern. If any pattern got worse by more than 0.02, open those cases in Layer 2
  with "Compare with" set to the parent run, and explain the regression before moving on.
- If the total got worse, revert: the next iteration starts again from the best version.

### Step 7. Record
Write the result (pattern, change, CER before and after, kept or reverted) at the top of the
prompt file's notes, so the history travels with the prompt.

## When to stop and hand back to a human
- Two iterations in a row bring no gain beyond the noise floor.
- The remaining failures are of the **data** kind.
- A policy question comes up that the ground truth does not answer.
- A fix keeps trading one pattern against another.

Then summarize: best version and its CER, what was tried, what is left, and your recommendation.
The decision to continue, change the model, fix the data, or stop belongs to the human.
