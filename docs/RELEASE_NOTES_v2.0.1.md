# math-router v2.0.1

A structured, routable edition of the 719 mathematical preprints in openai/math (Apache-2.0), plus an offline router that returns the few statements most likely to answer a question in at most 2,000 bytes. Not affiliated with or endorsed by OpenAI.

## Try it

```bash
git clone https://github.com/oguirado/math-router.git && cd math-router
python3 tools/route_v2.py --q "irrationality of Catalan's constant"
sh tools/reproduce_test.sh
```

## Measured (TEST split, 72 queries written blind to the router, evaluated once after the parameter freeze; the receipt was regenerated once after a label rename, metrics unchanged)

| System | R@1 | R@5 | MRR | nDCG@5 | Answer bytes p50 / max |
|---|---|---|---|---|---|
| math-router v2.0.1 | 0.222 | 0.516 | 0.596 | 0.463 | 1,077 / 1,167 |
| v1 (row budget 2,000 B) | 0.090 | 0.114 | 0.256 | 0.128 | 2,246 / 2,801 |
| v1 (unbudgeted) | 0.090 | 0.266 | 0.352 | 0.250 | 18,180 / 22,181 |

Abstention on 33 unanswerable and 39 answerable queries: precision 0.629, recall 0.667, F1 0.647. All 14 router gates pass; 100 unit tests (none skipped). Receipts: `test_eval/test_run_v2.0.1.json`, `out/gates_v2.0.1.json`.

## In this release
CI workflow (Python 3.10 to 3.13), documentation claims check, publication lint, DEV tuning reproduction, community files, release notes and changelog. The empty catalogue/graph.jsonl is removed. Details: `CHANGELOG.md`.

## Limits
R@1 is 0.22; abstention precision is 0.63 and 13 of the 39 answerable queries are flagged; per-class figures are anecdotal. One DEV pair (W-R12, PM-101.1) is unjudged and disclosed, not guessed. Labels come from model graders, not human experts. Models used to build the corpus: see the README (model versions as of 2026-10).
