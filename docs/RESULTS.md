# Measured results (router v2.0.1)

Receipts: `test_eval/test_run_v2.0.1.json` (TEST, single frozen run), `out/run_DEV_v2.0.1.json` (DEV), `test_eval/cold_latency_TEST.json`. Reproduce TEST with `sh tools/reproduce_test.sh`; the `systems` section of the receipt must match byte for byte. Reproduce the DEV tuning with `sh tools/reproduce_dev.sh`.

Index sha256 `2c1459766a263fdc954a10976198cfb6c441155fac78f0217e2dac3fc2c248a1`; parameters sha256 `ad1c42c79dad98fadd867cd9649f12f3096cb08be93cdc208f3872f10dbf06de` (the file `out/params.json`). Parameters were fitted on DEV only (`out/tune_report.json`); TEST was evaluated once after the freeze. `tools/claims_check.py` compares the numbers quoted in the README, AGENTS, CHANGELOG and docs with the receipts, so they cannot drift silently.

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

## TEST (answerable n = 39)

| System | R@1 | R@5 | MRR | nDCG@5 | hit@1 | hit@5 | bytes p50 | bytes max | share <= 2,000 B |
|---|---|---|---|---|---|---|---|---|---|
| v2.0.1 | 0.2220 | 0.5160 | 0.5958 | 0.4627 | 0.4359 | 0.8462 | 1,077 | 1,167 | 1.00 |
| v1 row budget 2,000 B | 0.0904 | 0.1139 | 0.2564 | 0.1280 | 0.2308 | 0.2821 | 2,246 | 2,801 | 0.26 |
| v1 unbudgeted | 0.0904 | 0.2662 | 0.3516 | 0.2496 | 0.2308 | 0.4872 | 18,180 | 22,181 | 0.00 |
| B1 | 0.0523 | 0.1564 | 0.2340 | 0.1559 | 0.1538 | 0.3590 | - | - | - |

B1 is the v1 lexical-only baseline. The v1 "row budget" caps the summed size of its result rows at 2,000; the rest of the v1 answer (query, parameters, abstention) is added on top, and at least one row is always kept. That is why its whole answer can exceed 2,000 B. v2 caps the whole answer.

## Abstention (TEST, 33 unanswerable and 39 answerable queries)

v2.0.1: precision 0.6286, recall 0.6667, F1 0.6471, answerable pass-through 0.6667. In counts: 35 queries flagged, of which 22 are unanswerable (true positives) and 13 are answerable; 11 unanswerable queries are not flagged. So **13 of the 39 answerable queries (33%) carry an abstain flag**. The flag means "little lexical support", not "the corpus has no answer": `AGENTS.md` tells agents to inspect the top rows before concluding that nothing matches.

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

## Note on the receipts

The receipts were regenerated from the files in this repository after a source label in the benchmark was renamed (`themed_brainstorm`, in schema and data) and the DEV hash pinned in `out/params.json` was updated accordingly. The ranking metrics are identical to the original run; only hashes of the renamed inputs differ.

`out/protocol.json` describes the router mount of this repository: the index is `out/index` and the parameters are `out/params.json`.
