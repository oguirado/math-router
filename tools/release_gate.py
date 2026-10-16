#!/usr/bin/env python3
r"""Read-only publication lint (G-PUBLIC). Findings never contain matched text or file names.
Adapted from the round-two release gate: the credential token regex is case-sensitive; path patterns run on
text whose math ($...$, $$...$$, \(...\), \[...\]) and LaTeX commands are masked, so "\\y\to x" inside a
display and maps such as "$T:\Sigma\to D$" are not paths, while file-scheme URIs and lower-case drive paths
with forward slashes are; strong private roots (home, root and Users directories, file-scheme URIs) are
checked on the unmasked text too.
Base64 runs of 512+ characters are found anywhere in a line. The language heuristic also runs on
paragraphs (consecutive non-blank lines, JSON "\n" escapes decoded). Deny rules may be case-sensitive:
tool-invocation rules match lower-case identifiers only, never ordinary mathematics (Newton's method)."""

import argparse
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import unicodedata


SCHEMA = "pm.release-scan.v1"
SCANNER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
# Generated from a reviewed private inventory; no plaintext identifiers shipped.
BUILTIN_DENY = []
SOURCE_LICENSE_SHA256 = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
SENSITIVE_NAMES = {"operator.token", "launch.token", "auth.json"}
BINARY_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pdf", ".zip", ".gz", ".png", ".jpg", ".jpeg", ".webp", ".woff", ".so", ".pyc"}
SOURCE_SUFFIXES = {".tex", ".lean"}
PATH_RE = re.compile(r"(?<![\w:/.])/(?:[\w.~+-]+/)+[\w.~+-]*|(?<![\w:/.])/(?:home|root|Users|tmp|etc|var|opt|srv)(?=$|[\s'\"`])|(?<!\\)\\\\[\w.-]+\\[\w.$-]+"
                     r"|(?i:\bfile:/{1,3})[^\s'\"`<>]*")
# Operator 2026-10-14 (PM-189.1): a literal scratch path under the root tmp dir (ONE component, `tmp` + name) quoted from a source command is not private.
# Opt-in (--allow-tmp-literal) for the assembled public tree only: each paper already passed the source-aware per-paper G-PUBLIC
# (a tmp-dir line is WARN only when it is a verbatim source quotation, FAIL otherwise), which the tree scan cannot re-check.
TMP_OK_RE = re.compile("/" + "tmp" + r"/[\w.~+-]+")  # built in pieces: the scanner ships in the public tree and scans itself
ALLOW_TMP_LITERAL = False


LETTERS2_RE = re.compile(r"[A-Za-z]{2}")


def math_like(g):
    """Promotion 7 adjudication (2026-10-15, 5 tree-scan false positives): a slash 'path' whose FIRST component has no run of
    two letters is arithmetic or code ("/6+w/3+", "/2+1/6", "/n-9/n-edge"); a UNC 'share' whose host is one character is a
    LaTeX line break before a command ("\\\\p\\nmid"). Real roots (/opt/x, /data/y, \\\\server\\share) keep matching;
    /home, /root, /Users and file: stay caught by STRONG_PATH_RE regardless."""
    if g.startswith("/"):
        return not LETTERS2_RE.search(g[1:].split("/", 1)[0])
    if g.startswith("\\\\"):
        return len(g[2:].split("\\", 1)[0]) < 2
    return False


def path_hit(text):
    """First PATH_RE match, skipping single-component tmp-dir paths when ALLOW_TMP_LITERAL is on and math/code look-alikes."""
    for m in PATH_RE.finditer(text):
        if ALLOW_TMP_LITERAL and TMP_OK_RE.fullmatch(m.group(0)):
            continue
        if math_like(m.group(0)):
            continue
        return m
    return None


def drive_hit(text):
    """DRIVE_RE, except LaTeX degree notation "[L:\\Qp]" (a one-component 'drive path' wrapped in square brackets)."""
    for m in DRIVE_RE.finditer(text):
        if m.start() > 0 and text[m.start() - 1] == "[" and text[m.end():m.end() + 1] == "]" and not re.search(r"[\\/].*[\\/]", m.group(0)):
            continue
        return m
    return None


# Never legitimate in a public paper, even inside math: checked on the unmasked line.
STRONG_PATH_RE = re.compile(r"(?i:\bfile:/{1,3})|(?<![\w.])/(?:home|root|Users)/[\w.~+-]+")
# Drive-letter paths are matched on masked text: "$T:\Sigma\to D$" is a map, not a path. An upper-case drive
# takes either separator; a lower-case drive needs forward slashes and two components ("s:\n" escapes are code).
DRIVE_RE = re.compile(r"\b[A-Z]:[\\/][A-Za-z0-9_-][\w. -]*(?:[\\/][\w. -]+)*|\b[a-z]:/[\w.~-]+(?:/[\w.~ -]+)+")
MATH_MASK_RE = re.compile(r"\$\$.*?\$\$|(?<!\\)\$[^$]*?(?<!\\)\$|\\\(.*?\\\)|\\\[.*?\\\]")
# Display math that spans lines is masked over the whole text first (bounded span so a stray $$ cannot hide a file).
# A $$ display never crosses an empty line or a pipe-table row: an unclosed $$ (a truncated table cell) must not
# flip the pairing of every later display and expose their bodies as text.
MATH_BLOCK_RE = re.compile(r"\$\$(?:(?!\$\$|\n\n|\|[ \t]*\n[ \t]*\|).){0,20000}?\$\$|\\\[(?:(?!\\\]).){0,20000}?\\\]|\\begin\{(equation|align|gather|multline|eqnarray)\*?\}.{0,20000}?\\end\{\1\*?\}", re.S)
# Common LaTeX command names are masked outside math too ("\\y\to x" in a text-mode array is not a UNC path);
# unknown names are kept, so drive paths and UNC shares with ordinary names are still paths.
TEX_CMD_RE = re.compile(r"\\(?:to|frac|dfrac|tfrac|mathrm|mathbf|mathcal|mathbb|mathfrak|operatorname|infty|alpha|beta|gamma|delta|epsilon|varepsilon|lambda|mu|nu|sigma|tau|phi|varphi|psi|omega|rho|theta|pi|xi|eta|zeta|kappa|chi|Gamma|Delta|Lambda|Sigma|Phi|Psi|Omega|Theta|sum|prod|int|lim|liminf|limsup|sup|inf|max|min|log|exp|sin|cos|le|leq|ge|geq|ne|neq|in|subset|subseteq|cup|cap|times|cdot|ldots|cdots|dots|quad|qquad|left|right|big|Big|text|textbf|textit|emph|label|ref|eqref|cite|hline|item|newline|underline|overline|substack|partial|nabla|mid|setminus|forall|exists|colon|vert|Vert|langle|rangle|hat|tilde|bar|vec|sqrt|binom|over|nonumber|notag|tag|qed|hspace|vspace|mapsto|rightarrow|leftarrow|Rightarrow|Leftarrow|iff|implies)(?![A-Za-z])")
# Private piece identifiers ("s" "cr-" family), matched case-sensitively.
PIECE_RE = re.compile(r"(?<![\w-])" + "s" + r"cr-[a-z0-9]+(?:-[a-z0-9]+)+\b")
# private working-file references copied from harvest context: a file name with a colon and line range, and catalogue node ids
PRIVREF_RE = re.compile(r"(?<![\w/.-])[A-Za-z][\w-]*\.(?:md|json|jsonl|py|txt|tsv):\d+(?:-\d+)?\b|\b(?:SW|HB|CAT)-\d{4}\b")
PORTABLE_SHEBANG = "#!" + "/usr" + "/bin" + "/env python3"
EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
TOKEN_RE = re.compile(r"\b(?:sk-(?![a-z]{2,24}(?:-[a-z]{1,24})*(?![A-Za-z0-9_-]))[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,})\b|\bBearer\s+[A-Za-z0-9._-]{16,}|-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")
# Case-sensitive on purpose: upper-case "SK-" Sherrington-Kirkpatrick labels in papers are not credentials. Operator GO 2026-10-15:
# an "sk-" followed only by short lower-case words (a slug: "sk-autocorrelations", "sk-free-energy-limiting-law") is not a key;
# real keys carry digits / upper case / long random segments and stay matched (see the slug fixture in the gate tests).
ASSIGN_RE = re.compile(r"[\"']?(?:password|api[_-]?key|access[_-]?token|secret)[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_./+-]{12,})", re.I)
CAPSULE_RE = re.compile(r"data:(?:application|image)/[^;,]+;base64|(?<![A-Za-z0-9+/])(?=[0-9+/]*[A-Za-z])[A-Za-z0-9+/]{512,}={0,2}")  # a pure decimal integer is mathematics, not a capsule (PM-238.8: 598 digits)
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
JSON_ESCAPE_RE = re.compile(r'\\(["\\/bfnrt]|u[0-9a-fA-F]{4})')
JSON_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": " ", "f": " ", "n": "\n", "r": " ", "t": "\t"}
# Letter-like mathematical symbols (double-struck N, script l, Fraktur, modifier and sub/superscript letters)
# are notation, not a script; Greek letters count only inside a run of three or more (a Greek word).
MATH_LETTER_NAMES = ("DOUBLE-STRUCK", "MATHEMATICAL", "SCRIPT", "BLACK-LETTER", "MODIFIER LETTER", "SUBSCRIPT", "SUPERSCRIPT")
GREEK_RUN_RE = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]{3,}")
LANGUAGE_RULES = {
  "french": [
    [
      "098e337b8d4e27708251dff0447bf9b8d701a1995726b115555daf7f1bcaa80a",
      "0b135e8de8f42b4baddb5e580400b8c2dc56f9204758314c2be7019aa9d8d98a",
      "52597892af72166c5a1b5a1ef53f51beb6de370dab847be9026fb145caf1c213",
      "61098a4bf2a5e216533e5f2994d8f290308b310f2efa046548a96302afe412ea",
      "7b24c1ad239d4a6b2c73716e122644f4d45329a71d01c9437f033381e8832fe4",
      "7b5454f75089acf2693bc531725160e31ab0a1a34bcba17afb98109b194d049b",
      "a96b5cac90bfd6200319f968cdb34c1311a98b19b01a246432e7e2767f17387f",
      "b6cf348bc9b1a71d9db0ce76c3b2645a3d57e2a6b2119b58a236adbef5e05c43",
      "b737ca7ee563ae80e457bb3d1dfe64edd2b4c015a8f88b6f87d5c113b68897fd",
      "c57b7501cd843672550c711a346dd93e9bdc2c97a640874d54b4c9cf4b12ee81",
      "ed29bcecc78d7ffb672491c9440a4159f9aa81182f5b1fc32726a96ec10e0392"
    ],
    [
      "04c018a2198d74ae782f02afb9159f0529d0fe735f4ff6e3971c502bb2b4534f",
      "13a3c6498bb6ce3a16a8e2b089016b7d91e79410de4ceec983e8c2042876f989",
      "1941f6309e3ee5c0b220eede723d06db30a34e65a0f64a5c26ff08214e6f3702",
      "2652d4b2f3032117e54d188032efdc62e7ad73e63344310a6541b799d68d0485",
      "2b709b2ed05facb10aa5aae726e71144738876c51b5e124a8ad4104eeebee43f",
      "326ec838558bf00fcfb3c3445fca9912fa346d63def9834f71bad812427b0b5d",
      "47af944d945116a36e7260b2431e865f73b4ba3c70a79e327728e53e6524fe96",
      "a1e95e8d498edecba29f57dadb14c7b44c7951bd1c57f02761ee80217ccb7819",
      "de7baed9f330dc1b969b8aeb0ec29ee7c40f3f14a58286017169002b061d7510"
    ]
  ],
  "german": [
    [
      "0a7cb27e52927eacabbb7ecc738b0fea50b3967945257c43a67eb753cb465bd0",
      "1da8321dcc9a00abe48f2d3bab1786eebbdedc363ccbac3de1a649c03efe47fd",
      "4c3c3030130a4a1b174aa4b0eda1ab26f1ac0c3b88d8fb30e015e3172f356810",
      "5050d80d22ecd471ea55df7034042c1e041341ff4066e7f6ff38e20b720df8ea",
      "6a8cd96a4b778934f9ef7673a09b59c0bb5475442ccbc491bb8e7862318f2302",
      "78198e7ab262449ad56e4ca48e10a36f98dda6fd5a377875dd7425afcca2312b",
      "856cc99d87343400dc05fe7d03fa666602a1d92c4fb0ee1f5ae2f0a5fb218eb8",
      "a42517945927c258f319d7eb4e70a438178fd18c66ad0951424553c0bb30f773",
      "a8d79f40ddb79de569d778f1c0b832f9cc266b32274b702cff4ba2b8a0dd1549",
      "be1130b77b9d58d66a21ef4b2c84cfb3ea182c69d071d4032df5b17829d703c6"
    ],
    [
      "23e125affa427a7cffd4969bcb4728c8fb42539ca38d7a9c951a10cf87198ff2",
      "35487809a6ee83cc250ebf60f0ff133547d177394c4b8ab9927a7c3be4e7f866",
      "7b656824e2e6d148a8f4d5ea8973b09c4f62b28cd861a2d9f509f44259b0722b",
      "9508201864adb962ccc168332be22bee4647903ef126aa63456718329b470752",
      "d58b28ffa5c2f8f6c5165d8624e804a4328d967624a55942b93370df675783ca",
      "e964d0402084ce52e57ba90dd0cc269953cf1204454d8c038c11d24a4af326f1",
      "f5167aa5b96fc55df7746d2ae835330c95e04f0eb230c31fc1a494e53f6954e8"
    ]
  ],
  "italian": [
    [
      "1143da2bc54c495c4be31d3868785d39ffdfd56df5668f0645d8f14d47647952",
      "161f0e5ed45f6d514dc23e22a4a9cadda05a3bb9b2c1661612301c6116141f10",
      "187f4e2a5d12a774edfbab5fd7bb5512dc4eb0deb1c0397153b2084514b2dd56",
      "21425924b1a9a5d8768eb48b6ad03d4d4bfb736df6fa8a0164c0aaaed910a8d1",
      "250fccd5f5f76c7c866647d737ea3af37a8404744a5fc7c2628245194242304d",
      "374b3a2a8b4003dd15be4fbb2cc632da719f627316327d0fc8fd8bd865e139cb",
      "7294e1afc53ae7fe8b7d780125f41d1e9918b86df5c8f3b92aae800aab6b9251",
      "9294ab38039f60d2ec53822fb46b52c663af7ea478f4d17bf43da44ede5e166c",
      "a0fb903525dc10dccaa4bd72bed4fe5b24ae8346b8a7343edce84172feb7085a",
      "b427c3dec9045990213ccc3dbffbdf189e75c7ce18e1a86ed7c4fe9a2db5d627"
    ],
    [
      "2f75226b03f6b8395e9cb6f5840bbd0cb8a817f8ec948444352d2f1e9c6958f9",
      "3a2b22a65bbe8602b2804aaa7b99feef5ff976ebd7f8f18ed0c6c75c60b0dff4",
      "cd1da35aac6989476c6b69987d8774ccf35401f8fbd7bbc1bcdeb5d229df952a",
      "dccaea52748612e61eb45869967ceb3be71abe8b0cf1e8f68fbfaedaf3b08de6",
      "e18338ad8f71649c1be07dc43b79c9d053057a1aaaa0cccd241030c20dbc4ad7",
      "e5515edad18f0a4a7be86ce018dd0e04c7b39dcd860d8eb3c520d42927b873f8",
      "e6c8b318b65a509cd07a2385d21ed0b13e84124b8a1466bf84a1dc59fe8d578e"
    ]
  ],
  "portuguese": [
    [
      "2d98c0c5592a747cd6dbae3976a1be83195053bef12495226c97961ea07cdc03",
      "71b4f3a3748cd6843c01e293e701fce769f52381821e21daf2ff4fe9ea57a6f3",
      "840a8dcfeae95966a870b0b5257997ce94cbc19dd979409d1671d2e93a9e0de6",
      "a1453f380fa9f1a08e84d4703e9c168fda1fb9a36976c41a03c8af842aa04ce5",
      "b3aa33b34e1b14e4cf3eded0cac6717a8385caa1e948448d0055e59eff4def69",
      "c1299854f2b209632ab22aeb848c24c2b02da4b37ecf93a830ee9c7f6f809924",
      "c57b7501cd843672550c711a346dd93e9bdc2c97a640874d54b4c9cf4b12ee81",
      "e604f8c97caaadb4c15db94f28d54802722aeba64e375071e4d1eeb1a3cc68fa",
      "e811eb7830249bae4b61145ae6e5f0933d7f890570d6ead6e78f89f04fd6aeb5",
      "f4bf9f7fcbedaba0392f108c59d8f4a38b3838efb64877380171b54475c2ade8"
    ],
    [
      "068b480e20b37bc2ea802a19b35b0100720e53636659109b3cc366e5fae81ac6",
      "21209597f685c8bef83dfa0b7cb389453074695a4f0ed6d6b6bca574a2d5d77f",
      "48b910466e425bb5816ed75a560d41af4a28e76b4976a08676a35328377e3edc",
      "7462b2ca03a6fb2205e57d73d805b94596e898ce83cec5028f80f23ca05ea008",
      "9cc50439b3aee8afb5b8a6bb206fd44c82abcff4eede668df401f17d982b3f39",
      "d1650fc85a3c8a468f4194779acff31c01df69a2875f1b14b54f782d276c9662",
      "e5515edad18f0a4a7be86ce018dd0e04c7b39dcd860d8eb3c520d42927b873f8",
      "f8671e672c0bf2dde27569b7843fbf6d3e120e4011c69e353ad5972e1aaaf3e3"
    ]
  ],
  "spanish": [
    [
      "02d5d0522a76608d64a5d329e13a2f8627e935efca8d77a73ca0f523a7410c7f",
      "0db9df7d8e7ff24ae5980d8862caf37b60f0e3ef9165630a8d64247c9d42cfd3",
      "1143da2bc54c495c4be31d3868785d39ffdfd56df5668f0645d8f14d47647952",
      "161f0e5ed45f6d514dc23e22a4a9cadda05a3bb9b2c1661612301c6116141f10",
      "2d98c0c5592a747cd6dbae3976a1be83195053bef12495226c97961ea07cdc03",
      "3d9ac7a050e12bdf2d1c5d0cbc6012c414b405a6ffb9c88a583117fa7a331f0b",
      "3ea6bc47a6277afef178e3a230f945fca1153690cafc7f61be2738f5abb5165f",
      "75e3090289e2955dfaecfe21eabbe80b7146ab62339454a3dcd1a0ca53111381",
      "a1453f380fa9f1a08e84d4703e9c168fda1fb9a36976c41a03c8af842aa04ce5",
      "b3aa33b34e1b14e4cf3eded0cac6717a8385caa1e948448d0055e59eff4def69",
      "b737ca7ee563ae80e457bb3d1dfe64edd2b4c015a8f88b6f87d5c113b68897fd",
      "c133cf8c40c407b3e1df8fd9c006a74f6f1d7c0e3e7a7408799c9ed2d7a6639e",
      "c57b7501cd843672550c711a346dd93e9bdc2c97a640874d54b4c9cf4b12ee81",
      "cb6e53541e37a1d6076e5b516510607a5f3af6c4c4d7f5ce7ac2ffbd18b340a2",
      "cccc68c7928e63feb966db96210f5f3b085f371800b6341b27001f8374076f2b",
      "d65c3e892354b17a4c032593974d46bc8732c6c0b1ce56edf0c95511d1749cf5"
    ],
    [
      "3340292fcf65c3a26b646a82989d04d8b680bee67b9aab516ac0622cdc3e80e0",
      "3a2b22a65bbe8602b2804aaa7b99feef5ff976ebd7f8f18ed0c6c75c60b0dff4",
      "3f6ab90de0bd1f2c5ba961efccf84f03023af2a8a2febf1d028a09eedad8deb7",
      "4a84e284cafad2b3f20c0bb7e13d02054f0aebbb3128cee83b6eb8d460b84b02",
      "56de46ffd775d275910cbd204fbe42b29c9ef5bd219394626d37d05b75f8f434",
      "6ab03c93de35ebf147214c9070a6a189e60a4db21d2a3261849354154707fa82",
      "6dc523794bc2406e26c62177ead2ea500ea9ccbebe118fb46681fae76dcb68bc",
      "809d598264033be8d901d7cd2859a487a04c9436cc4f5cc6cba0ea5f6a89e032",
      "8e7dbc5859cb6fa963da23c3650c792a632cc49e0a4040ea1e839097cfab470c",
      "b28ad89a06f3fb2c0ad08d066266b03b65df695e6d7fedfe0601846621bc2425",
      "c133cf8c40c407b3e1df8fd9c006a74f6f1d7c0e3e7a7408799c9ed2d7a6639e",
      "ce3ebf0e11e398513e44c5419dc4a97a459776ba99cf00fd6135a676c17c62d1",
      "e4bec56d7ae619740970381162f55a44cc0007317edeaf1f1504c3f5ff6a3ba9",
      "e7b1998badcf54f16fb68eb2a9c614dc05fbbd22e6b74d2d637abf839caa7e3b",
      "eb2c97a846a6e0bebc2fd8f1103fb48789b1867a396ffcf25520169b9cce2412",
      "ed0c4cfaf1d9903125fc546b2d0706ca501422c183b9d300730b4f24b294aaab",
      "f13f8e16a9f744f064a650c627756ef2f135ad445217a826f472e0c02f8ba89a"
    ]
  ]
}


@functools.lru_cache(maxsize=65536)
def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normal_words(value):
    if value.isascii():
        return WORD_RE.findall(value.casefold())
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Cf")
    return WORD_RE.findall(normalized)


def cased_words(value):
    if not value.isascii():
        value = unicodedata.normalize("NFKC", value)
        value = "".join(ch for ch in value if unicodedata.category(ch) != "Cf")
    return WORD_RE.findall(value)


def mask_math(text):
    """Blank math spans and LaTeX command names, keeping line structure."""
    keep = lambda m: re.sub(r"[^\n]", " ", m.group(0))
    return MATH_BLOCK_RE.sub(keep, text)


def json_unescape(value):
    """Decode JSON string escapes of one line ("\\\\" -> one backslash, "\\n" -> newline)."""
    return JSON_ESCAPE_RE.sub(lambda m: chr(int(m.group(1)[1:], 16)) if m.group(1)[0] == "u" else JSON_ESCAPES[m.group(1)], value)


def json_lines(name, text):
    """Line numbers (1-based) holding JSON text: every line of a .json/.jsonl file, the body of ```json fences in Markdown."""
    lines = text.splitlines()
    if name.endswith((".json", ".jsonl")):
        return set(range(1, len(lines) + 1))
    out, inside = set(), False
    for i, line in enumerate(lines, 1):
        if not inside and line.startswith("```json"):
            inside = True
        elif inside and line.startswith("```"):
            inside = False
        elif inside:
            out.add(i)
    return out


def non_latin_letters(value):
    """Letters of a non-Latin script, ignoring mathematical letter-like symbols and isolated Greek letters."""
    if value.isascii():
        return 0
    greek = sum(len(m.group(0)) for m in GREEK_RUN_RE.finditer(value))
    n = 0
    for ch in value:
        if not ch.isalpha() or ord(ch) <= 127:
            continue
        nm = unicodedata.name(ch, "")
        if "LATIN" in nm or "GREEK" in nm or any(k in nm for k in MATH_LETTER_NAMES):
            continue
        n += 1
    return n + greek


def mask_path_view(value):
    return TEX_CMD_RE.sub(" ", MATH_MASK_RE.sub(" ", mask_math(value)))


def fold_accents(value):
    if value.isascii():
        return value
    return "".join(ch for ch in unicodedata.normalize("NFKD", value) if not unicodedata.combining(ch))


def load_policy(path):
    if path is None:
        return [], None
    candidate = Path(path)
    parts = candidate.parts
    if any(p in SENSITIVE_NAMES or p.endswith(".key") for p in parts) or any(parts[i:i+2] == ("." + "bec" + "kett", "token") for i in range(len(parts)-1)):
        raise ValueError("sensitive_policy_file_not_opened")
    raw = candidate.read_bytes()
    data = json.loads(raw)
    if set(data) != {"schema", "reviewed", "deny"} or data["schema"] != "pm.release-policy.v1" or data["reviewed"] is not True or not data["deny"]:
        raise ValueError("unreviewed_or_empty_policy")
    for rule in data["deny"]:
        if set(rule) - {"case_sensitive"} != {"category", "words", "first_sha256", "phrase_sha256"} or rule.get("case_sensitive", False) not in (True, False):
            raise ValueError("invalid_policy_keys")
        if rule["category"] not in {"private_user", "private_host", "private_tool", "private_corpus", "private_project"} or type(rule["words"]) is not int or not 1 <= rule["words"] <= 12:
            raise ValueError("invalid_policy_rule")
        if any(not re.fullmatch(r"[a-f0-9]{64}", rule[k]) for k in ("first_sha256", "phrase_sha256")):
            raise ValueError("invalid_policy_hash")
    return data["deny"], hashlib.sha256(raw).hexdigest()


class Scan:
    def __init__(self, args, rules):
        self.args = args
        self.started = time.monotonic()
        self.findings = []
        self.seen_findings = set()
        self.files = 0
        self.text_files = 0
        self.bytes = 0
        self.errors = 0
        self.revision = hashlib.sha256()
        self.first = {}
        for rule in rules:
            self.first.setdefault(rule["first_sha256"], []).append(rule)
        self.repo_words = normal_words(args.repository_name or "")
        self.languages = {language: (frozenset(common), frozenset(distinctive)) for language, (common, distinctive) in LANGUAGE_RULES.items()}

    def bound(self):
        if time.monotonic() - self.started > self.args.deadline:
            raise ValueError("deadline_exceeded")
        if self.files > self.args.max_files or self.bytes > self.args.max_bytes or len(self.findings) >= self.args.max_findings:
            raise ValueError("scan_limit_exceeded")

    def finding(self, name, category, line=0):
        key = (name, category, line)
        if key in self.seen_findings:
            return
        self.seen_findings.add(key)
        self.findings.append({"file_id": digest(name), "category": category, "line": line})
        self.bound()

    def identifiers(self, name, value, line):
        words = normal_words(value)
        raw = None
        for i, word in enumerate(words):
            for rule in self.first.get(digest(word), ()):
                phrase = " ".join(words[i:i + rule["words"]])
                if digest(phrase) != rule["phrase_sha256"]:
                    continue
                if rule.get("case_sensitive"):
                    # tool identifiers are lower-case; "Newton potential" in a paper is mathematics
                    if raw is None:
                        raw = cased_words(value)
                    if len(raw) == len(words) and any(w != w.lower() for w in raw[i:i + rule["words"]]):
                        continue
                self.finding(name, rule["category"], line)
        if PIECE_RE.search(value):
            self.finding(name, "private_tool", line)
        if PRIVREF_RE.search(value):
            self.finding(name, "private_corpus", line)
        if self.repo_words and name.startswith("papers/") and name.endswith(".md"):
            n = len(self.repo_words)
            if any(words[i:i+n] == self.repo_words for i in range(len(words)-n+1)):
                self.finding(name, "release_repository_name_in_paper", line)
        return words

    def text(self, name, text):
        # Inspect all text, including comments, code, JSON values and escaped paths.
        views = [text]
        if re.search(r"\\u[0-9a-fA-F]{4}|\\/", text):
            views.append(re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), text).replace("\\/", "/"))
        jlines = json_lines(name, text)
        for view in dict.fromkeys(views):
            masked_lines = mask_math(view).splitlines()
            for line, value in enumerate(view.splitlines(), 1):
                self.bound()
                masked = masked_lines[line - 1] if line - 1 < len(masked_lines) else value
                if not value.isascii():
                    value = unicodedata.normalize("NFKC", value)
                    value = "".join(ch for ch in value if unicodedata.category(ch) != "Cf")
                    masked = unicodedata.normalize("NFKC", masked)
                masked = TEX_CMD_RE.sub(" ", MATH_MASK_RE.sub(" ", masked))
                for category, regex in (("absolute_path", PATH_RE), ("email", EMAIL_RE), ("credential", TOKEN_RE), ("encoded_capsule", CAPSULE_RE)):
                    if category == "absolute_path" and name.endswith(".py") and line == 1 and value == PORTABLE_SHEBANG:
                        continue
                    if category == "absolute_path" and line in jlines:
                        # JSON-escaped text ("\\\\to\\n" is LaTeX "\\to" plus a newline, not a UNC share): paths are
                        # matched on the decoded string, masked the same way; strong roots on both forms
                        dv = json_unescape(value)
                        dm = mask_path_view(dv)
                        hit = path_hit(dm) or drive_hit(dm) or STRONG_PATH_RE.search(value) or STRONG_PATH_RE.search(dv)
                    elif category == "absolute_path":
                        hit = path_hit(masked) or drive_hit(masked) or STRONG_PATH_RE.search(value)
                    else:
                        hit = regex.search(value)
                    if hit:
                        self.finding(name, category, line)
                if any(m.group(1).casefold() not in {"placeholder", "redacted_value", "example_value"} for m in ASSIGN_RE.finditer(value)):
                    self.finding(name, "credential_assignment", line)
                words = [fold_accents(w) for w in self.identifiers(name, value, line)]
                word_hashes = [digest(w) for w in words]
                word_set = set(word_hashes)
                for language, (common, distinctive) in self.languages.items():
                    if not word_set & distinctive:
                        continue
                    hits = sum(w in common or w in distinctive for w in word_hashes)
                    if len(word_set & distinctive) >= 1 and hits >= 3 and hits / max(1, len(words)) >= 0.12:
                        self.finding(name, "non_english_heuristic_" + language, line)
                if non_latin_letters(value) >= 12:
                    self.finding(name, "non_english_script_review", line)
        self.paragraph_language(name, text)

    def window_languages(self, words, size=25, need=3):
        """Languages with some window of `size` consecutive words holding >= `need` common-or-distinctive
        hits and at least one distinctive word."""
        hashes = [digest(fold_accents(w)) for w in words]
        out = set()
        for language, (common, distinctive) in self.languages.items():
            if not distinctive.intersection(hashes):
                continue
            hit = [h in common or h in distinctive for h in hashes]
            dis = [h in distinctive for h in hashes]
            run_h = run_d = 0
            for i in range(len(hashes)):
                run_h += hit[i]
                run_d += dis[i]
                if i >= size:
                    run_h -= hit[i - size]
                    run_d -= dis[i - size]
                if run_h >= need and run_d >= 1:
                    out.add(language)
                    break
        return sorted(out)

    def paragraph_language(self, name, text):
        # Wrapped prose (2-3 words per line, or JSON "\n" escapes) is judged over word windows that cross lines.
        view = text.replace("\\n", "\n")
        para, first = [], 0
        for line, value in enumerate(view.splitlines() + [""], 1):
            if value.strip():
                if not para:
                    first = line
                para.append(value)
                if len(para) < 200:
                    continue
            if len(para) >= 2:
                self.bound()
                for language in self.window_languages(normal_words(" ".join(para))):
                    self.finding(name, "non_english_heuristic_" + language, first)
            para = []

    def forbidden_name(self, name):
        parts = Path(name).parts
        return any(p in SENSITIVE_NAMES or p.endswith(".key") for p in parts) or any(parts[i:i+2] == ("." + "bec" + "kett", "token") for i in range(len(parts)-1))

    def file(self, name, size, mode, reader):
        self.files += 1
        self.bytes += size
        self.bound()
        self.text(name, name)
        if self.forbidden_name(name):
            self.finding(name, "sensitive_file_not_opened")
            self.errors += 1
            return
        if mode not in {"100644", "100755"}:
            self.finding(name, "non_regular_file")
            self.errors += 1
            return
        if Path(name).suffix.casefold() in BINARY_SUFFIXES | SOURCE_SUFFIXES:
            self.finding(name, "unsupported_public_payload")
            self.errors += 1
            return
        if size > self.args.max_file_bytes:
            self.finding(name, "oversized_unscanned_file")
            self.errors += 1
            return
        try:
            raw = reader()
            if len(raw) != size:
                raise ValueError("size_changed")
            if b"\0" in raw:
                raise ValueError("binary_content")
            text = raw.decode("utf-8-sig", errors="strict")
        except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
            self.finding(name, "unreadable_or_binary")
            self.errors += 1
            return
        self.text_files += 1
        self.revision.update(name.encode("utf-8") + b"\0" + hashlib.sha256(raw).digest())
        self.text(name, text)


def git(root, *args, timeout=20):
    return subprocess.run(["git", "-C", str(root), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout).stdout


def index_files(root, scan):
    raw = git(root, "ls-files", "--stage", "-z")
    entries = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        meta, name = record.split(b"\t", 1)
        mode, oid, stage = meta.decode("ascii").split()
        name = name.decode("utf-8", errors="strict")
        if stage != "0":
            raise ValueError("unmerged_index")
        if len(entries) >= scan.args.max_files:
            raise ValueError("file_limit_exceeded")
        entries.append((name, mode, oid))
    for name, mode, oid in sorted(entries):
        scan.bound()
        # The size check precedes reading each blob.
        size = int(git(root, "cat-file", "-s", oid))
        scan.file(name, size, mode, lambda oid=oid: git(root, "cat-file", "blob", oid))
    if raw != git(root, "ls-files", "--stage", "-z"):
        raise ValueError("index_changed_during_scan")
    return {name for name, _, _ in entries}


def tree_files(root, scan):
    names = set()
    def walk_error(error):
        raise ValueError("unreadable_directory")
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        scan.bound()
        rel = Path(directory).relative_to(root)
        if len(rel.parts) > 64:
            raise ValueError("depth_limit_exceeded")
        # Git object storage is transport metadata, never part of a release snapshot.
        dirs[:] = sorted(d for d in dirs if not (rel == Path(".") and d == ".git"))
        for d in list(dirs):
            target = Path(directory) / d
            if target.is_symlink():
                scan.finding(target.relative_to(root).as_posix(), "symlink_directory")
                scan.errors += 1
                dirs.remove(d)
        for filename in sorted(files):
            target = Path(directory) / filename
            name = target.relative_to(root).as_posix()
            names.add(name)
            info = target.lstat()
            mode = "100755" if info.st_mode & stat.S_IXUSR else "100644"
            if not stat.S_ISREG(info.st_mode):
                mode = "unsupported"
            def read_stable(target=target, info=info):
                fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | os.O_NONBLOCK)
                try:
                    current = os.fstat(fd)
                    if not stat.S_ISREG(current.st_mode) or (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns):
                        raise ValueError("file_changed")
                    with os.fdopen(fd, "rb", closefd=False) as stream:
                        data = stream.read(scan.args.max_file_bytes + 1)
                    after = os.fstat(fd)
                    if (after.st_size, after.st_mtime_ns) != (info.st_size, info.st_mtime_ns):
                        raise ValueError("file_changed")
                    return data
                finally:
                    os.close(fd)
            scan.file(name, info.st_size, mode, read_stable)
    return names


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--index", action="store_true", help="Inspect exact staged Git blobs.")
    parser.add_argument("--release", action="store_true", help="Require reviewed policy, repository identity and legal files.")
    parser.add_argument("--policy")
    parser.add_argument("--repository-name")
    parser.add_argument("--out")
    parser.add_argument("--allow-tmp-literal", action="store_true", help="Public tree of gated papers: allow one-component tmp-dir paths.")
    parser.add_argument("--deadline", type=float, default=240)
    parser.add_argument("--max-files", type=int, default=20000)
    parser.add_argument("--max-bytes", type=int, default=2_000_000_000)
    parser.add_argument("--max-file-bytes", type=int, default=16_000_000)
    parser.add_argument("--max-findings", type=int, default=200000)
    args = parser.parse_args(argv)
    global ALLOW_TMP_LITERAL
    ALLOW_TMP_LITERAL = bool(args.allow_tmp_literal)
    result = {"schema": SCHEMA, "scanner_sha256": SCANNER_SHA256, "mode": "git_index" if args.index else "working_tree", "status": "FAIL", "files": 0, "text_files": 0, "bytes_examined_or_blocked": 0, "findings": 0, "unscanned_or_blocked": 0, "categories": {}, "content_manifest_sha256": None, "policy_sha256": None, "samples": [], "errors": []}
    scan = None
    try:
        if min(args.deadline, args.max_files, args.max_bytes, args.max_file_bytes, args.max_findings) <= 0:
            raise ValueError("invalid_limits")
        if args.release and (not args.index or not args.policy or not normal_words(args.repository_name or "")):
            raise ValueError("release_preconditions_absent")
        root = Path(args.root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("root_not_directory")
        if args.release and Path(args.policy).resolve().is_relative_to(root):
            raise ValueError("private_policy_inside_release")
        rules, policy_sha = load_policy(args.policy)
        result["policy_sha256"] = policy_sha
        scan = Scan(args, BUILTIN_DENY + rules)
        names = index_files(root, scan) if args.index else tree_files(root, scan)
        if not names:
            raise ValueError("empty_tree")
        if args.release:
            if not {"LICENSE", "NOTICE"} <= names:
                raise ValueError("legal_files_absent")
            license_raw = git(root, "show", ":LICENSE")
            if hashlib.sha256(license_raw).hexdigest() != SOURCE_LICENSE_SHA256:
                raise ValueError("source_license_drift")
            if len(git(root, "show", ":NOTICE").strip()) < 80:
                raise ValueError("notice_incomplete")
        result["status"] = "PASS" if not scan.findings and not scan.errors else "FAIL"
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        # Do not expose system error text, paths, credentials or Git stderr.
        code = str(error) if isinstance(error, ValueError) and re.fullmatch(r"[a-z_]+", str(error)) else "scan_exception"
        result["errors"].append(code)
    if scan is not None:
        categories = {}
        for finding in scan.findings:
            categories[finding["category"]] = categories.get(finding["category"], 0) + 1
        result.update(files=scan.files, text_files=scan.text_files, bytes_examined_or_blocked=scan.bytes, findings=len(scan.findings), unscanned_or_blocked=scan.errors, categories=categories, content_manifest_sha256=scan.revision.hexdigest(), samples=scan.findings[:20])
    encoded = json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(encoded, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
