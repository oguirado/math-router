# Run with: sh tools/reproduce_test.sh
# Re-run the TEST split from the shipped files and compare it with the shipped receipt.
set -e
cd "$(dirname "$0")/.."
T=$(mktemp -d)
python3 -I tools/eval_v2.py --freeze --out "$T/freeze.json"
python3 -I tools/eval_v2.py --split TEST --bench test_eval/bench_test_graded.jsonl --out "$T/run_TEST.json"
python3 -I - "$T/run_TEST.json" test_eval/test_run_v2.0.1.json <<'PY'
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
ok = a["systems"] == b["systems"] and a["bench_sha256"] == b["bench_sha256"] and a["index_sha256"] == b["index_sha256"]
print("TEST metrics reproduced" if ok else "MISMATCH")
sys.exit(0 if ok else 1)
PY
rm -rf "$T"
