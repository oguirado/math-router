# Measured results (router v2.0.1)

Receipts: `test_eval/test_run_v2.0.1.json` (TEST, single frozen run), `out/run_DEV_v2.0.1.json` (DEV), `test_eval/cold_latency_TEST.json`. Reproduce TEST with `sh tools/reproduce_test.sh`; the `systems` section of the receipt must match byte for byte.

Index sha256 `2c1459766a263fdc...`, parameters sha256 `ad1c42c7...`. Parameters were fitted on DEV only (`out/tune_report.json`); TEST was evaluated once after the freeze.

## Benchmark

| Split | Queries | Answerable | Source of queries |
|---|---|---|---|
| DEV | 90 | 27 | 30 blind-authored, 60 themed brainstorm |
| TEST | 72 | 39 | 72 blind-authored |

Labels: two independent model graders over a pooled candidate set, a third model adjudicating binary disagreements. Final grades are in `adjudication` and `gold` of each row.

## TEST (answerable n = 39)

| System | R@1 | R@5 | MRR | nDCG@5 | bytes p50 | bytes max | share <= 2,000 B |
|---|---|---|---|---|---|---|---|
| v2.0.1 | 0.2220 | 0.5160 | 0.5958 | 0.4627 | 1,077 | 1,167 | 1.00 |
| v1 budgeted | 0.0904 | 0.1139 | 0.2564 | 0.1280 | 2,246 | 2,801 | 0.26 |
| v1 unbudgeted | 0.0904 | 0.2662 | 0.3516 | 0.2496 | 18,180 | 22,181 | 0.00 |
| B1 | 0.0523 | 0.1564 | 0.2340 | 0.1559 | - | - | - |

Abstention (positive = unanswerable; 33 unanswerable, 39 answerable): v2.0.1 precision 0.6286, recall 0.6667, F1 0.6471, answerable pass-through 0.6667.

## Limits

Recall at rank 1 is 0.22. Abstention is a lexical heuristic. DS has no answerable TEST query and SYS has one, so per-class numbers are anecdotal. Every judged pair comes from a pool of candidates retrieved by the evaluated systems; the unjudged top-5 count for v2 is 0.

One DEV pair remains unjudged (query W-R12, paper PM-101.1, `out/unjudged_pairs.jsonl`); it is disclosed as is and no judgement was invented for it.

## Note on the receipts

The receipts were regenerated from the files in this repository after the benchmark's `source` value `w11_brainstorm` was renamed `themed_brainstorm` (schema and data) and the DEV hash pinned in `out/params.json` was updated accordingly. The ranking metrics are identical to the original run; only hashes of the renamed inputs differ.

`out/protocol.json` is the reference mount description of the router protocol schema (`catalogue/router`); in this repository the same index and parameters are shipped as `out/index` and `out/params.json`.
