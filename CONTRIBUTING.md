# Contributing

Python 3 standard library only; no network. Run everything from the repository root.

## Run the checks

```bash
python3 -I tools/build_index_v2.py --root . --out out/index --check
python3 -I tools/gates_v2.py --all --root "$PWD" --index out/index --params out/params.json --dev eval/dev.jsonl --out /tmp/gates.json
sh tools/reproduce_test.sh
python3 -m unittest discover -s tests
python3 -I tools/claims_check.py
```

Changing any paper, catalogue file, `standards/thesaurus.json` or `tools/build_index_v2.py` makes the index stale: rebuild `out/index` with `tools/build_index_v2.py --root . --out out/index` and re-run the checks. These are the same steps as `.github/workflows/ci.yml`.

## Pull requests

- Never push directly to `main`. Work on a branch and open a pull request; CI must pass.
- Agents follow the same flow: one branch per task, commits limited to the files the task owns, no force pushes.
- Do not tune parameters on the TEST split.
- Keep published text in English and free of private paths, identities and credentials.
- Documentation may only name files, tools and flags that exist; `tools/claims_check.py` enforces it.
- Keep mathematical content faithful to the source; `NOTICE` lists the allowed kinds of changes.
