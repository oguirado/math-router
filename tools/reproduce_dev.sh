# Run with: sh tools/reproduce_dev.sh
# Re-run the DEV tuning (null test, then grid search and abstention fit) from the shipped files and compare the result
# with the shipped parameters (out/params.json), tuning report (out/tune_report.json) and unjudged pairs.
# The procedure is deterministic: integer scoring, exact fractions, and a fixed-seed null test, so all three must match byte for byte.
set -e
cd "$(dirname "$0")/.."
T=$(mktemp -d)
python3 -I tools/null_edges.py --index out/index --bench eval/dev.jsonl --out "$T/null.json"
python3 -I tools/tune_v2.py --index out/index --bench eval/dev.jsonl --null "$T/null.json" --grid standards/grid.json \
  --out "$T/params.json" --report "$T/tune_report.json" --unjudged-out "$T/unjudged_pairs.jsonl"
ok=1
for f in params.json tune_report.json unjudged_pairs.jsonl; do
  src=out/$f
  cmp -s "$T/$f" "$src" || { echo "MISMATCH $f"; ok=0; }
done
printf 'params sha256 %s\n' "$(python3 -I -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$T/params.json")"
rm -rf "$T"
if [ "$ok" = 1 ]; then echo "DEV tuning reproduced"; else exit 1; fi
