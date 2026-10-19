"""Check that file paths, tools, flags and workflows named in the docs exist in the tree.

Usage: python3 -I tools/claims_check.py [--root DIR]
Exit 0: every claim resolves. Exit 1: at least one dead claim (listed on stdout).
Stdlib only. Scans backticked spans and fenced code blocks of the top-level docs. It also compares the benchmark
numbers quoted in the docs (metric tables, "R@1 0.222"-style phrases, byte sizes, latencies, gate count, hash prefixes)
with test_eval/test_run_v2.0.1.json, test_eval/cold_latency_TEST.json, out/gates_v2.0.1.json and the index manifest.
"""
import hashlib
import json
import argparse
import glob
import os
import re
import sys

DOCS = ["README.md", "ARCHITECTURE.md", "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md",
        "CHANGELOG.md", "CATALOGUE.md", "llms.txt", "docs/*.md", "catalogue/README.md"]
EXT = (".py", ".sh", ".md", ".json", ".jsonl", ".tsv", ".yml", ".yaml", ".txt", ".sql", ".cff")
ALLOWED = set()
ROOTS = ("papers", "catalogue", "tools", "tests", "docs", "out", "eval", "test_eval", "standards",
         "search", "release", "v1_frozen", ".github")
SPAN = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
TOOLCMD = re.compile(r"\b(tools/[A-Za-z0-9_]+\.(?:py|sh))\b([^\n`;&|]*)")


def exists(root, p):
    p = p.rstrip("/,.;:)")
    if p in ALLOWED:
        return True
    if not p or p.startswith(("/", "~", "http", "$")) or "://" in p:
        return True
    if any(c in p for c in "<>{}$"):  # placeholder: check the static prefix only
        p = re.split(r"[<>{}$]", p)[0].rstrip("/")
        return not p or os.path.exists(os.path.join(root, p))
    if "*" in p:
        return bool(glob.glob(os.path.join(root, p)))
    return os.path.exists(os.path.join(root, p))


def pathlike(tok):
    tok = tok.strip().rstrip("/,.;:)")
    if tok.startswith(("-", "/", "~", "http")) or " " in tok:
        return False
    if tok.startswith(ROOTS) and ("/" in tok):
        return True
    return "/" not in tok and tok.endswith(EXT) and re.match(r"^[A-Za-z0-9_.-]+$", tok) and tok[0].isupper()


def flags_of(root, tool):
    try:
        src = open(os.path.join(root, tool), encoding="utf-8").read()
    except OSError:
        return None
    return set(re.findall(r"""["'](--[A-Za-z0-9][\w-]*)["']""", src))


def check(root, rel):
    errs = []
    text = open(os.path.join(root, rel), encoding="utf-8").read()
    chunks = [m.group(1) for m in SPAN.finditer(text)] + [m.group(1) for m in FENCE.finditer(text)]
    for ch in chunks:
        for tok in re.split(r"[\s=|]+", ch):
            if pathlike(tok) and not exists(root, tok):
                errs.append("%s: dead path %s" % (rel, tok))
        for m in TOOLCMD.finditer(ch):
            fl = flags_of(root, m.group(1))
            if fl is None:
                continue
            for f in re.findall(r"(?<!\S)(--[A-Za-z0-9][\w-]*)", m.group(2)):
                if f not in fl and f != "--help":
                    errs.append("%s: %s has no flag %s" % (rel, m.group(1), f))
    return errs


# ---- quoted benchmark numbers ---------------------------------------------------------------------
RECEIPT = "test_eval/test_run_v2.0.1.json"
LATENCY = "test_eval/cold_latency_TEST.json"
GATES = "out/gates_v2.0.1.json"
SYSTEMS = (("unbudgeted", "v1-unbudgeted"), ("b1", "b1"), ("v1", "v1"), ("v2.0.1", "v2"), ("math-router", "v2"))
METRIC_COLS = {"r@1": "recall_at_1", "r@5": "recall_at_5", "mrr": "mrr", "ndcg@5": "ndcg_at_5"}


def load(root, rel):
    try:
        return json.load(open(os.path.join(root, rel), encoding="utf-8"))
    except (OSError, ValueError):
        return None


def num(cell):
    m = re.fullmatch(r"\**\s*(-?\d[\d,]*(?:\.\d+)?)\s*\**", cell.strip())
    return None if not m else (float(m.group(1).replace(",", "")), len(m.group(1).split(".")[1]) if "." in m.group(1) else 0)


def close(true, val, dec):
    return true is not None and abs(true - val) <= 0.5 * 10 ** (-dec) * 1.0001


def hit_rates(root, rec):
    """Share of answerable queries with at least one relevant paper (grade >= 2) in the top 1 / top 5, per system."""
    bench = {}
    try:
        for line in open(os.path.join(root, "test_eval/bench_test_graded.jsonl"), encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                bench[r["qid"]] = r
    except OSError:
        return {}
    out = {}
    for name, sysd in rec["systems"].items():
        h1 = h5 = n = 0
        for p in sysd["per_query"]:
            q = bench.get(p["qid"])
            if not q or not q["answerable"]:
                continue
            rel = {g["id"] for g in q["gold"] if g["grade"] >= 2}
            n += 1
            h1 += bool(rel & set(p["ids"][:1]))
            h5 += bool(rel & set(p["ids"][:5]))
        out[name] = {"hit@1": h1 / n if n else None, "hit@5": h5 / n if n else None}
    return out


def truth(root):
    rec = load(root, RECEIPT)
    if not rec:
        return None
    t = {}
    for name, sysd in rec["systems"].items():
        m = sysd["metrics"]
        q = dict(m["quality"])
        q.update({k: v for k, v in hit_rates(root, rec).get(name, {}).items()})
        q.update({"p50": m["answer_bytes"]["p50"], "max": m["answer_bytes"]["max"], "share": m["answer_bytes"]["share_le_2000"]})
        q.update({"abstain_" + k: v for k, v in m["abstain"].items()})
        t[name] = q
    return t


def system_of(label):
    low = label.lower()
    for key, name in SYSTEMS:
        if key in low:
            return name
    return None


def check_numbers(root, rel, text, t, lat, gates, hashes):
    errs = []
    lines = text.splitlines()
    # 1) metric tables: header row names the columns, the first cell of each row names the system
    for i, line in enumerate(lines):
        if not line.startswith("|") or "R@1" not in line:
            continue
        hdr = [c.strip().lower() for c in line.strip().strip("|").split("|")]
        for row in lines[i + 2:]:
            if not row.startswith("|"):
                break
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            sysname = system_of(cells[0])
            if not sysname or sysname not in t:
                continue
            for h, c in zip(hdr[1:], cells[1:]):
                key = None
                if h in METRIC_COLS:
                    key = METRIC_COLS[h]
                elif h in ("hit@1", "hit@5"):
                    key = h
                elif h.startswith("abstention f1"):
                    key = "abstain_f1"
                elif h.startswith("share"):
                    key = "share"
                pairs = []
                if key:
                    pairs = [(key, c)]
                elif "p50" in h and "max" in h and "/" in c:
                    pairs = [("p50", c.split("/")[0]), ("max", c.split("/")[1])]
                elif "p50" in h:
                    pairs = [("p50", c)]
                elif "max" in h:
                    pairs = [("max", c)]
                for k, cell in pairs:
                    v = num(cell)
                    if v is None:
                        continue
                    if not close(t[sysname].get(k), v[0], v[1]):
                        errs.append("%s: table value %s for %s %s differs from %s (receipt %s)" % (rel, cell.strip(), sysname, h, t[sysname].get(k), RECEIPT))
    # 2) phrases: "<metric> <number>" must equal that metric of some system in the receipt
    metrics = {"R@1": "recall_at_1", "R@5": "recall_at_5", "MRR": "mrr", "nDCG@5": "ndcg_at_5", "precision": "abstain_precision",
               "recall": "abstain_recall", "F1": "abstain_f1"}
    for m in re.finditer(r"(?<![\w@])(R@1|R@5|MRR|nDCG@5|precision|recall|F1)(?:\s+is|\s+of|\s+)\s*(\d\.\d+)(?![\d.]*%)", text):
        v = num(m.group(2))
        if not any(close(s.get(metrics[m.group(1)]), v[0], v[1]) for s in t.values()):
            errs.append("%s: %s %s matches no system in %s" % (rel, m.group(1), m.group(2), RECEIPT))
    for m in re.finditer(r"(?<![\w@])(R@1|R@5|precision|recall)\s+(?:is\s+)?(\d+(?:\.\d+)?)%", text):
        v = float(m.group(2)) / 100
        k = metrics[m.group(1)]
        if not any(close(s.get(k), v, 2 if "." not in m.group(2) else 4) for s in t.values()):
            errs.append("%s: %s %s%% matches no system in %s" % (rel, m.group(1), m.group(2), RECEIPT))
    for m in re.finditer(r"\b(p50|max)\s+(\d[\d,]*)\b(?!\.\d)(?!\s*ms)", text):
        v = float(m.group(2).replace(",", ""))
        if not any(s.get(m.group(1)) == v for s in t.values()):
            errs.append("%s: bytes %s %s matches no system in %s" % (rel, m.group(1), m.group(2), RECEIPT))
    if lat:
        for m in re.finditer(r"p50\s+(\d+\.\d+)\s*ms", text):
            if not any(abs(lat[k]["p50"] - float(m.group(1))) <= 0.051 for k in ("v1", "v2") if k in lat):
                errs.append("%s: latency p50 %s ms matches no system in %s" % (rel, m.group(1), LATENCY))
    if gates:
        for m in re.finditer(r"\b(\d+)\s+(?:router |release )?gates\b", text):
            if int(m.group(1)) != gates["total"]:
                errs.append("%s: %s gates quoted, %s has %s" % (rel, m.group(1), GATES, gates["total"]))
    for m in re.finditer(r"\b[0-9a-f]{16,64}\b", text):
        if not any(h.startswith(m.group(0)) for h in hashes):
            errs.append("%s: hash %s... matches no shipped hash" % (rel, m.group(0)[:16]))
    return errs


def known_hashes(root, rec):
    hs = set()
    man = load(root, "out/index/manifest.json") or {}
    if man.get("index_sha256"):
        hs.add(man["index_sha256"])
    try:
        hs.add(hashlib.sha256(open(os.path.join(root, "out/params.json"), "rb").read()).hexdigest())
    except OSError:
        pass
    for k in ("bench_sha256", "freeze_sha256", "index_sha256", "params_sha256"):
        if rec and rec.get(k):
            hs.add(rec[k])
    return hs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    files = sorted({os.path.relpath(f, root) for pat in DOCS for f in glob.glob(os.path.join(root, pat))})
    errs = []
    t = truth(root)
    lat = load(root, LATENCY)
    gates = load(root, GATES)
    hashes = known_hashes(root, load(root, RECEIPT))
    for rel in files:
        errs += check(root, rel)
        if t:
            errs += check_numbers(root, rel, open(os.path.join(root, rel), encoding="utf-8").read(), t, lat, gates, hashes)
    errs = sorted(set(errs))
    for e in errs:
        print(e)
    print("claims_check: %d files, %d dead claims" % (len(files), len(errs)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
