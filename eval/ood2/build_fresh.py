"""Assemble and validate the FRESH eval set (never used for any design decision).

    python build_fresh.py   # writes ood_cases_fresh.json
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "data", "gen"))

import core2                # noqa: E402
import cases_a              # noqa: E402,F401
import cases_b              # noqa: E402,F401
import audit                # noqa: E402
import core                 # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402

CASES = core2.CASES
ids = set()
bad = ungrounded = 0
for c in CASES:
    assert c["id"] not in ids, c["id"]
    ids.add(c["id"])
    errs = list(Draft202012Validator(c["schema"]).iter_errors(c["expected"]))
    if errs:
        bad += 1
        print("SCHEMA", c["id"], errs[0].message[:100])
    flagged = []
    audit.walk(c["expected"], c["text"], c["text"].lower(), [], flagged)
    for path, val in flagged:
        ungrounded += 1
        print("UNGROUNDED", c["id"], path, repr(val))


def leaves(o):
    if isinstance(o, dict):
        return sum(leaves(v) for v in o.values())
    if isinstance(o, list):
        return sum(leaves(v) for v in o)
    return 1


def nulls(o):
    if isinstance(o, dict):
        return sum(nulls(v) for v in o.values())
    if isinstance(o, list):
        return sum(nulls(v) for v in o)
    return 1 if o is None else 0


# domains must not overlap set 1
old = set(c["id"] for c in json.load(open(os.path.join(HERE, "..", "ood", "ood_cases.json"),
                                          encoding="utf-8")))
print("id overlap with set 1:", sorted(old & ids))

# leak check against v4 training attack lines + set-1 attack lines (4-grams)
def grams(t, n=4):
    w = re.findall(r"[a-z0-9_']+", t.lower())
    return set(tuple(w[i:i + n]) for i in range(len(w) - n + 1))


tpl = grams(" ".join(core.NULL_TEMPLATES + core.OVERRIDE_TEMPLATES + core.GENERIC_V4))
mine = set()
for c in CASES:
    if "injection" in c["tags"]:
        mine |= grams(c["text"].split("\n")[-1])
print("4-grams shared between fresh attack lines and v4 attack templates:",
      sorted(" ".join(g) for g in (mine & tpl)))

with open(os.path.join(HERE, "ood_cases_fresh.json"), "w", encoding="utf-8") as f:
    json.dump(CASES, f, indent=1, ensure_ascii=False)
tags = collections.Counter(t for c in CASES for t in c["tags"])
print("cases %d | fields %d | expected-null %d | schema errors %d | ungrounded %d"
      % (len(CASES), sum(leaves(c["expected"]) for c in CASES),
         sum(nulls(c["expected"]) for c in CASES), bad, ungrounded))
print(dict(tags))
