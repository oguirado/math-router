# Design notes: a computable mathematical paper library

**Status: design, not fully implemented.** This document describes the intended full design of the paper library. The shipped system is smaller; `ARCHITECTURE.md` describes exactly what this repository contains and which checks run. Differences, as of v2.0.1:

| Design element in this document | Status in this repository |
|---|---|
| Papers with machine-readable inline blocks, catalogue shards, routes | Shipped (`papers/`, `catalogue/`) |
| Deterministic router and index | Shipped (`tools/route_v2.py`, `out/index`) |
| The gates named the gateway gate, `G-ID`, `G-PATH`, ..., `G-CATALOGUE` | Design names only. The checks that run are the 14 router gates of `tools/gates_v2.py` (listed in `ARCHITECTURE.md`) plus the checks in `.github/workflows/ci.yml` |
| Verified typed edges | Not shipped: every one of the 1,308 relations in the papers has verification status `PENDING`, and `graph_edges` is 0 in `release/manifest.json` |
| Embedding-based candidate selection, rerankers | Not shipped |
| Executable panels with independent oracles and mutant receipts | Present as text in section 4 of each paper; no receipts are shipped |
| Lean 4 re-check receipts | Not shipped |
| Closed repair loop | Not shipped (it is a description of how the corpus was produced and could be maintained) |

Everything below is the design as written; read it as intent, not as a description of shipped behaviour.

## Problem: discovery loses scope and ingestion loses evidence

A flat list of preprints does not expose the conditions under which their results apply. Summaries can omit hypotheses; an application bridge can imply an algorithm that a proof never constructs. Complete long papers require planned reading, while a single catalogue containing every detailed node is too large to be a universal entry page. Search ranking alone cannot decide any of these questions.

The release therefore needs separate navigation and authority. A small entry plane selects a subject and a paper. Complete Markdown preserves the paper. Machine records expose inputs, outputs, negative applicability and evidence without replacing proofs.

## Dual-tier solution and release tree

```text
release root
|-- llms.txt                   entry pointer
|-- AGENTS.md                  operating and publication contract
|-- README.md                  user navigation and evidence boundaries
|-- ARCHITECTURE.md            the shipped architecture (this design is docs/DESIGN.md)
|-- LICENSE                    exact source Apache-2.0 text
|-- NOTICE                     retained notices and modifications
|-- Catalogo_Math.md            dimensions, family register, subject links
|-- papers/
|   `-- <coordinate>_<pm_id>_<Title_Slug>.md
|-- catalogue/
|   |-- subjects.json           bounded subject index
|   |-- subjects/<subject_id>/
|   |   |-- index.json          page pointers, keywords, measured sizes
|   |   `-- pages/<page_id>.jsonl
|   |-- details/<pm_id>.json    full node when too large for a page
|   |-- families/<family_id>.json
|   |-- routes.tsv             compact derived path ledger
|   `-- README.md              mount note and edge location
|-- standards/
|   |-- schemas/               exact paper, connector and router schemas
|   |-- thesaurus.json         router vocabulary
|   `-- grid.json              parameter grid
|-- tools/
|   |-- release_gate.py        publication lint
|   |-- claims_check.py        documentation claims check (CI)
|   `-- build_index_v2.py      deterministic index builder, `--check` verifies the shipped index
|-- search/
|   `-- schema.sql             optional standard SQLite interface
|-- eval/
|   `-- dev.jsonl              DEV benchmark with final graded labels
`-- release/
    |-- manifest.json          external artifact hashes and counts
    `-- fidelity.json          per-paper gate verdict and receipt hash (catalogue telemetry)
```

The tree describes the shipped repository; tools not listed here (router, evaluation, gates) are documented in `AGENTS.md` and `README.md`. Optional databases are rebuilt locally and are not committed binary payloads. Model briefs, quota records, private policy inventories, local logs and failed fixtures remain outside the release tree.

```text
TIER 1: gateway                 TIER 2: connectable nodes
llms.txt --------------------> subject index
AGENTS.md                           |
README.md                           v
                            subject -> page -> node
                                              |
                                 exact paper path + anchors
                                              |
                              complete text + inline blocks
```

`llms.txt` has a hard token ceiling enforced by the gateway gate. The subject index has a separate bounded token budget in `release/manifest.json`; it stores subject names, scoped keywords, shard pointers and measured sizes, rather than detailed paper nodes. Subject page splits are deterministic by identifier order and measured serialized token length. A node too large for a subject page goes in `catalogue/details/<pm_id>.json`; its page contains a strict `pm.connector-ref.v1` descriptor with `schema,id,paper,detail,detail_context`. The detail context gives measured `bytes,tokens,tokenizer` for that complete node. The detail file is explicitly outside the page cap and must be read in admitted slices. No node is clipped. Family indexes refer to paper nodes rather than copying their proof text.

All paths are repository-relative and resolve inside the release tree. The `paper` value comes from `pm.node.v2.filename`; `G-PATH` checks the actual file and anchors from another working directory. No client constructs a paper path from an identifier. Original source coordinates remain separate from the final coordinate. The established corpus grammar is preserved; final TOK is recomputed from the final file. `pm.node.v2.context.tier` uses the same four grammar tiers as the coordinate (T1 below 10,000 tokens, T2 below 30,000, T3 below 60,000, T4 otherwise), and the exact measured count is kept in `context.tokens`.

The configured admission limits use the pinned `o200k_base` tokenizer: gateway below 150 tokens, subject index at most 2,048 tokens, each subject page at most 12,000 tokens. These are policy limits, not measured performance claims. The compiler records actual serialized counts in the external manifest and rejects a page over its cap; sharding changes the page set, never the retained paper content.

## Universal node schema adapted to papers

`pm.connector.v1` is a compiled projection, not a second source of mathematical authority. Its executable schema is `standards/schemas/connector-node.v1.schema.json`. Every object has closed keys; all root keys are required. The exact root is:

```json
{
  "schema": "pm.connector.v1",
  "id": "PM-999.1",
  "family": "PM-999",
  "subject_id": 1,
  "coordinate": "fixture-only",
  "paper": "papers/fixture.md",
  "title": "Schema fixture, not a corpus paper",
  "purpose": "Illustrate the connector shape without claiming a result.",
  "status": "ACTIVE",
  "claim_status": "CORPUS_CLAIMED",
  "inputs": {"hypotheses": [], "prerequisites": []},
  "outputs": [],
  "synergies": [],
  "domains": [],
  "exclusions": [],
  "telemetry": {
    "fidelity": {"status": "PENDING", "receipt_sha256": null, "coverage_manifest_sha256": null},
    "oracle": {"status": "NOT_APPLICABLE", "receipt_sha256": null, "coverage": [], "mutant_receipts": []},
    "retrieval": {"snapshot_sha256": null, "receipt_sha256": null, "metrics": []}
  },
  "context": {"bytes": null, "tokens": null, "tokenizer": null, "tier": null, "reading_anchor": "pm-s0"},
  "source_hashes": {"paper_sha256": null, "canonical_sha256": null, "repaired_body_sha256": null, "blocks_sha256": {}}
}
```

This fixture demonstrates syntax. It intentionally lacks the evidence needed for publication; `G-ADMISSION` rejects its absent hashes, measurements and fidelity receipt. Schema validity is not release eligibility.

| Connector field | Exact source or transformation | Verification gate and negative contrast |
|---|---|---|
| `id,family,subject_id,coordinate,title,status,claim_status` | `pm.node.v2.pm_id,family,subject_id,coordinate,title,status,claim_status` | `G-ID`: exact registry join; wrong sibling identity fails |
| `paper` | `papers/` plus validated `pm.node.v2.filename` | `G-PATH`: existing relative path, exact final file hash; guessed identifier filename fails |
| `purpose` | Supported `pm.search.v1.questions_answered[].question`; otherwise exact title | `G-PROJECTION`: deterministic selection; an unsupported engineering promise fails |
| `inputs.hypotheses[]` | `pm.claims.v2.claims[].id,statement_anchor,hypotheses`; copy each condition with its governing claim | `G-CLAIM`: scope and quantifier preservation; exists-to-forall fails |
| `inputs.prerequisites[]` | `pm.search.v1.prerequisite_chains[].concept,requires_concepts,supporting_pm_ids,evidence` | `G-PREREQUISITE`: known identities and evidence; unknown target or prerequisite cycle fails |
| `outputs[]` | `pm.claims.v2.claims[].id,kind,statement_anchor,exact_statement` | `G-OUTPUT`: result and construction scope match the complete statement; invented runtime fails |
| `synergies[]` | Supported `pm.edges.v2.edges[]`, preserving source and target quotes and anchors | `G-EDGE`: both endpoints and exact quotes, direction and independent semantic receipt; similarity-only edge fails |
| `domains[]` | Every `pm.domains.v2.domains[]` plus supported `additional_domains[]`; retain domain, applies, strength, maturity, basis and verification | `G-DOMAIN`: complete checklist and source support; software-only coverage fails |
| `exclusions[]` | `pm.search.v1.exclusions[].query,reason,evidence` | `G-EXCLUSION`: separate negative index; rejected task in positive routing fails |
| `telemetry.fidelity` | `pm.provenance.v2.verified_sections[]` and independent source-object coverage receipt | `G-FIDELITY`: receipt hashes bind unchanged paper and repair manifest; self-certified PASS fails |
| `telemetry.oracle` | `pm.triptych.v2.panel3.execution_status,host_receipt_sha256,coverage_map,mutants` plus matching coverage in the referenced receipt | `G-ORACLE`: exact reference/oracle code hashes, scope, every mutant rejected; a surviving mutant fails |
| `telemetry.retrieval` | Same-generation held-out evaluation receipt | `G-EVAL`: metric, cohort and snapshot hashes; stale card/index comparison fails |
| `context` | `pm.node.v2.context` and `pm.reading.v2` | `G-CONTEXT`: measured final bytes/tokens, reading anchor and complete span cover; null counted as zero fails |
| `source_hashes` | External final-paper hash, `pm.provenance.v2.canonical_sha256,repaired_body_sha256`, serialized inline block hashes | `G-HASH`: deterministic recomputation; a repaired file with old receipts fails |

The inline graph relation vocabulary is `prerequisite`, `uses`, `generalises`, `specialises`, `shared_technique`, `shared_constant`, `contradicts`, `supersedes`. Record directed relations in their documented source-to-target meaning. Shared-technique and shared-constant relations are symmetric; compile one canonical unordered edge while retaining its paper views. Contradiction requires incompatible conclusions under the same hypotheses, not merely different regimes. Source versions and withdrawal notices remain explicit identities; their presence never makes them active recommendations.

Every inventoried source preprint receives a status-aware identity and its complete readable paper or, for a withdrawn item without a paper, its retained notice. Superseded papers remain complete separate files; an active sibling does not absorb their ownership. The history gate checks all identities independently of the active-paper cohort used for retrieval evaluation.

`synergies` never means unconstrained composability. Evidence must support the claimed transfer and applicable regime. Cycles are forbidden in the prerequisite projection, not in the full graph of arbitrary relations. Candidate links are not published as supported graph edges until independently verified.

## Catalogue anatomy in the software-style model

`Catalogo_Math.md` is deterministically compiled in the following order. Its detailed paper-node fences are in linked subject shards, keeping the root catalogue navigable.

| Section | Exact public content | Compiler source and gate |
|---|---|---|
| Header and standards | Schema versions, grammar identity, manifest hash, measured coverage, gateway links | External release manifest; `G-HASH` rejects old counts and stale hashes |
| Section 0: dimensions and conventions | `LANG,DOM,TECH,PAR,LVL,YR,FMT,TOK,REL,DEP,MAT,QUA,DUT,PRI,IDX`; subject-domain map, context/claim-status rules | Preserved grammar and final nodes; `G-ID` rejects changed axis meanings |
| Family register | Family id/title, exact members and version statuses, entry-paper path, applicable formal-scope note | Registry/provenance joins; `G-FAMILY` rejects missing members and cross-version scope upgrades |
| Subject index and paper rows | `id,title,status,coordinate,paper,main_anchor,context_tokens,claim_status`; shard links | Final nodes and measured context; `G-PATH` rejects dangling routes |
| Node fences in subject shards | `pm.connector.v1` and bounded supported search view | Inline blocks only; `G-CATALOGUE` requires exact deterministic recompilation |
| Relations and negative routing | Supported typed graph links, prerequisites, exclusions | Verified graph/search blocks; `G-EDGE` and `G-EXCLUSION` |
| Version notices and verification | Withdrawn/superseded records, successor links, coverage and receipt links | Identity and independent receipts; `G-ADMISSION` rejects absent verification |

No host substrate, private producer names, quota data or unpublished workspace paths are imported from the catalogue model. Its anatomy and evidence discipline transfer; its environment-specific headers and coordinate changes do not.

## Continuous-improvement loop (design)

```text
 frozen eval failures + weak sections + missing candidate edges
                             |
                             v
       anchored repair request, pinned source and dependencies
                             |
                             v
       targeted annotation generation and independent verification
                             |
                             v
       schemas -> source coverage -> oracle/mutants -> release lint
                  | FAIL                       | PASS
                  v                            v
       retain last accepted revision      build out/index
                  |                            |
                  `---------- receipts + held-out eval ----------'
```

The loop detects missing answers, weak domain explanations and unsupported graph candidates. It regenerates only affected annotations. Mathematical content is copied or repaired deterministically from source evidence; models do not rewrite source equations. Every change invalidates dependent receipts, graph entries, vectors and catalogue projections. Finite repair budgets end in quarantine when gates do not close; convergence is not promised.

Constructive or algorithmic results receive the executable engineering panel (section 4 of each paper). The independent reference must differ from the implementation being tested. Checks remain active in optimised execution; Python checks cannot rely on removable `assert` statements. Receipts list the tested scope and exact code hashes, and reject every planted semantic mutant. Partial test coverage stays partial. Pure-theory papers retain contract and negative panels with an explicitly non-applicable implementation panel.

Graph-edge proposals come from from candidate paper pairs selected by embeddings and lexical evidence. Each candidate reads both complete governing statements and relevant proof dependencies; independent verification judges the relation and scope. Similarity provides candidates only. Pair selection, source/target hashes and accepted-edge revision are reproducible. Exact quotes and anchors must resolve inside the released papers.

Retrieval uses supported search fields and body objects, with exclusions in a separate channel. Reranking is evaluated on matching paper-body chunks and supported task fields rather than summary-only inputs. No improvement is claimed until an evaluation receipt measures it on a frozen corpus with held-out questions and negative tasks. A measurement names its metric, cohort, snapshot, method and result; a missing receipt leaves the metric absent.

External literature may suggest an engineering use or query. It is stored as separately attributed commentary and must pass the same scope checks. It cannot change the paper's own result or erase an extraction defect.

## Public-release contract

Complete readable Markdown replaces encoded PDF, whole TeX archives, Lean project closures and inline images. Small exact diagram source belongs beside its caption and textual witness. When the source corpus has a Lean 4 comparator challenge for the paper's family, the paper carries a "Formal statement (Lean 4)" subsection at the end of section 6, before the complete paper body, with the `pm.formal.v2` block: pinned toolchain and Mathlib revision, the family scope note copied verbatim, the declarations with their exact statements, and the comparator metadata. The comparator source file is inlined verbatim when it is at most 30,720 bytes; a larger file contributes its declaration statements only and the omitted byte count is recorded. The status is "formalized in the source corpus"; it never states that this release re-checked the proof unless a separate Lean re-check receipt is attached. Papers without a comparator carry `pm.formal.v2` with status `none`. No vendored library code is published. Object coverage, citation associations, uncited bibliography records and label targets are independently audited; matching the old Markdown hash does not close extraction losses.

Each paper carries original title, slug, date and the explicit modified-source attribution. A missing original field blocks publication until resolved; it is not invented. The upstream Apache-2.0 licence is copied unchanged. Applicable upstream notices are inventoried independently and retained, with modifications recorded in `NOTICE`. A generic draft notice is not proof that notice retention is complete.

`tools/release_gate.py` is the maintainer's release scan. It checks filenames and all text, including code comments and JSON values, for absolute paths, contacts, credentials, configured private identifiers and non-English prose heuristics. It rejects binary/source archives, symlinks and unreadable or bounded-out input. Findings contain only file-name hashes, categories and line numbers. Private deny-policy digests are supplied from outside the release tree; the public scanner contains no private identifier inventory.

The path rule permits only the exact portable Python interpreter shebang on the opening line of a Python script. Extra text on that line is scanned normally. This is a standard executable entry point, not a private environment path. No other code, comment or JSON path exemption is applied. Findings are unique by file, category and line across raw and decoded text views.

Release mode requires an exact Git-index scan, reviewed external policy, actual repository name, unchanged source licence and nonempty notice. A source label that conflicted with the release identity was renamed; required upstream attribution is never removed to clear a scanner conflict. The public CI workflow (`.github/workflows/ci.yml`) runs the generic `tools/publication_lint.py`; the stricter `tools/release_gate.py` scan, which needs an externally supplied policy, is run by the maintainer on the staged tree before each release. A scanner result cannot alone prove English fluency, exhaustive privacy inventory, licence completeness or mathematical correctness; those remain independent admission gates.

The initial public repository is created from a clean export with fresh Git history. Private staging history is not pushed. The scanner excludes Git object storage because it inspects a candidate snapshot; a clean snapshot does not clear earlier commits. Every later public commit passes the staged-tree gate. Importing an existing history requires a separate complete history audit.

Public receipts omit usernames, host/hardware identity, absolute paths, private project/tool names, private transport commands, contacts and quota telemetry. They retain code/paper hashes, generic toolchain version, relative commands, exit codes, check-to-contract coverage and mutant verdicts. An internal host receipt is transformed and revalidated before its public receipt hash is referenced by a released paper.

The final reconstruction gate rebuilds subject/family shards, routes and optional search indexes from released Markdown and public receipts alone, with the extraction workspace unavailable. Missing source-object evidence blocks the release; no deletion or publication operation is authorised by this design document.

## Transfer to other domains

| Domain | Input contract | Output contract | Synergy and telemetry adaptation |
|---|---|---|---|
| Mathematical tools and algorithms | Hypotheses, arithmetic model, prerequisites | Construction, guarantee, complexity where supported | Dependency edges; invariant coverage and mutant receipts |
| Games and simulation | Mathematical regime, state and approximation assumptions | Update rule or model property | Numerical failure modes; measured checks on declared inputs |
| Hardware and accelerators | Supported representation and resource assumptions | Algorithmic kernel or mathematical bound | Data-layout transfer marked inferred unless stated; portable scope receipts |
| Cryptography and security | Adversary, probability and hardness assumptions | Scoped security or impossibility claim | Reduction dependencies; forbidden extrapolations and check evidence |
| Machine learning and optimisation | Distribution, objective and regularity conditions | Bound, construction or obstruction | Shared techniques; held-out routing and implementation evidence |
| Distributed systems | Model, failure and synchronisation assumptions | Invariant, convergence or impossibility result | Prerequisite and conflict edges; declared test-domain coverage |

The connector shape stays constant. Domain semantics and check coverage change. No domain receives an implementation merely because its vocabulary resembles a theorem.

## Synthesis

The gateway selects a bounded catalogue view; the view points to complete papers with exact evidence and context costs. Closed checks govern repairs and projections. The resulting architecture supports navigation, graph construction and engineering use while preserving explicit boundaries around source claims, inferred transfers and tested scope.
