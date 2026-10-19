# Agent protocol

Find the right theorem in 719 preprints without reading them. All commands are offline, Python >= 3.10 standard library only, run from the repository root.

## Ladder (stop at the first rung that answers the task)

| Rung | Action | Cost |
|---|---|---|
| 0 | Read `llms.txt` | ~100 tokens |
| 1 | `python3 tools/route_v2.py --q "<question>"` (defaults: `out/index`, `out/params.json`) | one JSON line, <= 2,000 bytes |
| 2 | Resolve the paper path: add `--paths` to rung 1 (`files` maps id to `papers/<file>#<anchor>`), or `awk -F'\t' '$1=="PM-005.1"{print $3}' catalogue/routes.tsv` (columns in `catalogue/README.md`) | one line |
| 3 | Open the paper and jump to the anchor returned in rung 1 (`<a id="ANCHOR"></a>`) | one statement |
| 4 | Read the paper's reading map, then only the sections the task needs | bounded slice |
| 5 | Browse by topic: `catalogue/subjects.json` -> subject shard -> family/node records | fallback |

Never build a filename from an identifier; always take the path from `catalogue/routes.tsv`.

## Reading the router answer

`{"abstain":{...},"intent":...,"r":[[id, anchor, score, matched_terms?], ...],...}` — `r` is ranked best first; `score` is an integer, comparable only within one answer. Use `--k N` for N rows and `--intent` (find_method, find_structure, find_bound, find_prerequisite, check_claim, find_limit, locate_id) to bias the section choice. Pass a bare identifier such as `PM-005.1` to look a paper up directly.

## Budgets

- The answer is capped at 2,000 bytes by default (`--budget`); rows are dropped to fit and `overflow: true` is set when that happens.
- Take the top 3 rows first. Open more only if they do not contain the claim.
- A paper can be very large; never load one whole when an anchor is available.

## Abstention

`abstain.flag = true` means the query has little lexical support in the corpus. Reasons: `no_query_term`, `low_term_match`, `below_tau` (`exact_id` marks a direct identifier lookup). When it is set:
1. Rephrase with the mathematical objects named explicitly (not the application) and retry once.
2. Otherwise browse `catalogue/subjects.json`.
3. Otherwise, before concluding "no match", inspect the top 3 rows of `r` (rows are still returned for `low_term_match` and `below_tau`; `no_query_term` returns none) and report only what those papers actually state. Do not guess an identifier.

The flag is a heuristic: on the shipped TEST split it catches 67% of unanswerable queries at 63% precision, and it also flags about 33% of answerable queries (13 of 39); see `docs/RESULTS.md`. A set flag therefore means weak lexical support, not absence, and `flag = false` does not prove the corpus answers the question.

## Evidence rules

Inline paper text is authoritative. A router score, a catalogue entry or a model-written interpretation never establishes a theorem on its own. Quote statement, hypotheses and the paper identifier when you cite a result. Generated sections are labelled as such; stated and inferred uses are kept separate.

## Verify and rebuild

```bash
python3 -I tools/route_v2.py --q "..." --verify .   # fails if the index is stale
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

Benchmark figures live in `docs/RESULTS.md` (definitions of R@k, MRR, nDCG and abstention included).

## Editing rules

Changing any paper, catalogue file, `standards/thesaurus.json` or `tools/build_index_v2.py` makes the index stale; rebuild it and re-run the gates. Keep published text in English and free of private paths, identities and credentials. Do not tune on the TEST split.
