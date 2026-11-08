"""Synthesise additional schemas per domain from the extracted field catalog.

The point of the fine-tune is that the model follows *any* schema, so schema
diversity is what the held-out split actually measures. v1 had 36 hand-written
schemas and scored 94.7% field accuracy on unseen ones; hand-writing another 64
would be slow and would still be a thin sample of schema space.

Every type used here came out of a hand-written schema that already validated
against real targets (see catalog.py), so a synthesised schema cannot ask for a
type the projected record would fail. What varies is the part the model has to
generalise over: which fields are present, what they are called, how deeply they
are nested, and which of them are grouped together.
"""
import json
import re
from collections import OrderedDict

from catalog import dedupe
from core import COLLAPSE, LIST_KEY, root, s_arr, s_obj

GROUP_NAMES = ["details", "meta", "info", "summary", "record", "header", "body",
               "attributes", "payload", "fields", "data", "properties_"]
TITLE_SUFFIX = ["Record", "Extract", "View", "Payload", "Form", "Row", "Entry",
                "Capture", "Digest", "Sheet", "Report", "Snapshot"]


def to_camel(s):
    parts = [p for p in s.split("_") if p]
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:]) if parts else s


def to_pascal(s):
    return "".join(p[:1].upper() + p[1:] for p in s.split("_") if p)


def to_kebabish(s):
    return s.replace("_", "")


STYLES = [lambda s: s, to_camel, to_pascal, to_kebabish]


def name_options(names, style):
    """All names this field has worn, rendered in the schema's naming style."""
    out = []
    for n in names:
        v = style(n)
        if v and v not in out:
            out.append(v)
    return out or [names[0]]


def _unique(name, taken):
    if name not in taken:
        return name
    i = 2
    while "%s_%d" % (name, i) in taken:
        i += 1
    return "%s_%d" % (name, i)


def _nullable_array(node):
    """Force an array node to be nullable, matching how project() emits absences."""
    n = json.loads(json.dumps(node))
    t = n.get("type")
    if isinstance(t, list):
        if "null" not in t:
            n["type"] = t + ["null"]
    elif t is not None:
        n["type"] = [t, "null"]
    return n


def _pick_fields(rng, cat, lo, hi):
    keys = list(cat["fields"].keys())
    rng.shuffle(keys)
    n = min(len(keys), rng.randint(lo, hi))
    return keys[:n]


def _list_node(rng, src, rec, style, taken):
    """Build one array property from a catalogued list."""
    if rec["scalar"]:
        name, node = rec["scalar"][rng.randrange(len(rec["scalar"]))]
        key = _unique(style(name), taken)
        return key, _nullable_array(node), {LIST_KEY: src, "item": None}
    if rec["object"]:
        sub_props, sub_tree = OrderedDict(), OrderedDict()
        sub_taken = set()
        subkeys = list(rec["object"].keys())
        rng.shuffle(subkeys)
        keep = subkeys[:max(1, rng.randint(1, len(subkeys)))]
        # Keep the catalogued order so the rendered columns and the schema agree.
        for wk in [k for k in rec["object"] if k in keep]:
            names, schemas = dedupe(rec["object"][wk])
            nm = _unique(style(rng.choice(name_options(names, lambda s: s))), sub_taken)
            sub_taken.add(nm)
            sub_props[nm] = schemas[rng.randrange(len(schemas))]
            sub_tree[nm] = "$" + wk
        key = _unique(style(src), taken)
        return key, s_arr(s_obj(sub_props)), {LIST_KEY: src, "item": sub_tree}
    return None


def synth_one(rng, domain, cat, index):
    """One (schema_id, schema, projection_tree)."""
    style = rng.choice(STYLES)
    chosen = _pick_fields(rng, cat, 5, 12)

    leaves = []            # (prop_name, schema_node, "$worldkey")
    taken = set()
    for wk in chosen:
        names, schemas = dedupe(cat["fields"][wk])
        opts = name_options(names, style)
        nm = _unique(rng.choice(opts), taken)
        taken.add(nm)
        leaves.append((nm, schemas[rng.randrange(len(schemas))], "$" + wk))

    arrays = []
    srcs = list(cat["lists"].keys())
    rng.shuffle(srcs)
    for src in srcs[:rng.randint(0, min(2, len(srcs)))]:
        built = _list_node(rng, src, cat["lists"][src], style, taken)
        if built:
            taken.add(built[0])
            arrays.append(built)

    # ---- shape: flat, one group, two groups, or a nested group
    shape = rng.choice(["flat", "flat", "group", "group", "two_groups", "nested"])
    props, tree = OrderedDict(), OrderedDict()

    def put_flat(items):
        for nm, node, ref in items:
            props[nm] = node
            tree[nm] = ref

    def group_of(items, nullable_obj):
        gp, gt = OrderedDict(), OrderedDict()
        for nm, node, ref in items:
            gp[nm] = node
            gt[nm] = ref
        if nullable_obj:
            gt[COLLAPSE] = True
        return s_obj(gp, nullable_obj=nullable_obj), gt

    if shape == "flat" or len(leaves) < 4:
        put_flat(leaves)
    elif shape == "group":
        k = rng.randint(2, max(2, len(leaves) // 2))
        gname = _unique(style(rng.choice(GROUP_NAMES)), taken)
        taken.add(gname)
        node, sub = group_of(leaves[:k], rng.random() < 0.5)
        props[gname] = node
        tree[gname] = sub
        put_flat(leaves[k:])
    elif shape == "two_groups":
        k1 = rng.randint(2, max(2, len(leaves) // 3))
        k2 = rng.randint(2, max(2, len(leaves) // 3))
        rest = leaves[k1 + k2:]
        for chunk in (leaves[:k1], leaves[k1:k1 + k2]):
            if not chunk:
                continue
            gname = _unique(style(rng.choice(GROUP_NAMES)), taken)
            taken.add(gname)
            node, sub = group_of(chunk, rng.random() < 0.4)
            props[gname] = node
            tree[gname] = sub
        put_flat(rest)
    else:  # nested: a group that itself contains a group
        k = rng.randint(3, max(3, (2 * len(leaves)) // 3))
        inner_k = max(2, k // 2)
        outer_name = _unique(style(rng.choice(GROUP_NAMES)), taken)
        taken.add(outer_name)
        inner_name = _unique(style(rng.choice(GROUP_NAMES)), taken)
        taken.add(inner_name)
        inner_node, inner_tree = group_of(leaves[:inner_k], rng.random() < 0.4)
        outer_props, outer_tree = OrderedDict(), OrderedDict()
        outer_props[inner_name] = inner_node
        outer_tree[inner_name] = inner_tree
        for nm, node, ref in leaves[inner_k:k]:
            outer_props[nm] = node
            outer_tree[nm] = ref
        nullable_outer = rng.random() < 0.3
        props[outer_name] = s_obj(outer_props, nullable_obj=nullable_outer)
        if nullable_outer:
            outer_tree[COLLAPSE] = True
        tree[outer_name] = outer_tree
        put_flat(leaves[k:])

    for nm, node, sub in arrays:
        props[nm] = node
        tree[nm] = sub

    title = to_pascal(domain) + rng.choice(TITLE_SUFFIX)
    schema = root(props, title=title)
    return ("%s_g%02d" % (domain, index), schema, tree)


def synth_for_domain(rng, domain, cat, n, avoid_sigs=()):
    """n distinct synthesised schemas for one domain."""
    out, seen = [], set(avoid_sigs)
    tries = 0
    while len(out) < n and tries < n * 60:
        tries += 1
        sid, schema, tree = synth_one(rng, domain, cat, len(out))
        sig = json.dumps(schema["properties"], sort_keys=True)
        if sig in seen:
            continue
        seen.add(sig)
        out.append((sid, schema, tree))
    return out


def signature(schema):
    return json.dumps(schema["properties"], sort_keys=True)
