# math-router

[![ci](https://github.com/oguirado/math-router/actions/workflows/ci.yml/badge.svg)](https://github.com/oguirado/math-router/actions/workflows/ci.yml) [![license: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

A structured, routable edition of the 719 mathematical preprints in [OpenAI's math repository](https://github.com/openai/math) (Apache-2.0), plus a small offline router that returns the few statements most likely to answer a question, in at most 2,000 bytes.

**Not affiliated with or endorsed by OpenAI.** The mathematical content comes from the upstream repository, which describes the manuscripts as produced by an internal OpenAI model and at different stages of verification; see `NOTICE` for attribution and the changes made.

## Quick start

```bash
git clone --depth 1 https://github.com/oguirado/math-router.git && cd math-router
python3 tools/route_v2.py --q "irrationality of Catalan's constant"
python3 tools/build_index_v2.py --root . --out out/index --check
```

Python >= 3.10, standard library only, no network. Without `--index` and `--params` the router uses `out/index` and `out/params.json` of this repository. The answer is one JSON line: ranked `[paper_id, anchor, score]` rows and an abstention flag. Add `--paths` to get a `files` map from each returned id to `papers/<file>#<anchor>` (it is not part of the 2,000-byte budget); otherwise map an id to its file with `catalogue/routes.tsv`, then open the paper at the anchor (`<a id="..."></a>`). Agents: read `llms.txt` and `AGENTS.md`.

Example answer, cut after three of the twenty rows (the real line is 1,077 bytes; `<...>` marks a value left out here):

```json
{"abstain":{"cov":1000000,"flag":false,"m":3,"peak":1217946,"reason":"none"},"intent":"none","ix":"2c1459766a263fdc","pr":"ad1c42c79dad98fa","q":"<hash of the query>","r":[["PM-005.1","stmt-thm-main",6809787,["catalan","irrationality","constant"]],["PM-017.1","stmt-thm-main",5591202,["irrationality","constant"]],["PM-211.7","stmt-thm-main",4900567,["catalan","constant"]],<17 more rows>],"router":"route_v2.py/2.0.1","schema":"ctx.shortlist.v2"}
```

`r` is ranked best first; a row is `[paper_id, anchor, score, matched query terms]` (the terms are omitted for weak rows), the score is an integer comparable only within one answer, and `abstain.flag` false means the query has lexical support (see "Honest limits" below for what a set flag means). `ix` and `pr` identify the index and the parameters used.

## What is in the repository

| Path | Content |
|---|---|
| `papers/` | 719 self-contained Markdown papers: the upstream paper (section 7) plus generated reading aids, reading maps and structured JSON blocks; coordinate grammar in [Catalogo_Math.md](Catalogo_Math.md#0-dimensions-and-conventions) |
| `catalogue/`, `Catalogo_Math.md`, `CATALOGUE.md` | subject shards, families, routes, per-paper records (typed relations are not shipped as verified edges; see below) |
| `tools/` | router, index builder, evaluation, tuning, router gates, documentation check, publication lint, reproduction scripts |
| `standards/` | JSON schemas, router vocabulary/thesaurus, parameter grid |
| `out/` | built index (`index/`), tuned parameters, tuning report, v1 baseline index, DEV receipts, gate receipt |
| `eval/`, `test_eval/` | benchmark with final graded labels (DEV 90 queries, TEST 72) and TEST receipts |
| `tests/` | unit and fixture tests |
| `docs/` | measured results and metric definitions, release notes, design notes (not fully implemented) |
| `release/` | release manifest and per-paper fidelity record |
| `search/` | optional SQLite layout (`schema.sql`), not built in this repository |
| `v1_frozen/` | the v1 router and builder, frozen as the comparison baseline |
| `.github/` | CI workflow, issue and pull request templates |

Status words you will meet in every paper header: `status ACTIVE` marks a current catalogue record, while `Publication status: DRAFT` and `Action rule: ABSENT` are the corpus's own fields and mean "not independently verified" and "generated action rule not present". They are kept byte-identical because the index and the published numbers hash the papers (details in "Corpus status fields" of `docs/RESULTS.md`), so they do not mean the paper is unfinished or withdrawn.

Typed relations between papers (for example `uses`, `generalises`) are stored inside each paper (section 9) and compiled into `out/index/edges.json`: 1,308 relations, none of them verified (all have status `PENDING`), which is why `graph_edges` is 0 in `release/manifest.json`. The router's tuned edge weight is 0, so they do not affect ranking.

## How routing works

1. The query is tokenised (case-folded, stop words dropped) into terms.
2. Each paper statement is indexed in weighted zones (trigger, task, Q&A, title, synonyms, purpose, keywords, outputs, prerequisites).
3. Scoring is integer-only (no floats), so results are bit-reproducible across machines.
4. A small thesaurus adds a few expansion terms when the query shares none with a statement.
5. Phrase matches and the paper's subject domain add bounded boosts.
6. Query intent (method, bound, prerequisite, ...) shifts weight toward the matching zone.
7. Candidates are ranked per statement and returned with the best anchor of each paper.
8. Coverage and peak-score thresholds decide whether to abstain.
9. Rows are packed under the byte budget, best first.
10. The index is built deterministically from `papers/` and `catalogue/`; `build_index_v2.py --check` proves the shipped index is byte-identical to a rebuild.

## Benchmark (TEST split: evaluated once after the parameter freeze; receipt regenerated once after a label rename, metrics unchanged)

72 queries written blind to the router, 39 answerable and 33 not answerable from the corpus; relevance labels graded by two independent model graders, disagreements adjudicated by a third (Cohen's kappa 0.89 between the two graders on pooled pairs, binary relevance; definition, the DEV value and what is not recorded about the graders: `docs/RESULTS.md`). Metrics are over the 39 answerable queries.

| System | R@1 | R@5 | MRR | nDCG@5 | Answer bytes p50 / max | Abstention F1 |
|---|---|---|---|---|---|---|
| **math-router v2.0.1** | 0.222 | 0.516 | 0.596 | 0.463 | 1,077 / 1,167 | 0.647 |
| v1 (row budget 2,000 B) | 0.090 | 0.114 | 0.256 | 0.128 | 2,246 / 2,801 | - |
| v1 (unbudgeted) | 0.090 | 0.266 | 0.352 | 0.250 | 18,180 / 22,181 | - |
| B1 (v1 lexical-only baseline) | 0.052 | 0.156 | 0.234 | 0.156 | - | 0.350 |

R@k is the share of a query's relevant papers (grade 2 or 3) found in the top k, averaged over queries; it is not a hit rate. As a hit rate, the top row is relevant for 17 of 39 answerable queries (hit@1 0.436) and some top-5 row is relevant for 33 of 39 (hit@5 0.846). Metric definitions: `docs/RESULTS.md`. With only 39 answerable queries the figures are noisy: the 95% bootstrap interval of v2.0.1 R@1 spans 0.12 to 0.34 and that of hit@5 spans 0.72 to 0.95 (all intervals and paired differences: `docs/RESULTS.md`, `test_eval/bootstrap_ci_TEST.json`). B1 abstention F1 0.350 and the v1 "-" are explained in `docs/RESULTS.md`. The "row budget" of v1 applies to the sum of its result rows only; its envelope (query, parameters, abstention) comes on top and at least one row is always kept, so v1 answers can exceed 2,000 B (they are 2,246 B at p50), unlike v2, whose whole answer is capped.

All 14 router gates pass. Reproduce: `sh tools/reproduce_test.sh` (TEST) and `sh tools/reproduce_dev.sh` (DEV tuning).

Honest limits: R@1 is 0.22; most topic classes have fewer than 10 answerable test queries, so per-class numbers are anecdotal. The abstention flag is a lexical heuristic with precision 0.629 and recall 0.667 on the unanswerable queries, and it also flags 13 of the 39 answerable queries (33%): an abstain flag means "weak lexical support", not "the corpus has no answer", so inspect the top rows before concluding there is none. See `docs/RESULTS.md`.

## Reproduce the numbers

`sh tools/reproduce_test.sh` re-runs the TEST split from the shipped files and compares the `systems` section, the benchmark hash and the index hash with the shipped receipt `test_eval/test_run_v2.0.1.json`; it prints `TEST metrics reproduced` or `MISMATCH`. `sh tools/reproduce_dev.sh` re-runs the DEV tuning (null test, grid search, abstention fit) and compares the parameters, tuning report and unjudged pairs byte for byte with `out/params.json`, `out/tune_report.json` and `out/unjudged_pairs.jsonl`. CI runs both on every push, plus `python3 -I tools/bootstrap_ci.py --check` for the confidence intervals and a byte comparison of a fresh gates run with `out/gates_v2.0.1.json`. The TEST receipt was regenerated once after a source label of the DEV file was renamed; the fields that changed (hashes only) are listed in `docs/receipt_regeneration.json`.

## What is measured vs claimed

Measured, with receipts in this repository: the ranking metrics, answer sizes and abstention figures above (`test_eval/test_run_v2.0.1.json`), the DEV run (`out/run_DEV_v2.0.1.json`) and the 14 gates (`out/gates_v2.0.1.json`). Claimed, not measured here: the mathematical correctness of the papers and generated sections and the label quality beyond the stated grader agreement; both rest on model graders plus deterministic gates, not on human expert review. One DEV pair (query W-R12, paper PM-101.1) was never judged and is listed in `out/unjudged_pairs.jsonl`; no judgement was invented for it (see `docs/RESULTS.md`).

## Verify

```bash
python3 -I tools/build_index_v2.py --root . --out out/index --check
python3 -I tools/gates_v2.py --all --root "$PWD" --index out/index --params out/params.json --dev eval/dev.jsonl --out "${TMPDIR:-/tmp}/gates.json"
cmp "${TMPDIR:-/tmp}/gates.json" out/gates_v2.0.1.json
sh tools/reproduce_test.sh
sh tools/reproduce_dev.sh
python3 -I tools/bootstrap_ci.py --check
python3 -I -m unittest discover -s tests -p 'test_*.py'
python3 -I tools/claims_check.py
python3 -I tools/publication_lint.py .
```

The same commands, plus a secret scan, run in `.github/workflows/ci.yml` on Python 3.10, 3.11, 3.12 and 3.13. See `CONTRIBUTING.md` and `ARCHITECTURE.md`.

## How this was built

Gemini 3.8 Flash, Gemini 4 Argon, GPT-6.1 Sol, GPT-6 Luna, Claude Opus 5.5 and Claude Sonnet 5.5 (model versions as of 2026-10), under deterministic, model-free gates. In each paper, section 7 is the upstream paper converted from TeX to Markdown, with citations, cross-references, label anchors, bibliography entries and figure descriptions restored by recorded insertions; the abstract text in each paper's `abstract_verbatim` field is recorded as the upstream abstract (`NOTICE` states what this repository can and cannot show about it). Sections 0 to 6, 8, 9 and 10 were added and are generated or assembled as marked (each paper's modification notice says so). Every paper still carries the status fields `DRAFT` and `ASSEMBLED` and an action-rule placeholder: they are the corpus's own status fields, kept unchanged so the published numbers stay byte-reproducible; see "Corpus status fields" in `docs/RESULTS.md`. Contact: [Contact.md](Contact.md). Contributions: `CONTRIBUTING.md`; conduct: `CODE_OF_CONDUCT.md`.

## License

Apache-2.0 (see `LICENSE`, `NOTICE`).
