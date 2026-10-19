"""Check that file paths, tools, flags and workflows named in the docs exist in the tree.

Usage: python3 -I tools/claims_check.py [--root DIR]
Exit 0: every claim resolves. Exit 1: at least one dead claim (listed on stdout).
Stdlib only. Scans backticked spans and fenced code blocks of the top-level docs.
"""
import argparse
import glob
import os
import re
import sys

DOCS = ["README.md", "ARCHITECTURE.md", "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md",
        "CHANGELOG.md", "llms.txt", "docs/*.md", "catalogue/README.md"]
EXT = (".py", ".sh", ".md", ".json", ".jsonl", ".tsv", ".yml", ".yaml", ".txt", ".sql", ".cff")
# Reference mount path of the router protocol; it is described, not shipped.
ALLOWED = {"catalogue/router"}
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    files = sorted({os.path.relpath(f, root) for pat in DOCS for f in glob.glob(os.path.join(root, pat))})
    errs = []
    for rel in files:
        errs += check(root, rel)
    errs = sorted(set(errs))
    for e in errs:
        print(e)
    print("claims_check: %d files, %d dead claims" % (len(files), len(errs)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
