# Architecture (shipped system, v2.0.1)

The repository has two layers: a corpus of 719 structured Markdown papers with navigation records, and an offline router that answers a question with at most 2,000 bytes of ranked pointers into that corpus. Everything below exists in this repository. The larger design the corpus was produced under, including parts that are not implemented, is in [docs/DESIGN.md](docs/DESIGN.md).

## Data flow

```text
papers/*.md  ──(inline JSON blocks)──►  catalogue/        subjects, families, routes, per-paper records
     │                                      │
     └──────────────┬───────────────────────┘
                    ▼   tools/build_index_v2.py   (deterministic, integer-only)
               out/index/  +  out/params.json   (parameters fitted on DEV only)
                    ▼   tools/route_v2.py
        {"abstain":..., "r":[[paper_id, anchor, score], ...]}   <= 2,000 bytes
                    ▼   catalogue/routes.tsv  (paper_id -> file path)
        open the paper, jump to the anchor <a id="..."></a>
```

Rules that make this reproducible: scoring uses integers and exact fractions only; the index depends only on `papers/`, `catalogue/`, `standards/thesaurus.json` and `tools/build_index_v2.py`; `build_index_v2.py --check` proves the committed `out/index` is byte-identical to a rebuild; parameters are fitted on the DEV split only and the TEST split is evaluated once after the freeze.

## Papers and records

Each paper in `papers/` is one Markdown file named `<coordinate>_<pm_id>_<Title_Slug>.md`; clients take the path from `catalogue/routes.tsv`, never from an identifier. The coordinate grammar is defined in section 0 of [Catalogo_Math.md](Catalogo_Math.md#0-dimensions-and-conventions) (also reachable as [CATALOGUE.md](CATALOGUE.md)). A paper has numbered sections: 0 reading map, 1 abstract and result contract, 2 definitions and bounds, 3 proof roadmap, 4 engineering contracts, 5 domain contracts, 6 applicability limits and search fields, 7 the complete paper, 8 citations and figures, 9 paper graph, 10 verification and provenance. Section 7 is the upstream paper converted from TeX to Markdown; the other sections are generated or assembled and labelled as such (see `docs/RESULTS.md`, "Corpus status fields"). Machine-readable `pm.*` JSON blocks inside the papers are validated by the schemas in `standards/schemas/`.

Identifier forms: the paper block `pm.node.v2` stores `family` as the three-digit upstream family number (for example `009`); the catalogue records (`catalogue/families/PM-009.json`, the `pm.connector.v1` nodes) store the same family with the `PM-` prefix (`PM-009`). The builder adds the prefix; no information differs.

## Repository tree

```text
README.md  AGENTS.md  llms.txt  CONTRIBUTING.md  CHANGELOG.md  SECURITY.md  CODE_OF_CONDUCT.md  Contact.md
LICENSE  NOTICE  CITATION.cff  ARCHITECTURE.md  CATALOGUE.md  Catalogo_Math.md  .gitleaks.toml
papers/            719 papers
catalogue/         README.md, subjects.json, subjects/<id>/ (page shards), details/ (large nodes), families/, routes.tsv, measurements.json
standards/         schemas/ (inline-block, connector, router schemas), thesaurus.json, grid.json
tools/             route_v2.py, build_index_v2.py, eval_v2.py, tune_v2.py, null_edges.py, gates_v2.py, claims_check.py,
                   publication_lint.py, bootstrap_ci.py, reproduce_test.sh, reproduce_dev.sh, and helpers
out/               index/ (built index), params.json, tune_report.json, run_DEV_v2.0.1.json, gates_v2.0.1.json,
                   ablation.json, census.json, protocol.json, unjudged_pairs.jsonl, v1_index/ (v1 baseline index)
eval/              dev.jsonl (DEV benchmark, 90 queries)
test_eval/         bench_test_graded.jsonl (TEST, 72 queries), test_run_v2.0.1.json, cold_latency_TEST.json, bootstrap_ci_TEST.json
tests/             unit tests (modules T0 to T13, there is no T4) and fixtures/
docs/              docs/RESULTS.md, docs/RELEASE_NOTES_v2.0.1.md, docs/DESIGN.md, docs/receipt_regeneration.json, docs/schemas/
release/           manifest.json, fidelity.json
search/            schema.sql (optional SQLite layout, not built here)
v1_frozen/         the v1 router and builder, frozen for baseline comparison (SHA256SUMS)
.github/           workflows/ci.yml, pull_request_template.md, ISSUE_TEMPLATE/
```

## Checks

Two separate things are called gates or lint; they are different tools.

**Router gates** (`tools/gates_v2.py --all`) are the 14 gates below. The receipt is `out/gates_v2.0.1.json`.

| Gate id | What it checks |
|---|---|
| `g_rebuild` | a rebuild of the index from the sources is byte-identical |
| `g_fresh` | every source file hash recorded in the index manifest matches the file on disk |
| `g_volatile` | the rebuild is stable and the entry files (`llms.txt`, `AGENTS.md`, `catalogue/subjects.json`, `out/protocol.json`) contain no ISO timestamps |
| `g_size` | every index file is under the size cap and the manifest's maximum matches |
| `g_nofloat` | no floating-point value in the index or in router answers |
| `g_schema` | manifest, parameters, thesaurus, answers and protocol validate against their schemas |
| `g_anchor` | every anchor returned for the DEV queries exists in the paper file |
| `g_compact` | DEV answers respect the byte budget and answer shape |
| `g_determinism` | repeated and mount-shuffled runs give identical answers |
| `g_stdlib` | the tools import only the standard library and each other |
| `g_thes` | the thesaurus entries are valid for the index and are justified on DEV |
| `g_blind` | tuning refuses TEST rows and bench-directory paths; the parameters pin the DEV file hash |
| `g_calib` | DEV has both answerable and unanswerable queries |
| `g_privacy` | the index and entry files contain no home-directory path, e-mail address or owner name |

**Publication lint** (`tools/publication_lint.py`) is a generic scan of the whole tree: absolute home-directory paths, e-mail addresses outside `Contact.md`, private-key headers, well-known token shapes (errors), and non-English file names (warnings). It needs no policy file and runs in CI. The maintainer's stricter, policy-driven release scan is not part of this repository.

**Other CI checks** (`.github/workflows/ci.yml`, Python 3.10 to 3.13): `build_index_v2.py --check`, `reproduce_test.sh` (TEST metrics equal the shipped receipt), `reproduce_dev.sh` (DEV tuning reproduces `out/params.json`), a byte comparison of a fresh `gates_v2.py` run with `out/gates_v2.0.1.json`, `bootstrap_ci.py --check` (the confidence intervals in `docs/RESULTS.md` and `test_eval/bootstrap_ci_TEST.json` are reproduced), the unit tests, `claims_check.py` (paths, tools, flags and quoted numbers in the docs exist and match the receipts), and a gitleaks secret scan with a verified binary and three planted-credential negative controls (`SECURITY.md`).
