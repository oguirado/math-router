#!/usr/bin/env python3
"""Deterministic bootstrap confidence intervals for the shipped TEST receipt (standard library only).

Usage:
  python3 -I tools/bootstrap_ci.py                 print the receipt JSON
  python3 -I tools/bootstrap_ci.py --out FILE      write it
  python3 -I tools/bootstrap_ci.py --check         recompute and compare with test_eval/bootstrap_ci_TEST.json and
                                                   with the table in docs/RESULTS.md (exit 1 on any difference)

Method: the 39 answerable TEST queries are resampled with replacement (percentile bootstrap, 10,000 resamples, level 95%).
The per-query values (R@1, R@5, MRR, hit@1, hit@5) are exact rationals scaled to integers, the resampling uses
random.Random(SEED).random() only, and the interval ends are order statistics of integer sums, so the output does not
depend on the platform or on the Python version. All systems and the paired differences use the same resamples.
Input: test_eval/test_run_v2.0.1.json (ranked ids per query) and test_eval/bench_test_graded.jsonl (graded labels).
"""
import argparse
import hashlib
import json
import math
import os
import random
import sys
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECEIPT = "test_eval/test_run_v2.0.1.json"
BENCH = "test_eval/bench_test_graded.jsonl"
SHIPPED = "test_eval/bootstrap_ci_TEST.json"
RESULTS = "docs/RESULTS.md"
SEED = 20261019
B = 10000
LEVEL = 95
SYSTEMS = ("v2", "v1", "v1-unbudgeted", "b1")
LABELS = {"v2": "v2.0.1", "v1": "v1 row budget 2,000 B", "v1-unbudgeted": "v1 unbudgeted", "b1": "B1"}
METRICS = ("recall_at_1", "recall_at_5", "mrr", "hit_at_1", "hit_at_5")
COLS = ("R@1", "R@5", "MRR", "hit@1", "hit@5")
PAIRED = (("v2", "v1"), ("v2", "v1-unbudgeted"))


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def per_query_values(ids, gold):
    """Exact per-query values as Fractions; relevant = grade >= 2."""
    rel = {i for i, g in gold.items() if g >= 2}
    r1 = Fraction(len(rel & set(ids[:1])), len(rel))
    r5 = Fraction(len(rel & set(ids[:5])), len(rel))
    first = next((j + 1 for j, i in enumerate(ids) if i in rel), 0)
    mrr = Fraction(1, first) if first else Fraction(0)
    return {"recall_at_1": r1, "recall_at_5": r5, "mrr": mrr,
            "hit_at_1": Fraction(int(bool(rel & set(ids[:1])))), "hit_at_5": Fraction(int(bool(rel & set(ids[:5]))))}


def load(root):
    rec = json.load(open(os.path.join(root, RECEIPT), encoding="utf-8"))
    bench = {}
    with open(os.path.join(root, BENCH), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                bench[r["qid"]] = r
    return rec, bench


def scaled(vals):
    """Scale a list of Fractions to integers with a common denominator; return (ints, denominator)."""
    den = 1
    for v in vals:
        den = den * v.denominator // math.gcd(den, v.denominator)
    return [int(v * den) for v in vals], den


def compute(root):
    rec, bench = load(root)
    qids = sorted(q for q, r in bench.items() if r["answerable"])
    data = {}
    for s in SYSTEMS:
        by_q = {p["qid"]: p for p in rec["systems"][s]["per_query"]}
        rows = [per_query_values(by_q[q]["ids"], {g["id"]: g["grade"] for g in bench[q]["gold"]}) for q in qids]
        data[s] = {m: scaled([r[m] for r in rows]) for m in METRICS}
    n = len(qids)
    rnd = random.Random(SEED)
    draws = [[int(rnd.random() * n) for _ in range(n)] for _ in range(B)]
    lo_i, hi_i = int(B * (100 - LEVEL) / 200), int(math.ceil(B * (100 + LEVEL) / 200)) - 1

    def interval(vals, den):
        sums = sorted(sum(vals[i] for i in d) for d in draws)
        return sums[lo_i] / (n * den), sums[hi_i] / (n * den)

    out = {"schema": "math-router.bootstrap-ci.v1", "method": "percentile bootstrap over answerable queries",
           "seed": SEED, "resamples": B, "level": LEVEL / 100, "n_queries": n, "receipt": RECEIPT,
           "receipt_sha256": sha256_file(os.path.join(root, RECEIPT)), "bench": BENCH,
           "bench_sha256": sha256_file(os.path.join(root, BENCH)), "systems": {}, "paired": {}}
    for s in SYSTEMS:
        out["systems"][s] = {}
        for m in METRICS:
            vals, den = data[s][m]
            lo, hi = interval(vals, den)
            out["systems"][s][m] = {"point": round(sum(vals) / (n * den), 4), "lo": round(lo, 4), "hi": round(hi, 4)}
            want = rec["systems"][s]["metrics"]["quality"].get(m)
            if want is not None and abs(out["systems"][s][m]["point"] - want) > 1e-9:
                raise SystemExit("point estimate %s %s differs from the receipt" % (s, m))
    for a, b in PAIRED:
        key = "%s_minus_%s" % (a, b)
        out["paired"][key] = {}
        for m in METRICS:
            (va, da), (vb, db) = data[a][m], data[b][m]
            den = da * db // math.gcd(da, db)
            diff = [x * (den // da) - y * (den // db) for x, y in zip(va, vb)]
            lo, hi = interval(diff, den)
            out["paired"][key][m] = {"point": round(sum(diff) / (n * den), 4), "lo": round(lo, 4), "hi": round(hi, 4)}
    return out


def render(out):
    """Markdown rows that docs/RESULTS.md must contain."""
    rows = ["| System | " + " | ".join(COLS) + " |", "|---|" + "---|" * len(COLS)]
    for s in SYSTEMS:
        cells = []
        for m in METRICS:
            c = out["systems"][s][m]
            cells.append("%.3f [%.3f, %.3f]" % (c["point"], c["lo"], c["hi"]))
        rows.append("| %s | %s |" % (LABELS[s], " | ".join(cells)))
    rows += ["", "| Paired difference | " + " | ".join(COLS) + " |", "|---|" + "---|" * len(COLS)]
    for a, b in PAIRED:
        cells = []
        for m in METRICS:
            c = out["paired"]["%s_minus_%s" % (a, b)][m]
            cells.append("%+.3f [%+.3f, %+.3f]" % (c["point"], c["lo"], c["hi"]))
        rows.append("| %s minus %s | %s |" % (LABELS[a], LABELS[b], " | ".join(cells)))
    return rows


def dumps(o):
    return json.dumps(o, indent=1, sort_keys=True) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    out = compute(a.root)
    if a.check:
        errs = []
        try:
            shipped = open(os.path.join(a.root, SHIPPED), encoding="utf-8").read()
        except OSError:
            shipped = None
        if shipped != dumps(out):
            errs.append("%s differs from a fresh computation" % SHIPPED)
        try:
            text = open(os.path.join(a.root, RESULTS), encoding="utf-8").read()
        except OSError:
            text = ""
        lines = {l.strip() for l in text.splitlines()}
        for row in render(out):
            if row and row not in lines:
                errs.append("%s lacks table row: %s" % (RESULTS, row))
        for e in errs:
            print(e)
        print("bootstrap_ci: %s" % ("MISMATCH" if errs else "confidence intervals reproduced"))
        return 1 if errs else 0
    text = dumps(out)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
