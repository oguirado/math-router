# Measured results (router v2.0.1)

Receipts: `test_eval/test_run_v2.0.1.json` (TEST: evaluated once after the parameter freeze, then regenerated once after a label rename, see "Receipt regeneration"), `out/run_DEV_v2.0.1.json` (DEV), `test_eval/cold_latency_TEST.json`, `test_eval/bootstrap_ci_TEST.json` (confidence intervals). Reproduce TEST with `sh tools/reproduce_test.sh`; the `systems` section of the receipt must match byte for byte. Reproduce the DEV tuning with `sh tools/reproduce_dev.sh`.

Index sha256 `2c1459766a263fdc954a10976198cfb6c441155fac78f0217e2dac3fc2c248a1`; parameters sha256 `ad1c42c79dad98fadd867cd9649f12f3096cb08be93cdc208f3872f10dbf06de` (the file `out/params.json`). Parameters were fitted on DEV only (`out/tune_report.json`); TEST was evaluated once after the freeze (no parameter was changed afterwards). `tools/claims_check.py` compares the numbers quoted in the README, AGENTS, CHANGELOG and docs with the receipts, so they cannot drift silently.

## Metric definitions

Positives are the papers graded 2 or 3 for a query (the "relevant set"); a query has 3.13 relevant papers on average over the 39 answerable TEST queries. All ranking metrics are averaged over the answerable queries of the split.

| Metric | Definition |
|---|---|
| R@k | number of relevant papers in the top k, divided by the size of the relevant set (recall, not a hit rate) |
| MRR | reciprocal rank of the first relevant paper in the returned list, 0 if none |
| nDCG@5 | DCG of the top 5 with gain 2^grade - 1 (grades 0 to 3) and discount log2(rank + 1), divided by the DCG of the ideal top 5 |
| hit@k | share of queries for which at least one relevant paper is in the top k (the intuitive "was it found" rate) |
| Abstention | positive class = unanswerable query; precision = flagged unanswerable / all flagged; recall = flagged unanswerable / all unanswerable; F1 their harmonic mean; answerable pass-through = share of answerable queries that were not flagged |
| Answer bytes | size of the whole JSON answer line, in bytes |

## Benchmark

| Split | Queries | Answerable | Source of queries |
|---|---|---|---|
| DEV | 90 | 27 | 30 blind-authored, 60 themed brainstorm |
| TEST | 72 | 39 | 72 blind-authored |

Labels: two independent model graders over a pooled candidate set, a third model adjudicating binary disagreements. Final grades are in `adjudication` and `gold` of each row.

### Label quality and provenance

- **Cohen's kappa 0.89 (TEST).** Computed by `tools/claims_check.py` from the `adjudication` fields `a1` and `a2` of `test_eval/bench_test_graded.jsonl`: the unit is the pooled (query, paper) pair (`kappa_unit: pooled_pair`), 3,596 pairs, each grader's grade reduced to binary relevance (grade 2 or 3 is relevant, as in the metrics). Raw agreement is 0.9936; the two graders disagree on 23 pairs, which the third model adjudicated (`resolved_by` contains `a3` for 15 of the 72 queries). Kappa is 0.8936. On the 0 to 3 grades themselves it is lower (0.70, unweighted), so 0.89 describes the relevant / not relevant decision only. DEV, same definition: 4,672 pairs, kappa 0.6978, 49 disagreements; two DEV queries carry a `single_seat` marker in `resolved_by`, which the repository does not document further.
- **Who wrote and graded.** The TEST queries are marked `authored_blind` (written without seeing router output); the DEV set mixes 30 `authored_blind` and 60 `themed_brainstorm` queries. The files record the label source and how each query was resolved, but not who authored the queries and not which models acted as grader 1, grader 2 or adjudicator: **not recorded in this repository**. The overlap between those models and the models that built the corpus (listed in the README) therefore cannot be established from the repository; a shared model family could bias the labels towards generated text.

## TEST (answerable n = 39)

| System | R@1 | R@5 | MRR | nDCG@5 | hit@1 | hit@5 | bytes p50 | bytes max | share <= 2,000 B |
|---|---|---|---|---|---|---|---|---|---|
| v2.0.1 | 0.2220 | 0.5160 | 0.5958 | 0.4627 | 0.4359 | 0.8462 | 1,077 | 1,167 | 1.00 |
| v1 row budget 2,000 B | 0.0904 | 0.1139 | 0.2564 | 0.1280 | 0.2308 | 0.2821 | 2,246 | 2,801 | 0.26 |
| v1 unbudgeted | 0.0904 | 0.2662 | 0.3516 | 0.2496 | 0.2308 | 0.4872 | 18,180 | 22,181 | 0.00 |
| B1 | 0.0523 | 0.1564 | 0.2340 | 0.1559 | 0.1538 | 0.3590 | - | - | - |

B1 is the v1 lexical-only baseline: BM25 over the title and purpose fields of the v1 index, returning only papers with a positive score (`b1_scores` in `v1_frozen/eval_route.py`). The v1 "row budget" caps the summed size of its result rows at 2,000; the rest of the v1 answer (query, parameters, abstention) is added on top, and at least one row is always kept. That is why its whole answer can exceed 2,000 B. v2 caps the whole answer.

## Abstention (TEST, 33 unanswerable and 39 answerable queries)

v2.0.1: precision 0.6286, recall 0.6667, F1 0.6471, answerable pass-through 0.6667. In counts: 35 queries flagged, of which 22 are unanswerable (true positives) and 13 are answerable; 11 unanswerable queries are not flagged. So **13 of the 39 answerable queries (33%) carry an abstain flag**. The flag means "little lexical support", not "the corpus has no answer": `AGENTS.md` tells agents to inspect the top rows before concluding that nothing matches.

### Abstention of the baselines

| System | Flag raised on | Flagged (of 72) | Precision | Recall | F1 |
|---|---|---|---|---|---|
| v2.0.1 | no query term, low term match or score below the fitted threshold (`abstain.reason`) | 35 | 0.6286 | 0.6667 | 0.6471 |
| B1 | no paper has a positive score (no query term occurs in any title or purpose) | 7 | 1.0000 | 0.2121 | 0.3500 |
| v1 (both rows) | no query term or expansion term occurs in the index | 0 | - | 0.0000 | 0.0000 |

The B1 figure quoted in the README (abstention F1 0.350) is the `abstain` block of the `b1` system in `test_eval/test_run_v2.0.1.json`: 7 queries flagged, all 7 unanswerable (precision 1.0), 7 of 33 unanswerable queries found (recall 0.2121). v1 has no abstention figure ("-" in the README) because its flag never fired on the TEST split: precision is undefined with no flagged query and recall is 0; B1 is not v1 with its flag, it is a separate ranker with its own empty-result rule.

## Uncertainty (bootstrap, TEST answerable n = 39)

With 39 answerable queries the point estimates above are noisy. `tools/bootstrap_ci.py` resamples the 39 queries with replacement (10,000 resamples, fixed seed 20261019, percentile interval, 95%) and writes `test_eval/bootstrap_ci_TEST.json`; CI runs `python3 -I tools/bootstrap_ci.py --check`, which recomputes the intervals and requires this table to match. The same resamples are used for every system, so the paired differences are paired. Values are `point [low, high]`.

| System | R@1 | R@5 | MRR | hit@1 | hit@5 |
|---|---|---|---|---|---|
| v2.0.1 | 0.222 [0.122, 0.335] | 0.516 [0.410, 0.625] | 0.596 [0.477, 0.713] | 0.436 [0.282, 0.590] | 0.846 [0.718, 0.949] |
| v1 row budget 2,000 B | 0.090 [0.034, 0.161] | 0.114 [0.052, 0.187] | 0.256 [0.128, 0.397] | 0.231 [0.103, 0.359] | 0.282 [0.154, 0.436] |
| v1 unbudgeted | 0.090 [0.034, 0.161] | 0.266 [0.168, 0.372] | 0.352 [0.236, 0.476] | 0.231 [0.103, 0.359] | 0.487 [0.333, 0.641] |
| B1 | 0.052 [0.011, 0.115] | 0.156 [0.082, 0.242] | 0.234 [0.130, 0.353] | 0.154 [0.051, 0.282] | 0.359 [0.205, 0.513] |

| Paired difference | R@1 | R@5 | MRR | hit@1 | hit@5 |
|---|---|---|---|---|---|
| v2.0.1 minus v1 row budget 2,000 B | +0.132 [+0.021, +0.251] | +0.402 [+0.282, +0.525] | +0.339 [+0.174, +0.501] | +0.205 [+0.026, +0.385] | +0.564 [+0.385, +0.718] |
| v2.0.1 minus v1 unbudgeted | +0.132 [+0.021, +0.251] | +0.250 [+0.113, +0.389] | +0.244 [+0.099, +0.385] | +0.205 [+0.026, +0.385] | +0.359 [+0.205, +0.513] |

The intervals are wide: v2.0.1 R@1 could plausibly be anywhere between 0.12 and 0.34. The paired differences against both v1 rows exclude 0 for every metric, so v2.0.1 is better than v1 on this benchmark beyond resampling noise of the 39 queries; that says nothing about queries unlike these, and it does not cover the labelling uncertainty described above.

## Limits

R@1 is 0.22. Abstention is a lexical heuristic. DS has no answerable TEST query and SYS has one, so per-class numbers are anecdotal. Every judged pair comes from a pool of candidates retrieved by the evaluated systems; the unjudged top-5 count for v2 is 0.

One DEV pair remains unjudged (query W-R12, paper PM-101.1, `out/unjudged_pairs.jsonl`); it is disclosed as is and no judgement was invented for it.

## Corpus status fields

Every paper carries status fields that read like unfinished work. They are the corpus's own fields, kept byte-identical because the index, the parameters and the TEST receipt hash the papers; changing them would change every published number. Counts computed from `papers/` (719 files):

| Field | Value in all 719 papers | Meaning |
|---|---|---|
| `publication_status` (also "Publication status" in the header and "Verification status" in section 10) | `DRAFT` | the paper's verification status is still the initial one; its provenance record lists no verified section ("Verified sections: 0") |
| `generation_status` of the paper node | `ASSEMBLED` | the node was assembled from the converted paper and the generated sections; individual blocks inside a paper may carry `COMPLETE` |
| `Action rule: ABSENT` in section 0 | 719 papers | the generated action rule is not present (the placeholder says "generated action rule pending"); it is a navigation aid and the mathematical text does not depend on it |
| other `ABSENT` markers | 5,578 occurrences in total across the papers, mostly in section 5 (262 papers) and section 6 (244 papers) | an engineering or domain contract that the paper does not support is stated as absent instead of being invented |
| `verification: PENDING` on relations (section 9) | 1,308 of 1,308 | none of the typed relations between papers has been independently verified |

Read `DRAFT` as "not independently verified", and use the generated sections as navigation aids, not as authority: section 7 and the paper's own statements are the authority.

## Skipped test

Before `out/census.json` was shipped the unit test suite had one skipped test, `test_real_census_receipt` in `tests/test_T1_blocks.py`. It checks `out/census.json` against the corpus census counts and skips when that file is absent; the file is generated by `tools/census.py --root . --out out/census.json` and is shipped, so the test runs.

## Receipt regeneration

The TEST and DEV receipts were regenerated once from the files in this repository, after the source label of the 60 brainstormed DEV rows was renamed to `themed_brainstorm` (in `eval/dev.jsonl` and in `docs/schemas/ctx.bench.v1.schema.json`; nothing else in the DEV file changed). The exact list of changed fields is in `docs/receipt_regeneration.json`:

| File | Fields that changed (hash values only) |
|---|---|
| `test_eval/test_run_v2.0.1.json` | `freeze_sha256`, `params_sha256` |
| `out/params.json` | `dev_sha256` (the pinned DEV file hash) |
| `out/run_DEV_v2.0.1.json` | `bench_sha256`, `freeze_sha256`, `params_sha256` |

Everything else is identical to the original run: the whole `systems` section of the TEST receipt (every metric, ranking and abstention figure), its `bench_sha256` and `index_sha256`, `out/tune_report.json`, and the tuned parameter values. `freeze_sha256` identifies a freeze record of tool, parameter and DEV-file hashes that is not shipped; tools were edited after it was written (documentation and CI tools, command-line defaults), so that field is informational. The original receipts are not shipped; `sh tools/reproduce_test.sh` and `sh tools/reproduce_dev.sh` re-derive the metrics and the tuning from the shipped files.

## Latency

`test_eval/cold_latency_TEST.json` holds 30 cold-start timings per router (v2 p50 58.0 ms, p99 67.2 ms; v1 p50 87.2 ms, p99 103.7 ms; ratio 0.665). The measuring environment (CPU, operating system, Python version, file-cache state, what exactly "cold" excluded) was not recorded in the receipt or elsewhere in the repository, so treat the figures as indicative and relative (v2 against v1 on the same machine), not as a performance guarantee.

`out/protocol.json` describes the router mount of this repository: the index is `out/index` and the parameters are `out/params.json`.
