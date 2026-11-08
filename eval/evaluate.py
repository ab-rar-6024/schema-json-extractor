"""SchemaForge evaluation: valid JSON, schema pass, field accuracy, hallucination.

Works for the tuned adapter and for the plain base model, so the two are measured the
same way.

    python evaluate.py --model Qwen/Qwen2.5-3B-Instruct --adapter out/adapter \
        --data data/out/val_unseen.jsonl --tag tuned-unseen
"""
import argparse
import json
import os
import re
import time


# ----------------------------------------------------------------- parsing
FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.S)


def extract_json(raw):
    """Best-effort recovery of a JSON object from a model completion."""
    if raw is None:
        return None, "empty"
    s = raw.strip()
    m = FENCE.search(s)
    if m:
        s = m.group(1).strip()
    try:
        return json.loads(s), "direct"
    except Exception:
        pass
    start = s.find("{")
    if start < 0:
        return None, "no_object"
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start:i + 1]), "repaired"
                except Exception:
                    return None, "unparseable"
    return None, "truncated"


# ----------------------------------------------------------------- comparison
def norm_str(s):
    return " ".join(s.strip().lower().split())


def values_equal(exp, got):
    if exp is None:
        return got is None
    if got is None:
        return False
    if isinstance(exp, bool) or isinstance(got, bool):
        return exp is got
    if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
        return abs(float(exp) - float(got)) <= 1e-6 * max(1.0, abs(float(exp)))
    if isinstance(exp, (int, float)) and isinstance(got, str):
        try:
            return abs(float(exp) - float(got.replace(",", "").strip())) <= 1e-6 * max(1.0, abs(float(exp)))
        except Exception:
            return False
    if isinstance(exp, str) and isinstance(got, (int, float)):
        try:
            return abs(float(exp) - float(got)) < 1e-9
        except Exception:
            return False
    if isinstance(exp, str) and isinstance(got, str):
        return norm_str(exp) == norm_str(got)
    if isinstance(exp, list) and isinstance(got, list):
        if len(exp) != len(got):
            return False
        if all(not isinstance(x, (dict, list)) for x in exp):
            def key(x):
                return norm_str(x) if isinstance(x, str) else x
            try:
                return sorted(map(key, exp), key=repr) == sorted(map(key, got), key=repr)
            except Exception:
                return False
        return all(values_equal(a, b) for a, b in zip(exp, got))
    if isinstance(exp, dict) and isinstance(got, dict):
        return set(exp) == set(got) and all(values_equal(exp[k], got[k]) for k in exp)
    return False


def leaves(obj, path=()):
    """Flatten to field leaves; arrays count as one leaf, as in the data builder."""
    if isinstance(obj, dict):
        out = []
        for k, v in obj.items():
            out += leaves(v, path + (k,))
        return out
    return [(".".join(path), obj)]


def get_path(obj, path):
    cur = obj
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return "__missing__"
        cur = cur[p]
    return cur


def list_f1(exp, got):
    """Set F1 for scalar arrays, so partial list extraction is visible."""
    if not isinstance(exp, list) or not isinstance(got, list):
        return None
    if any(isinstance(x, (dict, list)) for x in exp + got):
        return None
    e = set(norm_str(x) if isinstance(x, str) else repr(x) for x in exp)
    g = set(norm_str(x) if isinstance(x, str) else repr(x) for x in got)
    if not e and not g:
        return 1.0
    inter = len(e & g)
    if inter == 0:
        return 0.0
    p = inter / len(g) if g else 0.0
    r = inter / len(e) if e else 0.0
    return 2 * p * r / (p + r)


# ----------------------------------------------------------------- scoring
def score(rows, preds, validators):
    from collections import defaultdict
    n = len(rows)
    agg = {
        "n": n, "valid_json": 0, "schema_pass": 0, "exact_record": 0,
        "fields_total": 0, "fields_correct": 0,
        "null_expected": 0, "null_correct": 0, "hallucinated": 0,
        "nonnull_expected": 0, "nonnull_correct": 0, "missed_as_null": 0,
        "extra_keys": 0, "missing_keys": 0, "parse_modes": defaultdict(int),
        "list_f1_sum": 0.0, "list_f1_n": 0,
    }
    per_field = defaultdict(lambda: [0, 0])
    per_schema = defaultdict(lambda: {"n": 0, "schema_pass": 0, "fields_total": 0,
                                      "fields_correct": 0, "null_expected": 0,
                                      "hallucinated": 0})
    failures = []
    for row, raw in zip(rows, preds):
        obj, mode = extract_json(raw)
        agg["parse_modes"][mode] += 1
        sid = row["schema_id"]
        ps = per_schema[sid]
        ps["n"] += 1
        if obj is not None:
            agg["valid_json"] += 1
            errs = list(validators[sid].iter_errors(obj))
            if not errs:
                agg["schema_pass"] += 1
                ps["schema_pass"] += 1
            elif len(failures) < 40:
                failures.append({"id": row["id"], "why": "schema:" + errs[0].message[:160],
                                 "got": raw[:400]})
        elif len(failures) < 40:
            failures.append({"id": row["id"], "why": "parse:" + mode, "got": (raw or "")[:400]})

        exp_leaves = leaves(row["expected"])
        all_ok = obj is not None
        for path, exp_val in exp_leaves:
            got_val = get_path(obj, path) if isinstance(obj, dict) else "__missing__"
            if got_val == "__missing__":
                agg["missing_keys"] += 1
                got_val = None
                ok = exp_val is None and False  # a missing key is never credited
            else:
                ok = values_equal(exp_val, got_val)
            agg["fields_total"] += 1
            ps["fields_total"] += 1
            per_field[sid + "." + path][1] += 1
            if ok:
                agg["fields_correct"] += 1
                ps["fields_correct"] += 1
                per_field[sid + "." + path][0] += 1
            else:
                all_ok = False
            if exp_val is None:
                agg["null_expected"] += 1
                ps["null_expected"] += 1
                if got_val is None:
                    agg["null_correct"] += 1
                else:
                    agg["hallucinated"] += 1
                    ps["hallucinated"] += 1
            else:
                agg["nonnull_expected"] += 1
                if ok:
                    agg["nonnull_correct"] += 1
                if got_val is None:
                    agg["missed_as_null"] += 1
            f1 = list_f1(exp_val, got_val) if isinstance(exp_val, list) else None
            if f1 is not None:
                agg["list_f1_sum"] += f1
                agg["list_f1_n"] += 1
        if isinstance(obj, dict):
            exp_keys = set(p for p, _ in exp_leaves)
            got_keys = set(p for p, _ in leaves(obj))
            agg["extra_keys"] += len(got_keys - exp_keys)
        if all_ok:
            agg["exact_record"] += 1

    def rate(a, b):
        return round(a / b, 4) if b else None

    out = {
        "n": n,
        "valid_json_rate": rate(agg["valid_json"], n),
        "schema_pass_rate": rate(agg["schema_pass"], n),
        "exact_record_rate": rate(agg["exact_record"], n),
        "field_accuracy": rate(agg["fields_correct"], agg["fields_total"]),
        "nonnull_field_accuracy": rate(agg["nonnull_correct"], agg["nonnull_expected"]),
        "null_abstention_rate": rate(agg["null_correct"], agg["null_expected"]),
        "hallucination_rate": rate(agg["hallucinated"], agg["null_expected"]),
        "missed_as_null_rate": rate(agg["missed_as_null"], agg["nonnull_expected"]),
        "list_set_f1": rate(agg["list_f1_sum"], agg["list_f1_n"]),
        "extra_keys_total": agg["extra_keys"],
        "missing_keys_total": agg["missing_keys"],
        "parse_modes": dict(agg["parse_modes"]),
    }
    out["per_schema"] = dict(
        (sid, {"n": v["n"],
               "schema_pass_rate": rate(v["schema_pass"], v["n"]),
               "field_accuracy": rate(v["fields_correct"], v["fields_total"]),
               "hallucination_rate": rate(v["hallucinated"], v["null_expected"])})
        for sid, v in sorted(per_schema.items()))
    worst = sorted(((k, c / t, t) for k, (c, t) in per_field.items() if t >= 5),
                   key=lambda x: x[1])[:20]
    out["weakest_fields"] = [{"field": k, "accuracy": round(a, 3), "n": t} for k, a, t in worst]
    out["failures"] = failures
    return out


# ----------------------------------------------------------------- generation
def generate_all(model, tok, rows, max_new_tokens=600, batch_size=8, verbose=True):
    import torch
    prompts = [tok.apply_chat_template(r["messages"][:2], tokenize=False,
                                       add_generation_prompt=True) for r in rows]
    outs = []
    t0 = time.time()
    for i in range(0, len(prompts), batch_size):
        chunk = prompts[i:i + batch_size]
        enc = tok(chunk, return_tensors="pt", padding=True, truncation=True,
                  max_length=3072).to(model.device)
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                                 temperature=None, top_p=None, top_k=None,
                                 pad_token_id=tok.pad_token_id)
        for j in range(len(chunk)):
            outs.append(tok.decode(gen[j][enc["input_ids"].shape[1]:],
                                   skip_special_tokens=True))
        if verbose:
            done = min(i + batch_size, len(prompts))
            print("  generated %d/%d  (%.1fs)" % (done, len(prompts), time.time() - t0),
                  flush=True)
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--data", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=600)
    ap.add_argument("--load-4bit", action="store_true")
    ap.add_argument("--tag", default="run")
    ap.add_argument("--out", default="eval_results")
    ap.add_argument("--preds", default=None, help="score an existing predictions file instead")
    args = ap.parse_args()

    from jsonschema import Draft202012Validator
    rows = [json.loads(l) for l in open(args.data, encoding="utf-8")]
    if args.limit:
        rows = rows[:args.limit]
    validators = {}
    for r in rows:
        if r["schema_id"] not in validators:
            validators[r["schema_id"]] = Draft202012Validator(r["schema"])

    if args.preds:
        preds = [json.loads(l)["raw"] for l in open(args.preds, encoding="utf-8")]
    else:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        tok = AutoTokenizer.from_pretrained(args.model, padding_side="left")
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token
        kw = {"device_map": "auto"}
        if args.load_4bit:
            kw["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=torch.bfloat16 if (torch.cuda.get_device_properties(0).major >= 8)
                else torch.float16)
        else:
            kw["torch_dtype"] = torch.bfloat16 if (torch.cuda.get_device_properties(0).major >= 8) else torch.float16
        model = AutoModelForCausalLM.from_pretrained(args.model, **kw)
        if args.adapter:
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, args.adapter)
        model.eval()
        preds = generate_all(model, tok, rows, args.max_new_tokens, args.batch_size)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "preds_%s.jsonl" % args.tag), "w", encoding="utf-8") as f:
        for r, p in zip(rows, preds):
            f.write(json.dumps({"id": r["id"], "schema_id": r["schema_id"], "raw": p},
                               ensure_ascii=False) + "\n")
    res = score(rows, preds, validators)
    res["tag"] = args.tag
    res["model"] = args.model
    res["adapter"] = args.adapter
    res["data"] = os.path.basename(args.data)
    with open(os.path.join(args.out, "metrics_%s.json" % args.tag), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    head = dict((k, v) for k, v in res.items()
                if k not in ("per_schema", "weakest_fields", "failures"))
    print(json.dumps(head, indent=2))
    return res


if __name__ == "__main__":
    main()
