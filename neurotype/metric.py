"""Scoring. Primary metric: character error rate (CER), lower is better.

CER = Levenshtein distance(output, ground_truth) / len(ground_truth),
capped at 1.0 so that a single runaway answer cannot dominate the mean.
Secondary metric: exact match rate, higher is better.
"""

from __future__ import annotations


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(output: str, truth: str) -> float:
    output, truth = output.strip(), truth.strip()
    return min(1.0, levenshtein(output, truth) / max(1, len(truth)))


def exact(output: str, truth: str) -> bool:
    return output.strip() == truth.strip()
