"""Paired bootstrap interval for two prompt result files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random


def compare(a: list[dict], b: list[dict], seed: int = 0, iterations: int = 2000) -> dict:
    left, right = {x["id"]: bool(x["passed"]) for x in a}, {x["id"]: bool(x["passed"]) for x in b}
    if not left or left.keys() != right.keys() or len(left) != len(a) or len(right) != len(b):
        raise ValueError("Results need the same unique case IDs")
    deltas = [int(right[key]) - int(left[key]) for key in sorted(left)]
    rng = random.Random(seed)
    samples = sorted(sum(rng.choice(deltas) for _ in deltas)/len(deltas) for _ in range(iterations))
    return {"cases": len(deltas), "candidate_wins": deltas.count(1), "baseline_wins": deltas.count(-1),
            "pass_rate_difference": sum(deltas)/len(deltas), "bootstrap_95_percent": [samples[int(.025*iterations)], samples[min(iterations-1,int(.975*iterations))]]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(compare(json.loads(args.baseline.read_text()), json.loads(args.candidate.read_text()), args.seed), indent=2))

