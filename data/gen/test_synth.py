"""Validate synthesised schemas by generating real examples through them.

A synthesised schema is only useful if every projected record validates against it,
so this drives the real build path rather than inspecting the schema statically.
"""
import random
import sys
import traceback

import catalog
import synth
from build import make_example
from domains import DOMAINS
from jsonschema import Draft202012Validator

PER_DOMAIN = int(sys.argv[1]) if len(sys.argv) > 1 else 6
EXAMPLES = int(sys.argv[2]) if len(sys.argv) > 2 else 12

rng = random.Random(11)
cat = catalog.build(DOMAINS)

made = ok = bad = 0
shapes = {}
failures = []

for dom in sorted(DOMAINS):
    schemas = synth.synth_for_domain(rng, dom, cat[dom], PER_DOMAIN)
    made += len(schemas)
    for sid, schema, tree in schemas:
        depth = 0

        def walk(n, d=1):
            global depth
            depth = max(depth, d)
            for v in n.get("properties", {}).values():
                if v.get("type") == "object" or "object" in (v.get("type") or []):
                    walk(v, d + 1)
        walk(schema)
        shapes[depth] = shapes.get(depth, 0) + 1

        v = Draft202012Validator(schema)
        for i in range(EXAMPLES):
            try:
                ex = make_example(rng, dom, sid, schema, tree, v)
                if ex is None:
                    continue
                ok += 1
            except Exception as e:
                bad += 1
                if len(failures) < 6:
                    failures.append((dom, sid, repr(e)[:300]))

print("synthesised %d schemas across %d domains" % (made, len(DOMAINS)))
print("nesting depth histogram:", dict(sorted(shapes.items())))
print("examples: %d valid, %d failed" % (ok, bad))
for dom, sid, err in failures:
    print("\n  FAIL %s/%s\n    %s" % (dom, sid, err))
