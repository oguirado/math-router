# Contributing

Python >= 3.10, standard library only; no network. Run everything from the repository root. CI runs on Python 3.10, 3.11, 3.12 and 3.13.

## Run the checks

```bash
python3 -I tools/build_index_v2.py --root . --out out/index --check
python3 -I tools/gates_v2.py --all --root "$PWD" --index out/index --params out/params.json --dev eval/dev.jsonl --out "${TMPDIR:-/tmp}/gates.json"
sh tools/reproduce_test.sh
sh tools/reproduce_dev.sh
python3 -I -m unittest discover -s tests -p 'test_*.py'
python3 -I tools/claims_check.py
python3 -I tools/publication_lint.py .
```

Changing any paper, catalogue file, `standards/thesaurus.json` or `tools/build_index_v2.py` makes the index stale: rebuild `out/index` with `tools/build_index_v2.py --root . --out out/index` and re-run the checks. Changing a paper also changes the published numbers; do not edit `papers/` casually (see "Corpus status fields" in `docs/RESULTS.md`). These are the same steps as `.github/workflows/ci.yml`, which adds a secret scan.

## Pull requests

- Never push directly to `main`. Work on a branch and open a pull request; CI must pass.
- Agents follow the same flow: one branch per task, commits limited to the files the task owns, no force pushes.
- Do not tune parameters on the TEST split.
- Keep published text in English and free of private paths, identities and credentials.
- Documentation may only name files, tools and flags that exist, and the benchmark numbers it quotes must match the receipts; `tools/claims_check.py` enforces both.
- Keep mathematical content faithful to the source; `NOTICE` lists the allowed kinds of changes.
- Be kind: see `CODE_OF_CONDUCT.md`.
