## What changed

## Checks (run from the repository root)

- [ ] `python3 -I tools/build_index_v2.py --root . --out out/index --check`
- [ ] `python3 -I tools/gates_v2.py --all ...` (see CONTRIBUTING.md)
- [ ] `sh tools/reproduce_test.sh`
- [ ] `python3 -m unittest discover -s tests`
- [ ] `python3 -I tools/claims_check.py`
- [ ] No private paths, identities or credentials; no tuning on TEST
