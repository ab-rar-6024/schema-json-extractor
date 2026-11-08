"""Invert the hand-written schemas into a per-domain field catalog.

Each hand-written schema pairs a JSON Schema with a projection tree, so every leaf
gives us a triple: (world key, the JSON type that validated against it, the name it
was given). Collecting those across all 36 schemas yields, for each world key, the
set of types known to be correct for it and the set of names it has worn.

Deriving the catalog this way rather than writing it by hand means a synthesised
schema cannot invent a type that the target would fail to validate against: every
type in it already validated somewhere.
"""
from collections import OrderedDict

from core import COLLAPSE, LIST_KEY


def _walk(node, tree, out, path):
    """Pair schema nodes with projection-tree leaves."""
    if not isinstance(tree, dict):
        return
    if LIST_KEY in tree:
        src = tree[LIST_KEY]
        item_tree = tree.get("item")
        item_schema = (node or {}).get("items")
        if item_tree is None:
            out["lists"].setdefault(src, {"scalar": [], "object": OrderedDict()})
            out["lists"][src]["scalar"].append((path[-1], node))
        elif isinstance(item_tree, dict):
            rec = out["lists"].setdefault(src, {"scalar": [], "object": OrderedDict()})
            for k, v in item_tree.items():
                if isinstance(v, str) and v.startswith("$"):
                    sub = (item_schema or {}).get("properties", {}).get(k)
                    if sub is not None:
                        rec["object"].setdefault(v[1:], []).append((k, sub))
        return
    props = (node or {}).get("properties", {})
    for k, v in tree.items():
        if k == COLLAPSE:
            continue
        child = props.get(k)
        if isinstance(v, str) and v.startswith("$"):
            if child is not None:
                out["fields"].setdefault(v[1:], []).append((k, child))
        elif isinstance(v, dict):
            _walk(child, v, out, path + [k])


def build(domains):
    """domains: the DOMAINS registry. Returns {domain: {"fields":…, "lists":…}}."""
    cat = {}
    for dom, spec in domains.items():
        out = {"fields": OrderedDict(), "lists": OrderedDict()}
        for _sid, schema, tree in spec["schemas"]:
            _walk(schema, tree, out, [])
        cat[dom] = out
    return cat


def _key(schema_node):
    """A hashable identity for a JSON type, so duplicates collapse."""
    import json
    return json.dumps(schema_node, sort_keys=True)


def dedupe(entries):
    """[(name, schema)] -> (names in first-seen order, distinct schemas)."""
    names, schemas, seen = [], [], set()
    for name, sch in entries:
        if name not in names:
            names.append(name)
        k = _key(sch)
        if k not in seen:
            seen.add(k)
            schemas.append(sch)
    return names, schemas


if __name__ == "__main__":
    import sys
    from domains import DOMAINS
    cat = build(DOMAINS)
    total_f = total_l = 0
    for dom in sorted(cat):
        f, l = cat[dom]["fields"], cat[dom]["lists"]
        total_f += len(f)
        total_l += len(l)
        print("%-10s %2d scalar fields, %d lists" % (dom, len(f), len(l)))
        if "-v" in sys.argv:
            for wk, entries in f.items():
                names, schemas = dedupe(entries)
                print("   $%-16s names=%-34s types=%d"
                      % (wk, ",".join(names)[:34], len(schemas)))
            for src, rec in l.items():
                print("   list $%-14s scalar=%d objfields=%s"
                      % (src, len(rec["scalar"]), list(rec["object"])))
    print("\ntotal: %d scalar fields, %d lists across %d domains"
          % (total_f, total_l, len(cat)))
