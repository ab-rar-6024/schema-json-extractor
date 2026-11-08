"""Print the tuned-vs-base comparison table and write a model-card stub.

    python report.py --dir eval_results --out MODEL_CARD.md
"""
import argparse
import json
import os

KEYS = ["valid_json_rate", "schema_pass_rate", "field_accuracy",
        "nonnull_field_accuracy", "null_abstention_rate", "hallucination_rate",
        "missed_as_null_rate", "list_set_f1", "exact_record_rate"]
ORDER = ["base_seen", "tuned_seen", "base_unseen", "tuned_unseen"]


def pct(v):
    return "-" if v is None else "%.1f%%" % (100 * v)


def describe(data_dir):
    """Read the real schema/domain/null counts off the dataset.

    These used to be hardcoded in the card text, so the v1 numbers silently
    survived into a v2 run. Deriving them means the card cannot disagree with
    the data it describes.
    """
    def rows(name):
        p = os.path.join(data_dir, name)
        if not os.path.exists(p):
            return []
        return [json.loads(l) for l in open(p, encoding="utf-8")]

    tr, un = rows("train.jsonl"), rows("val_unseen.jsonl")
    if not tr:
        return None
    tr_dom = set(r["domain"] for r in tr)
    nulls = sum(r["null_fields"] for r in tr)
    total = sum(r["total_fields"] for r in tr) or 1
    d = {"examples": len(tr),
         "schemas": len(set(r["schema_id"] for r in tr)),
         "domains": len(tr_dom),
         "null_rate": 100.0 * nulls / total}
    if un:
        d["unseen_schemas"] = len(set(r["schema_id"] for r in un))
        d["heldout_domains"] = len(set(r["domain"] for r in un) - tr_dom)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="eval_results")
    ap.add_argument("--out", default="MODEL_CARD.md")
    ap.add_argument("--config", default=None, help="train_config.json")
    ap.add_argument("--name", default="SchemaForge",
                    help="model name for the card heading")
    ap.add_argument("--data-dir", default=None,
                    help="dataset dir; counts and null rate are read from it")
    args = ap.parse_args()

    res = {}
    for f in os.listdir(args.dir):
        if f.startswith("metrics_") and f.endswith(".json") and f != "metrics_all.json":
            tag = f[len("metrics_"):-len(".json")]
            res[tag] = json.load(open(os.path.join(args.dir, f), encoding="utf-8"))
    cols = [c for c in ORDER if c in res] + sorted(set(res) - set(ORDER))
    if not cols:
        print("no metrics files in %s" % args.dir)
        return

    w = max(14, max(len(c) for c in cols) + 2)
    header = "%-26s%s" % ("metric", "".join(("%-" + str(w) + "s") % c for c in cols))
    lines = [header, "-" * len(header)]
    for k in KEYS:
        lines.append("%-26s%s" % (k, "".join(("%-" + str(w) + "s") % pct(res[c].get(k))
                                             for c in cols)))
    lines.append("%-26s%s" % ("n", "".join(("%-" + str(w) + "s") % res[c].get("n")
                                           for c in cols)))
    table = "\n".join(lines)
    print(table)

    info = describe(args.data_dir) if args.data_dir else None

    cfg = {}
    if args.config and os.path.exists(args.config):
        cfg = json.load(open(args.config, encoding="utf-8"))

    if info:
        data_line = ("- Data: %d synthetic examples over %d training schemas from %d "
                     "domains; every target validated against its own schema and "
                     "groundedness-audited" % (info["examples"], info["schemas"],
                                               info["domains"]))
        null_line = "- Null rate: ~%.0f%% of fields are not stated in the text" % info["null_rate"]
        eval_line = ("`*_unseen` uses %d schemas and %d domains held out of training "
                     "entirely." % (info.get("unseen_schemas", 0),
                                    info.get("heldout_domains", 0)))
    else:
        data_line = ("- Data: %s synthetic examples; every target validated against its "
                     "own schema and groundedness-audited"
                     % cfg.get("train_examples", "-"))
        null_line = "- Null rate: see the build summary"
        eval_line = "`*_unseen` uses schemas and domains held out of training entirely."

    card = ["# %s" % args.name,
            "",
            "Schema-driven JSON extraction: given a JSON Schema and a text, return one "
            "JSON object that validates against that schema, with `null` for anything "
            "the text does not state.",
            "",
            "## Training",
            "",
            "- Base model: `%s`" % cfg.get("base_model", "see train_config.json"),
            "- Method: QLoRA (4-bit NF4, double quant), r=%s, alpha=%s, loss on the JSON "
            "completion only" % (cfg.get("lora_r", "-"), cfg.get("lora_alpha", "-")),
            data_line,
            null_line,
            "- Effective batch %s, lr %s, %s epoch(s)"
            % (cfg.get("effective_batch", "-"), cfg.get("lr", "-"), cfg.get("epochs", "-")),
            "",
            "## Evaluation",
            "",
            eval_line,
            "",
            "```",
            table,
            "```",
            "",
            "- **hallucination_rate**: share of not-stated fields where the model invented "
            "a value. Lower is better; this is the metric the fine-tune exists for.",
            "- **missed_as_null_rate**: share of stated fields the model wrongly left null.",
            "",
            "## Use",
            "",
            "Send the same system prompt used in training (see `build.py: SYSTEM`), then "
            "the schema and the text. Always validate the response against the schema in "
            "your application; retry once on failure, then fall back to manual review. "
            "For hard guarantees use constrained decoding (vLLM guided JSON, Outlines, or "
            "a llama.cpp grammar).",
            ""]
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(card))
    print("\nwrote %s" % args.out)


if __name__ == "__main__":
    main()
