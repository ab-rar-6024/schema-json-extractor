"""Re-score saved predictions on subsets, to find out *where* the model is weak.

No GPU and no regeneration: this reads the preds_*.jsonl that evaluate.py already wrote
and runs the same scorer over slices of the eval set.

    python slice.py --data-dir out --dir eval_results
"""
import argparse
import json
import os
from collections import defaultdict

from evaluate import score
from jsonschema import Draft202012Validator

PAIRS = [("seen", "base_seen", "tuned_seen"), ("unseen", "base_unseen", "tuned_unseen")]
KEY = "hallucination_rate"


def load(data_dir, split, limit):
    rows = [json.loads(l) for l in
            open(os.path.join(data_dir, "val_%s.jsonl" % split), encoding="utf-8")]
    return rows[:limit] if limit else rows


def load_preds(d, tag):
    p = os.path.join(d, "preds_%s.jsonl" % tag)
    if not os.path.exists(p):
        return None
    return [json.loads(l)["raw"] for l in open(p, encoding="utf-8")]


def validators_for(rows):
    v = {}
    for r in rows:
        if r["schema_id"] not in v:
            v[r["schema_id"]] = Draft202012Validator(r["schema"])
    return v


def bucket_missing(r):
    m = r["missing_rate"]
    if m <= 0.0:
        return "0.0 (all stated)"
    if m <= 0.2:
        return "0.1-0.2"
    if m <= 0.35:
        return "0.35"
    if m < 1.0:
        return "0.6"
    return "1.0 (nothing stated)"


def table(title, groups, base_rows, base_preds, tuned_rows, tuned_preds, vals):
    """groups: ordered list of (label, [indices])"""
    print("\n" + title)
    print("%-24s%6s  %-21s  %-21s" % ("", "n", "hallucination b->t", "field acc  b->t"))
    print("-" * 78)
    for label, idx in groups:
        if not idx:
            continue
        sub = [tuned_rows[i] for i in idx]
        t = score(sub, [tuned_preds[i] for i in idx], vals)
        line = "%-24s%6d  " % (label, len(idx))
        if base_preds is not None:
            b = score(sub, [base_preds[i] for i in idx], vals)
            line += "%5.1f%% -> %5.1f%%      %5.1f%% -> %5.1f%%" % (
                100 * b[KEY], 100 * t[KEY],
                100 * b["field_accuracy"], 100 * t["field_accuracy"])
        else:
            line += "%16.1f%%      %16.1f%%" % (100 * t[KEY], 100 * t["field_accuracy"])
        print(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="out")
    ap.add_argument("--dir", default="eval_results")
    ap.add_argument("--limit", type=int, default=120)
    ap.add_argument("--name", default="the tuned model",
                    help="label for the tuned column")
    args = ap.parse_args()

    for split, base_tag, tuned_tag in PAIRS:
        rows = load(args.data_dir, split, args.limit)
        tuned = load_preds(args.dir, tuned_tag)
        base = load_preds(args.dir, base_tag)
        if tuned is None:
            print("no predictions for %s, skipping" % tuned_tag)
            continue
        n = min(len(rows), len(tuned))
        rows, tuned = rows[:n], tuned[:n]
        base = base[:n] if base else None
        vals = validators_for(rows)

        print("\n" + "=" * 78)
        print("%s  (n=%d)   'b->t' is base model -> %s"
              % (split.upper(), n, args.name))
        print("=" * 78)

        by = defaultdict(list)
        for i, r in enumerate(rows):
            by[r["noise"]].append(i)
        order = ["clean", "distract", "typos", "foreign", "long", "verylong",
                 "contradict", "inject"]
        groups = [(k, by[k]) for k in order if k in by]
        groups += [(k, v) for k, v in sorted(by.items()) if k not in order]
        table("BY NOISE PROFILE  (the stress tests)", groups, rows, base, rows, tuned, vals)

        by = defaultdict(list)
        for i, r in enumerate(rows):
            by[bucket_missing(r)].append(i)
        order = ["0.0 (all stated)", "0.1-0.2", "0.35", "0.6", "1.0 (nothing stated)"]
        groups = [(k, by[k]) for k in order if k in by]
        table("BY HOW MUCH THE TEXT OMITS", groups, rows, base, rows, tuned, vals)

        by = defaultdict(list)
        for i, r in enumerate(rows):
            by[r["domain"]].append(i)
        groups = sorted(by.items())
        table("BY DOMAIN", groups, rows, base, rows, tuned, vals)

        full = score(rows, tuned, vals)
        print("\nWEAKEST FIELDS (tuned, %s)" % split)
        for w in full["weakest_fields"][:12]:
            print("  %-34s %5.1f%%   n=%d" % (w["field"], 100 * w["accuracy"], w["n"]))

        worst = sorted(full["per_schema"].items(),
                       key=lambda kv: kv[1]["field_accuracy"])[:8]
        print("\nWEAKEST SCHEMAS (tuned, %s)" % split)
        for sid, v in worst:
            print("  %-26s n=%-4d field_acc %5.1f%%  halluc %5.1f%%"
                  % (sid, v["n"], 100 * v["field_accuracy"], 100 * v["hallucination_rate"]))


if __name__ == "__main__":
    main()
