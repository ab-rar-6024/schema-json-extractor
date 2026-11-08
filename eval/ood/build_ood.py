"""Assemble and validate the independent eval set.

    python -I build_ood.py        # writes ood_cases.json next to this file

Checks every answer key against (a) its own schema and (b) the text, using the same
groundedness audit the training data went through, so an error in the answer key shows up
here instead of being mistaken for a model error.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "data", "gen"))

import make_cases      # noqa: E402  (defines helpers and cases 1-4)
import cases_b         # noqa: E402,F401  (registers more cases on import)
import cases_c         # noqa: E402,F401
import audit           # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402

CASES = make_cases.CASES


def count(o):
    if isinstance(o, dict):
        return sum(count(v) for v in o.values())
    if isinstance(o, list):
        return sum(count(v) for v in o)
    return 1


def main():
    ids = set()
    schema_errors = ungrounded = 0
    for c in CASES:
        assert c["id"] not in ids, "duplicate id " + c["id"]
        ids.add(c["id"])
        errs = list(Draft202012Validator(c["schema"]).iter_errors(c["expected"]))
        if errs:
            schema_errors += 1
            print("SCHEMA      %-16s %s" % (c["id"], errs[0].message[:120]))
        flagged = []
        audit.walk(c["expected"], c["text"], c["text"].lower(), [], flagged)
        for path, val in flagged:
            ungrounded += 1
            print("UNGROUNDED  %-16s %s = %r" % (c["id"], path, val))

    out = os.path.join(HERE, "ood_cases.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(CASES, f, indent=1, ensure_ascii=False)

    tags = {}
    for c in CASES:
        for t in c["tags"]:
            tags[t] = tags.get(t, 0) + 1
    nulls = 0

    def count_nulls(o):
        if isinstance(o, dict):
            return sum(count_nulls(v) for v in o.values())
        if isinstance(o, list):
            return sum(count_nulls(v) for v in o)
        return 1 if o is None else 0
    nulls = sum(count_nulls(c["expected"]) for c in CASES)
    print("\n%d cases | %d answer-key fields (%d expected null) | %d schema errors | "
          "%d ungrounded" % (len(CASES), sum(count(c["expected"]) for c in CASES), nulls,
                             schema_errors, ungrounded))
    print("tags:", dict(sorted(tags.items())))
    print("injection cases with a target field:",
          sum(1 for c in CASES if c["inject_fields"]))
    print("wrote", out)
    return 1 if schema_errors else 0


if __name__ == "__main__":
    sys.exit(main())
