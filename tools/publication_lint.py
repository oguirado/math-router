#!/usr/bin/env python3
"""Generic publication lint for a public checkout: no private policy, no network, standard library only.

Usage: python3 -I tools/publication_lint.py [ROOT]
Errors (exit 1): absolute home-directory paths, e-mail addresses outside Contact.md, private-key headers,
well-known credential token shapes. Warnings (exit 0): file names that are not plain ASCII English words.
Findings print the rule, the repository-relative file and the line number, never the matched text.
This is separate from the router gates (tools/gates_v2.py) and from the maintainer's release scan
(tools/release_gate.py, which needs an externally supplied policy).
"""
import os
import re
import sys

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}
MAX_BYTES = 16_000_000
EMAIL_HOME = "Contact.md"
EMAIL_OK = re.compile(r"(@users\.noreply\.github\.com|@example\.(com|org|net)|^noreply@)", re.I)

# Patterns are assembled from pieces so that this file does not trip the rules it implements.
_ROOTS = "|".join(("ho" + "me", "Us" + "ers", "ro" + "ot"))
RULES = [
    ("home-path", re.compile(r"(?<![\w.\\])/(?:%s)/[\w.-]+" % _ROOTS)),
    ("home-path", re.compile(r"\b[A-Za-z]:\\+Us" + r"ers\\+[\w.-]+", re.I)),
    ("private-key", re.compile("-----BEGIN (?:[A-Z]+ )?PRIV" + "ATE KEY")),
    ("token", re.compile(r"\b(?:AK" + r"IA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|xox[baprs]-[A-Za-z0-9-]{10,})")),
]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
# Words that mark a non-English file name (checked on lower-case name parts).
NON_ENGLISH = {"catalogo", "guia", "leeme", "contacto", "licencia", "informe", "resumen", "borrador", "prueba",
               "pruebas", "ejemplo", "entrada", "salida", "ayuda"}


def files_under(root):
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for n in sorted(names):
            yield os.path.join(base, n)


def read_text(path):
    try:
        if os.path.islink(path) or os.path.getsize(path) > MAX_BYTES:
            return None
        data = open(path, "rb").read()
    except OSError:
        return None
    if b"\0" in data:
        return None
    return data.decode("utf-8", errors="replace")


def lint(root):
    errors, warnings = [], []
    for path in files_under(root):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        stem = os.path.basename(rel).lower()
        parts = set(re.split(r"[^a-z]+", stem))
        if not rel.isascii() or parts & NON_ENGLISH:
            warnings.append(("file-name", rel, 0))
        text = read_text(path)
        if text is None:
            continue
        for no, line in enumerate(text.splitlines(), 1):
            for rule, rx in RULES:
                if rx.search(line):
                    errors.append((rule, rel, no))
            if rel != EMAIL_HOME:
                for m in EMAIL.finditer(line):
                    if not EMAIL_OK.search(m.group(0)):
                        errors.append(("email", rel, no))
    return sorted(set(errors)), sorted(set(warnings))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = os.path.abspath(argv[0] if argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    errors, warnings = lint(root)
    for rule, rel, no in warnings:
        print("warning %s %s" % (rule, rel))
    for rule, rel, no in errors:
        print("error %s %s:%d" % (rule, rel, no))
    print("publication_lint: %d errors, %d warnings" % (len(errors), len(warnings)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
