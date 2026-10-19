## What changed

## Checks (run from the repository root; same commands as CONTRIBUTING.md)

- [ ] `python3 -I tools/build_index_v2.py --root . --out out/index --check`
- [ ] `python3 -I tools/gates_v2.py --all --root "$PWD" --index out/index --params out/params.json --dev eval/dev.jsonl --out "${TMPDIR:-/tmp}/gates.json"`
- [ ] `cmp "${TMPDIR:-/tmp}/gates.json" out/gates_v2.0.1.json`
- [ ] `sh tools/reproduce_test.sh`
- [ ] `sh tools/reproduce_dev.sh`
- [ ] `python3 -I tools/bootstrap_ci.py --check`
- [ ] `python3 -I -m unittest discover -s tests -p 'test_*.py'`
- [ ] `python3 -I tools/claims_check.py`
- [ ] `python3 -I tools/publication_lint.py .`
- [ ] No private paths, identities or credentials; no tuning on TEST
