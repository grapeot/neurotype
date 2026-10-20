#!/usr/bin/env python3
"""Let the AI improve the corrector by itself, following SOP.md.

    python auto_improve.py                  # 2 iterations from the best version so far
    python auto_improve.py --iterations 3
    python auto_improve.py --from v2        # start from a specific version

Each iteration does what SOP.md says a person would do:
  1. read the latest full run of the current best version (scores + failing cases + rationales)
  2. ask a coach model to diagnose ONE failure pattern and write the next prompt version
  3. smoke-test the new prompt on the targeted cases, then run the full benchmark
  4. keep the new version only if it beats the best mean by more than the noise floor

It never changes the dataset or the metric, and it stops after N iterations.
Deciding whether to continue is left to a human. A log of every decision is
written to results/auto/<timestamp>.md.

This script is the scripted twin of IMPROVE.md, which gives the same
instructions to a coding agent (Codex, Claude Code, Cursor) in a live demo.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from datetime import datetime
from pathlib import Path

from neurotype import llm
from neurotype.corrector import list_versions, load_prompt
from run_eval import RESULTS, load_items, run_once, save

ROOT = Path(__file__).resolve().parent
COACH_MODEL_DEFAULT = "gpt-5"
NOISE_FLOOR_DEFAULT = 0.007  # max-min range of repeated runs at checkpoint-c; see SOP.md


def full_runs(version: str) -> list[dict]:
    n = len(load_items())
    runs = [json.loads(p.read_text()) for p in sorted((RESULTS / version).glob("*.json"))]
    return [r for r in runs if r["summary"]["n"] == n]


def mean_cer(version: str) -> float | None:
    runs = full_runs(version)
    return statistics.mean(r["summary"]["cer"] for r in runs) if runs else None


def best_version() -> str:
    scored = [(mean_cer(v), v) for v in list_versions() if v != "v0" and mean_cer(v) is not None]
    return min(scored)[1]


def next_version_name() -> str:
    nums = [int(m.group(1)) for v in list_versions() if (m := re.fullmatch(r"v(\d+)", v))]
    return f"v{max(nums) + 1}"


def build_brief(version: str, history: list[str]) -> str:
    run = full_runs(version)[-1]
    prompt_src = (ROOT / "prompts" / f"{version}.md").read_text()
    failures = sorted((it for it in run["items"] if it["cer"] > 0), key=lambda it: -it["cer"])[:30]
    cases = "\n\n".join(
        f"#{it['id']} [{it['pattern']}] CER {it['cer']:.3f}\n"
        f"typed:     {it['messy_text']}\n"
        f"expected:  {it['ground_truth']}\n"
        f"output:    {it['output']}\n"
        f"rationale: {it['rationale']}"
        for it in failures
    )
    patterns = "\n".join(
        f"- {p}: CER {s['cer']:.3f} over {s['n']} items" for p, s in run["summary"]["patterns"].items()
    )
    data_files = "\n".join(f"- {p.relative_to(ROOT)}" for p in sorted((ROOT / "data").glob("*")) if p.name != "dataset.json")
    sop = (ROOT / "SOP.md").read_text()
    hist = "\n".join(history) if history else "(none yet)"
    return f"""You are improving the prompt of a typo-correction system called Neurotype.
Follow this SOP exactly. It was written by the team after a successful coaching session.

=== SOP.md ===
{sop}
=== end SOP.md ===

Current best version: {version}, mean CER {mean_cer(version):.4f} (lower is better).
Per-pattern CER of its latest run:
{patterns}

Files in data/ you may inline into the prompt with {{{{file:path}}}} (do not invent new files):
{data_files}

Earlier iterations in this session:
{hist}

=== prompts/{version}.md ===
{prompt_src}
=== end ===

Worst failing cases of {version} (expected = ground truth, the definition of correct):
{cases}

Do ONE iteration of the SOP: pick one failure pattern, diagnose it, and write the next prompt version.
Reply with a JSON object only:
{{"pattern": "<the failure pattern you target>",
  "diagnosis": "<what goes wrong and why, citing case ids>",
  "kind": "<policy | context | ability | data>",
  "hypothesis": "<the change and the effect you expect on CER>",
  "smoke_ids": [<5 to 12 case ids that should improve>],
  "prompt_file": "<the complete new prompt file in the same format: '# vN: title', notes, '## System', '## User' with {{{{text}}}}>"}}"""


CALENDAR = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "january", "february", "march", "april", "may", "june", "july", "august",
            "september", "october", "november", "december"}


def leaked_cases(prompt_src: str, items: list[dict]) -> list[int]:
    """Ids of benchmark cases whose answers were copied into the prompt.

    Two kinds of leak: text copied from a case (five words of an expected output, three
    words or one distinctive garbled token of a typed input), or a proper name that
    appears only in the expected outputs (nowhere in the typed text or in data/), which
    the corrector could only know by reading the answer key.
    """
    if "## System" in prompt_src:  # the notes above it are for humans and never reach the model
        prompt_src = prompt_src.split("## System", 1)[1]
    known = " ".join(p.read_text() for p in (ROOT / "data").glob("*.md")).lower()
    typed_words = set(re.findall(r"[a-z]+", " ".join(it["messy_text"] for it in items).lower()))

    truth_words = set(" ".join(it["ground_truth"] for it in items).lower().split())

    def chunks(text: str, n: int = 5) -> set[str]:
        words = text.split()
        return {" ".join(words[i : i + n]) for i in range(max(0, len(words) - n + 1))}

    def garble(text: str) -> set[str]:  # distinctive typed tokens such as "yjitdfsu"
        return {w for w in text.split() if len(w) >= 6 and w.lower() not in truth_words}

    def answer_only_names(item: dict) -> set[str]:
        words = re.findall(r"[A-Za-z]+", item["ground_truth"])
        first = 0 if item["pattern"].endswith("names") else 1  # skip sentence-initial capitals
        return {w for i, w in enumerate(words) if i >= first and w[0].isupper() and len(w) > 3
                and w.lower() not in typed_words and w.lower() not in known
                and w.lower() not in CALENDAR}

    leaked = []
    for it in items:
        copied = any(c in prompt_src for c in
                     chunks(it["messy_text"], 3) | garble(it["messy_text"]) | chunks(it["ground_truth"]))
        names = any(re.search(rf"\b{n}\b", prompt_src) for n in answer_only_names(it))
        if copied or names:
            leaked.append(it["id"])
    return leaked


def ask_coach(brief: str, model: str) -> dict:
    raw, _ = llm.chat([{"role": "user", "content": brief}], model=model, max_tokens=12000,
                      temperature=1.0, reasoning_effort="low")
    start, end = raw.find("{"), raw.rfind("}")
    return json.loads(raw[start : end + 1])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iterations", type=int, default=2)
    ap.add_argument("--from", dest="start", help="version to start from (default: best so far)")
    ap.add_argument("--coach", default=COACH_MODEL_DEFAULT, help="model that diagnoses and rewrites")
    ap.add_argument("--noise", type=float, default=NOISE_FLOOR_DEFAULT,
                    help="minimum CER gain that counts as real (default %(default)s)")
    args = ap.parse_args()

    items = load_items()
    current = args.start or best_version()
    if mean_cer(current) is None:
        print(f"{current} has no full run yet; running it once first.")
        save(run_once(current, items, 32, quiet=True))
    log_lines = [f"# Auto-improve session {datetime.now():%Y-%m-%d %H:%M}",
                 f"Start: {current} (mean CER {mean_cer(current):.4f}), coach {args.coach}, "
                 f"corrector {llm.model_name()}, noise floor {args.noise}", ""]
    history: list[str] = []
    t_session = time.time()

    for k in range(1, args.iterations + 1):
        t0 = time.time()
        missing = 3 - len(full_runs(current))
        if missing > 0:  # SOP step 1: compare against a three-run mean, not a single lucky run
            print(f"\n{current} has {3 - missing} full run(s); running {missing} more to get a stable baseline")
            for _ in range(missing):
                save(run_once(current, items, 32, quiet=True), "auto")
        base = mean_cer(current)
        new = next_version_name()
        print(f"\n=== Iteration {k}: {current} (CER {base:.4f}) -> {new}")
        print("  asking the coach to diagnose and rewrite...")
        try:
            plan = ask_coach(build_brief(current, history), args.coach)
        except Exception as exc:
            print(f"  coach failed: {exc}")
            log_lines.append(f"## Iteration {k}: coach failed ({exc})")
            continue
        print(f"  pattern: {plan.get('pattern')} ({plan.get('kind')})")
        print(f"  diagnosis: {plan.get('diagnosis')}")
        print(f"  hypothesis: {plan.get('hypothesis')}")
        leaks = leaked_cases(plan["prompt_file"], items)
        if leaks:  # SOP step 4: examples must not come from the benchmark
            print(f"  the new prompt copies benchmark cases {leaks}; asking the coach to rewrite it")
            plan = ask_coach(build_brief(current, history) +
                             f"\n\nYour previous attempt copied benchmark cases {leaks} into the prompt. "
                             "That makes the score meaningless. Use only new examples you invent.", args.coach)
            leaks = leaked_cases(plan["prompt_file"], items)
            if leaks:
                print(f"  still copies cases {leaks}; skipping this iteration")
                log_lines.append(f"## Iteration {k}: rejected, prompt copied benchmark cases {leaks}")
                history.append(f"- An attempt on {plan.get('pattern')} was rejected for copying benchmark cases.")
                continue
        src = plan["prompt_file"].strip() + "\n"
        src = re.sub(r"^#\s*v\d+", f"# {new}", src, count=1)
        (ROOT / "prompts" / f"{new}.md").write_text(src)
        load_prompt(new)  # fail fast on a malformed file

        ids = set(plan.get("smoke_ids") or [])
        smoke_items = [it for it in items if it["id"] in ids] or items[:10]
        smoke = run_once(new, smoke_items, 32, quiet=True)
        before = {it["id"]: it["cer"] for it in full_runs(current)[-1]["items"]}
        s_before = statistics.mean(before[it["id"]] for it in smoke_items)
        print(f"  smoke test on {len(smoke_items)} cases: CER {s_before:.3f} -> {smoke['summary']['cer']:.3f}")

        full = run_once(new, items, 32, quiet=True)
        save(full, "auto")
        after = full["summary"]["cer"]
        gain = base - after
        reruns = ""
        if 0 < gain <= args.noise:
            print(f"  gain {gain:.4f} is within noise; running {new} two more times (SOP step 6)")
            for _ in range(2):
                save(run_once(new, items, 32, quiet=True), "auto")
            after = mean_cer(new)
            gain = base - after
            reruns = " (three-run mean)"
            keep = gain >= args.noise / 2
        else:
            keep = gain > args.noise
        regressions = [p for p, s in full["summary"]["patterns"].items()
                       if s["cer"] > full_runs(current)[-1]["summary"]["patterns"][p]["cer"] + 0.02]
        if keep:
            verdict = f"KEEP: {new} improves CER by {gain:.4f}{reruns}"
            current = new
        elif gain > -args.noise:
            verdict = f"NO CLEAR GAIN: change {gain:+.4f}{reruns} is within noise ({args.noise}); keep {current}"
        else:
            verdict = f"REGRESSION: CER worse by {-gain:.4f}; keep {current}"
        if regressions:
            verdict += f" (patterns that got worse: {', '.join(regressions)})"
        dt = time.time() - t0
        print(f"  full run: CER {base:.4f} -> {after:.4f}  [{dt:.0f}s]\n  {verdict}")
        history.append(f"- {new} targeted {plan.get('pattern')}: {plan.get('hypothesis')} Result: CER "
                       f"{base:.4f} -> {after:.4f}. {verdict}")
        log_lines += [f"## Iteration {k}: {new}",
                      f"- Pattern: {plan.get('pattern')} ({plan.get('kind')})",
                      f"- Diagnosis: {plan.get('diagnosis')}",
                      f"- Hypothesis: {plan.get('hypothesis')}",
                      f"- Smoke test ({len(smoke_items)} cases): {s_before:.3f} -> {smoke['summary']['cer']:.3f}",
                      f"- Full run: {base:.4f} -> {after:.4f} ({full['run_id']})",
                      f"- Verdict: {verdict}",
                      f"- Time: {dt:.0f}s", ""]

    total = time.time() - t_session
    log_lines += [f"Session time: {total:.0f}s. Best version now: {current} "
                  f"(mean CER {mean_cer(current):.4f}).",
                  "", "Next decision belongs to a human: continue, change the model, fix the data, or stop."]
    out = RESULTS / "auto" / f"{datetime.now():%Y%m%d-%H%M%S}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(log_lines) + "\n")
    print(f"\nDone in {total:.0f}s. Best: {current}. Log: {out.relative_to(ROOT)}")
    print("Your call: continue, change the model, fix the data, or stop.")


if __name__ == "__main__":
    main()
