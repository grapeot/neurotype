#!/usr/bin/env python3
"""Run the Neurotype benchmark for one or more corrector versions.

Examples:
    python run_eval.py v0                 # echo baseline, no API calls
    python run_eval.py v1                 # one full run of prompts/v1.md
    python run_eval.py v2 --runs 3        # three runs, to see the noise
    python run_eval.py v3 --limit 20      # quick smoke test on 20 items
    python run_eval.py --compare          # table of every recorded version

Each full run is saved to results/<version>/<run_id>.json and summarized in
results/index.json, which the dashboard reads.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from neurotype import llm
from neurotype.corrector import correct, list_versions, load_prompt
from neurotype.metric import cer, exact

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "data" / "dataset.json"
RESULTS = ROOT / "results"
INDEX = RESULTS / "index.json"


def load_items() -> list[dict]:
    return json.loads(DATASET.read_text())["items"]


def summarize(rows: list[dict]) -> dict:
    by_pattern: dict[str, list[dict]] = {}
    for r in rows:
        by_pattern.setdefault(r["pattern"], []).append(r)
    return {
        "cer": round(statistics.mean(r["cer"] for r in rows), 4),
        "exact": round(statistics.mean(r["exact"] for r in rows), 4),
        "n": len(rows),
        "parse_errors": sum(r["parse_error"] for r in rows),
        "patterns": {
            p: {
                "cer": round(statistics.mean(r["cer"] for r in rs), 4),
                "exact": round(statistics.mean(r["exact"] for r in rs), 4),
                "n": len(rs),
            }
            for p, rs in by_pattern.items()
        },
    }


def run_once(version: str, items: list[dict], concurrency: int, quiet: bool = False) -> dict:
    prompt = None if version == "v0" else load_prompt(version)
    t0 = time.time()

    def one(item: dict) -> dict:
        s = time.time()
        try:
            res = correct(version, item["messy_text"], prompt)
        except Exception as exc:  # keep the run alive; score the failure
            res = {"output": "", "rationale": f"(call failed: {exc})", "raw": "",
                   "parse_error": True, "usage": {}}
        return {
            "id": item["id"],
            "pattern": item["pattern"],
            "messy_text": item["messy_text"],
            "ground_truth": item["ground_truth"],
            "output": res["output"],
            "rationale": res["rationale"],
            "parse_error": res["parse_error"],
            "cer": round(cer(res["output"], item["ground_truth"]), 4),
            "exact": exact(res["output"], item["ground_truth"]),
            "latency_s": round(time.time() - s, 2),
            "tokens": res["usage"].get("total_tokens", 0),
        }

    rows: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(one, it) for it in items]
        for i, fut in enumerate(cf.as_completed(futures), 1):
            rows.append(fut.result())
            if not quiet and sys.stderr.isatty():
                print(f"\r  {version}: {i}/{len(items)}", end="", file=sys.stderr)
    if not quiet and sys.stderr.isatty():
        print(file=sys.stderr)
    rows.sort(key=lambda r: r["id"])
    elapsed = round(time.time() - t0, 1)
    return {
        "version": version,
        "title": prompt.title if prompt else "v0: echo baseline",
        "notes": prompt.notes if prompt else "Returns the typed text unchanged. Any real corrector must beat this.",
        "prompt_digest": prompt.digest if prompt else "",
        "prompt_source": prompt.source if prompt else "",
        "model": "none" if version == "v0" else llm.model_name(),
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_s": elapsed,
        "total_tokens": sum(r["tokens"] for r in rows),
        "summary": summarize(rows),
        "items": rows,
    }


def save(run: dict, tag: str = "") -> Path:
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + (f"-{tag}" if tag else "")
    run["run_id"] = run_id
    out = RESULTS / run["version"] / f"{run_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(run, indent=1, ensure_ascii=False) + "\n")
    rebuild_index()
    return out


def rebuild_index() -> dict:
    runs = []
    for path in sorted(RESULTS.glob("v*/*.json")):
        run = json.loads(path.read_text())
        runs.append({
            "version": run["version"],
            "run_id": run["run_id"],
            "title": run["title"],
            "model": run["model"],
            "started_at": run["started_at"],
            "elapsed_s": run["elapsed_s"],
            "total_tokens": run.get("total_tokens", 0),
            "summary": run["summary"],
            "path": str(path.relative_to(RESULTS)),
        })
    order = {v: i for i, v in enumerate(list_versions())}
    runs.sort(key=lambda r: (order.get(r["version"], 999), r["run_id"]))
    index = {"metric": "CER (character error rate, lower is better)", "runs": runs}
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(index, indent=1) + "\n")
    return index


def compare() -> None:
    index = rebuild_index()
    by_version: dict[str, list[dict]] = {}
    for r in index["runs"]:
        if r["summary"]["n"] == len(load_items()):
            by_version.setdefault(r["version"], []).append(r)
    patterns = sorted({p for rs in by_version.values() for r in rs for p in r["summary"]["patterns"]})
    head = f"{'version':8s} {'runs':>4s} {'CER':>7s} {'±sd':>6s} {'exact':>6s}  " + " ".join(f"{p[:10]:>10s}" for p in patterns)
    print(head)
    print("-" * len(head))
    for v, rs in by_version.items():
        cers = [r["summary"]["cer"] for r in rs]
        sd = statistics.stdev(cers) if len(cers) > 1 else 0.0
        ex = statistics.mean(r["summary"]["exact"] for r in rs)
        pats = " ".join(
            f"{statistics.mean(r['summary']['patterns'][p]['cer'] for r in rs if p in r['summary']['patterns']):10.3f}"
            for p in patterns
        )
        print(f"{v:8s} {len(rs):4d} {statistics.mean(cers):7.4f} {sd:6.4f} {ex:6.2f}  {pats}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("versions", nargs="*", help="versions to run, e.g. v0 v1 v2")
    ap.add_argument("--runs", type=int, default=1, help="repeat each version N times")
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--limit", type=int, help="only the first N items (smoke test, not saved)")
    ap.add_argument("--pattern", help="only items of one pattern (smoke test, not saved)")
    ap.add_argument("--tag", default="", help="suffix for the run id")
    ap.add_argument("--compare", action="store_true", help="print the version table")
    args = ap.parse_args()

    if args.compare or not args.versions:
        compare()
        return
    items = load_items()
    partial = bool(args.limit or args.pattern)
    if args.pattern:
        items = [it for it in items if it["pattern"] == args.pattern]
    if args.limit:
        items = items[: args.limit]
    for version in args.versions:
        for k in range(args.runs):
            run = run_once(version, items, args.concurrency)
            s = run["summary"]
            line = (f"{version} run {k + 1}/{args.runs}: CER {s['cer']:.4f} (lower is better) | "
                    f"exact {s['exact']:.0%} | {run['elapsed_s']}s | {run['total_tokens']} tokens")
            if partial:
                print(line + "  [smoke test, not saved]")
                for r in run["items"]:
                    if r["cer"] > 0:
                        print(f"  #{r['id']} {r['pattern']} CER {r['cer']:.3f}\n    want: {r['ground_truth']}\n    got:  {r['output']}")
            else:
                path = save(run, args.tag)
                print(line + f"  -> {path.relative_to(ROOT)}")
                print("   " + "  ".join(f"{p} {v['cer']:.3f}" for p, v in s["patterns"].items()))


if __name__ == "__main__":
    main()
