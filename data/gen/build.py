"""Build the SchemaForge v1 dataset.

Every example is generated record-first: a world state is sampled, a subset of its
fields is marked present, only present fields are rendered into the text, and the
expected JSON is projected from the world state.  The target is therefore correct by
construction and every example is validated against its own JSON Schema before it is
written out.

    python build.py --train 4000 --val 400 --unseen 400 --seed 7
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jsonschema import Draft202012Validator

import core
from core import LIST_KEY, apply_noise, leaf_keys, project
from domains import DOMAINS

SYSTEM = (
    "You are SchemaForge, a structured data extraction engine. You are given a JSON "
    "Schema and an input text. Return one JSON object that validates against the schema.\n"
    "Rules:\n"
    "1. Use only values stated in the text. Never guess, infer or invent a value.\n"
    "2. If the text does not state a field, set it to null.\n"
    "3. Normalise dates to YYYY-MM-DD, numbers to plain numerics without currency "
    "symbols or thousands separators, and enums to one of the allowed values.\n"
    "4. Output JSON only: no prose, no explanation, no markdown fences."
)

USER_TMPL = "<schema>\n%s\n</schema>\n\n<text>\n%s\n</text>"

# Which domains / schema variants the model is allowed to see during training.
TRAIN_DOMAINS = ["review", "ticket", "email", "receipt", "log", "job", "news",
                 "property", "meeting",
                 # v4: qualified-span domains (see domains_v4.py)
                 "cinema", "warehouse", "maintenance"]
HELDOUT_DOMAINS = ["shipment", "incident", "invoice"]
TRAIN_VARIANTS = (0, 1)          # variant 2 of every training domain is held out

# Synthesised schemas per domain (see synth.py), on top of the 3 hand-written
# ones. Of each domain's SYNTH_PER_DOMAIN, the last SYNTH_HELDOUT are held out.
# v1 trained on 18 schemas; schema diversity is what the unseen split measures,
# so this is the lever that matters most for generalisation.
SYNTH_PER_DOMAIN = 6
SYNTH_HELDOUT = 2
SYNTH_SEED = 4242               # fixed, so the pool is identical run to run

MISSING_MIX = [(0.0, 0.40), (0.1, 0.12), (0.2, 0.15), (0.35, 0.12),
               (0.6, 0.10), (1.0, 0.06)]

# A field that is only ever rendered alongside another field mirrors that anchor's
# presence exactly.  If it were present alone the target would state a value the text
# never shows (hallucination); if it were absent while the anchor is shown the target
# would claim "not stated" about something the text does state (false null).
MIRROR = {
    "review": {"currency": ["price"]},
    "ticket": {"currency": ["refund_amount"]},
    "email": {"currency": ["amount"]},
    "receipt": {"currency": ["items", "subtotal", "tax", "total"]},
    "job": {"currency": ["salary_min", "salary_max"]},
    "news": {"currency": ["amount"], "amount_unit": ["amount"]},
    "property": {"currency": ["price"]},
    "shipment": {"currency": ["cost"]},
    "incident": {"currency": ["revenue_loss"]},
    "invoice": {"currency": ["lines", "subtotal", "tax", "total"]},
    "cinema": {"currency": ["total"]},
}

DERIVED = {
    "email": [("meeting_time_iso", "meeting_time", lambda v: "%02d:%02d" % v)],
    "receipt": [("time_iso", "time", lambda v: "%02d:%02d" % v),
                ("item_count", "items", len)],
    "meeting": [("start_iso", "start", lambda v: "%02d:%02d" % v),
                ("attendee_count", "attendees", len),
                ("first_action_owner", "actions", lambda v: v[0]["owner"] if v else None)],
    "incident": [("followup_count", "followups", len)],
    "invoice": [("line_count", "lines", len)],
    "cinema": [("show_iso", "show_time", lambda v: "%02d:%02d" % v)],
}


def pick_missing(rng):
    r = rng.random()
    acc = 0.0
    for val, w in MISSING_MIX:
        acc += w
        if r <= acc:
            return val
    return 0.0


def intify(obj):
    """1200.0 -> 1200 so targets stay clean; integers still validate as `number`."""
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, float) and abs(obj - round(obj)) < 1e-9:
        return int(round(obj))
    if isinstance(obj, dict):
        return dict((k, intify(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return [intify(v) for v in obj]
    return obj


def null_leaf_names(obj, out=None):
    """Field names in this target whose value really is null.

    An injection may only name one of these: that way obeying it would be a
    visible error, and ignoring it is a choice the example actually records.
    """
    if out is None:
        out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if v is None:
                out.add(k)
            else:
                null_leaf_names(v, out)
    elif isinstance(obj, list):
        for v in obj:
            null_leaf_names(v, out)
    return out


def stated_leaf_pairs(obj):
    """(name, value) for every scalar the text really states, outside lists.

    An override attack may only name one of these, and dictates a different value; the
    target keeps the stated one. Names that appear twice with different values are dropped
    so the attack is never ambiguous about which field it means.
    """
    seen = {}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, (dict, list)):
                    walk(v)
                elif v is not None:
                    seen.setdefault(k, set()).add(json.dumps(v))
    walk(obj)
    out = []

    def collect(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, dict):
                    collect(v)
                elif not isinstance(v, list) and v is not None and len(seen.get(k, ())) == 1:
                    out.append((k, v))
    collect(obj)
    return sorted(out, key=lambda kv: kv[0])


def protect_words(expected):
    """Tokens that carry ground truth and must survive typo injection."""
    out = set()

    def walk(o):
        if isinstance(o, str):
            flat = o
            for ch in "/-,.@_:()[]\"'":
                flat = flat.replace(ch, " ")
            for tok in [o] + flat.split() + re.findall(r"\w+", o):
                tok = tok.strip(".:;()[]\"'")
                if tok:
                    out.add(tok)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(expected)
    return out


def count_fields(obj):
    """(null_leaves, total_leaves) over the expected JSON."""
    if isinstance(obj, dict):
        n = t = 0
        for v in obj.values():
            a, b = count_fields(v)
            n += a
            t += b
        return n, t
    if isinstance(obj, list):
        return 0, 1
    return (1 if obj is None else 0), 1


def make_example(rng, domain, schema_id, schema, tree, validator):
    spec = DOMAINS[domain]
    for _attempt in range(25):
        world = spec["world"](rng)
        for key, src, fn in DERIVED.get(domain, []):
            world[key] = fn(world[src]) if world.get(src) is not None else None
        schema_keys = leaf_keys(tree)
        p = pick_missing(rng)
        present = set()
        for k in world:
            if k in schema_keys:
                if rng.random() > p:
                    present.add(k)
            elif rng.random() < 0.6:
                present.add(k)
        for key, anchors in MIRROR.get(domain, {}).items():
            if any(a in present for a in anchors):
                present.add(key)
            else:
                present.discard(key)
        for key, src, _fn in DERIVED.get(domain, []):
            if src in present:
                present.add(key)
            else:
                present.discard(key)

        expected = intify(project(tree, world, present))
        text = spec["render"](world, present, rng)
        if len(text.strip()) < 45:
            continue
        profile = rng.choice(core.NOISE_PROFILES)
        text = apply_noise(text, rng, profile, protect_words(expected),
                           null_leaf_names(expected), stated_leaf_pairs(expected))
        errs = sorted(validator.iter_errors(expected), key=str)
        if errs:
            raise AssertionError("%s/%s invalid target: %s" % (domain, schema_id, errs[0].message))
        nulls, total = count_fields(expected)
        schema_txt = json.dumps(schema, ensure_ascii=False, indent=2)
        target = json.dumps(expected, ensure_ascii=False)
        return {
            "domain": domain,
            "schema_id": schema_id,
            "noise": profile,
            "missing_rate": p,
            "null_fields": nulls,
            "total_fields": total,
            "schema": schema,
            "text": text,
            "expected": expected,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER_TMPL % (schema_txt, text)},
                {"role": "assistant", "content": target},
            ],
        }
    return None


def schema_pool(domains, variants):
    pool = []
    for d in domains:
        for i, (sid, schema, tree) in enumerate(DOMAINS[d]["schemas"]):
            if variants is None or i in variants:
                pool.append((d, sid, schema, tree))
    return pool


def synth_pools():
    """Synthesised schemas, split into a train share and a held-out share."""
    import catalog
    import synth
    rng = random.Random(SYNTH_SEED)
    cat = catalog.build(DOMAINS)
    train, held = {}, {}
    for d in sorted(DOMAINS):
        avoid = [synth.signature(s) for _sid, s, _t in DOMAINS[d]["schemas"]]
        got = synth.synth_for_domain(rng, d, cat[d], SYNTH_PER_DOMAIN, avoid)
        cut = len(got) - SYNTH_HELDOUT
        train[d] = [(d,) + x for x in got[:cut]]
        held[d] = [(d,) + x for x in got[cut:]]
    return train, held


def generate(pool, n, rng, validators, seen):
    rows, skipped = [], 0
    while len(rows) < n:
        d, sid, schema, tree = pool[len(rows) % len(pool)] if rng.random() < 0.5 else rng.choice(pool)
        ex = make_example(rng, d, sid, schema, tree, validators[sid])
        if ex is None:
            skipped += 1
            continue
        h = hashlib.sha1((sid + "||" + ex["text"]).encode("utf-8")).hexdigest()
        if h in seen:
            skipped += 1
            continue
        seen.add(h)
        ex["id"] = "%s-%s-%06d" % (d, sid, len(rows))
        rows.append(ex)
    return rows, skipped


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def summarise(rows):
    nulls = sum(r["null_fields"] for r in rows)
    total = sum(r["total_fields"] for r in rows)
    chars = sum(len(r["messages"][1]["content"]) + len(r["messages"][2]["content"]) for r in rows)
    by_domain, by_noise = {}, {}
    for r in rows:
        by_domain[r["domain"]] = by_domain.get(r["domain"], 0) + 1
        by_noise[r["noise"]] = by_noise.get(r["noise"], 0) + 1
    return {
        "examples": len(rows),
        "schemas": len(set(r["schema_id"] for r in rows)),
        "null_field_rate": round(nulls / max(total, 1), 4),
        "all_null_examples": sum(1 for r in rows if r["null_fields"] == r["total_fields"]),
        "fully_populated_examples": sum(1 for r in rows if r["null_fields"] == 0),
        "avg_prompt_chars": round(chars / max(len(rows), 1)),
        "max_prompt_chars": max((len(r["messages"][1]["content"]) for r in rows), default=0),
        "by_domain": by_domain,
        "by_noise": by_noise,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=int, default=4000)
    ap.add_argument("--val", type=int, default=400)
    ap.add_argument("--unseen", type=int, default=400)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "..", "out"))
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    synth_train, synth_held = synth_pools()

    validators = {}
    for d, spec in DOMAINS.items():
        for sid, schema, _tree in spec["schemas"]:
            Draft202012Validator.check_schema(schema)
            validators[sid] = Draft202012Validator(schema)
    for bucket in (synth_train, synth_held):
        for d, entries in bucket.items():
            for _d, sid, schema, _tree in entries:
                Draft202012Validator.check_schema(schema)
                validators[sid] = Draft202012Validator(schema)

    # Training sees: hand-written variants 0-1 and most synthesised schemas, for
    # the 9 training domains only.
    train_pool = schema_pool(TRAIN_DOMAINS, TRAIN_VARIANTS)
    for d in TRAIN_DOMAINS:
        train_pool += synth_train[d]
    # Held out: variant 2 and the remaining synthesised schemas of those domains,
    # plus every schema of the 3 domains the model never trains on at all.
    unseen_pool = schema_pool(TRAIN_DOMAINS, (2,)) + schema_pool(HELDOUT_DOMAINS, None)
    for d in TRAIN_DOMAINS:
        unseen_pool += synth_held[d]
    for d in HELDOUT_DOMAINS:
        unseen_pool += synth_train[d] + synth_held[d]
    print("train schemas: %d   unseen schemas: %d   (total %d)"
          % (len(train_pool), len(unseen_pool), len(train_pool) + len(unseen_pool)))

    seen = set()
    rng = random.Random(args.seed)
    train, s1 = generate(train_pool, args.train, rng, validators, seen)
    val_seen, s2 = generate(train_pool, args.val, random.Random(args.seed + 1), validators, seen)
    val_unseen, s3 = generate(unseen_pool, args.unseen, random.Random(args.seed + 2), validators, seen)

    write_jsonl(os.path.join(out, "train.jsonl"), train)
    write_jsonl(os.path.join(out, "val_seen.jsonl"), val_seen)
    write_jsonl(os.path.join(out, "val_unseen.jsonl"), val_unseen)

    stats = {
        "seed": args.seed,
        "rejected_or_duplicate": s1 + s2 + s3,
        "train_schema_ids": sorted(set(x[1] for x in train_pool)),
        "unseen_schema_ids": sorted(set(x[1] for x in unseen_pool)),
        "train": summarise(train),
        "val_seen": summarise(val_seen),
        "val_unseen": summarise(val_unseen),
    }
    with open(os.path.join(out, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    # human spot-check file
    sample = random.Random(99).sample(train, min(50, len(train)))
    with open(os.path.join(out, "spotcheck.md"), "w", encoding="utf-8") as f:
        f.write("# SchemaForge - 50 random training examples for manual review\n")
        for i, r in enumerate(sample, 1):
            f.write("\n\n---\n\n## %d. %s / %s  (noise=%s, missing=%.2f)\n" %
                    (i, r["domain"], r["schema_id"], r["noise"], r["missing_rate"]))
            f.write("\n### schema\n```json\n%s\n```\n" %
                    json.dumps(r["schema"], ensure_ascii=False, indent=2))
            f.write("\n### text\n```\n%s\n```\n" % r["text"])
            f.write("\n### expected\n```json\n%s\n```\n" %
                    json.dumps(r["expected"], ensure_ascii=False, indent=2))

    print(json.dumps(stats, indent=2)[:4000])
    print("\nwrote -> %s" % out)


if __name__ == "__main__":
    main()
