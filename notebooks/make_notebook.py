"""Assemble schemaforge_v1_qlora.ipynb, embedding the local generator + eval sources
so the notebook is fully self-contained (nothing to upload besides the notebook)."""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read().rstrip("\n")


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": text}


cells = []

cells.append(md("""# SchemaForge v1 - universal schema-driven JSON extraction

QLoRA supervised fine-tune of a small Qwen model that takes **(JSON Schema + text)**
and returns **JSON that validates against that schema**, with `null` for anything the
text does not state.

This notebook is self-contained: it writes its own data generator, builds and audits
the dataset, trains, and evaluates the tuned model against the untuned baseline on
both seen and unseen schemas.

**Runtime > Change runtime type > GPU** before running anything.

Pipeline: GPU check -> install -> generate + audit data -> tokenise with
prompt masking -> QLoRA train -> evaluate (tuned vs base, seen vs unseen schemas)
-> merge + export."""))

cells.append(md("## 1. Runtime check"))
cells.append(code("""import subprocess, sys
print(subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout)
import torch
assert torch.cuda.is_available(), "No GPU: Runtime > Change runtime type > GPU, then rerun."
props = torch.cuda.get_device_properties(0)
# torch.cuda.is_bf16_supported() returns True on a T4 because it counts emulation.
# Real bf16 starts at compute capability 8.0 (A100 / L4), so check that instead.
BF16 = props.major >= 8
print("GPU:", props.name, "| VRAM: %.1f GB" % (props.total_memory / 1e9), "| bf16:", BF16)
print("torch", torch.__version__, "| python", sys.version.split()[0])"""))

cells.append(md("## 2. Install dependencies"))
cells.append(code("""# Pinned deliberately. transformers 5.x dropped warmup_ratio (and more) from
# TrainingArguments, and datasets 5.x requires a huggingface-hub that transformers 4.x
# will not install - that combination fails at import. This trio is what the QLoRA
# stack actually works against on Colab today.
%pip install -q -U "transformers<5" "tokenizers<0.22" "datasets<4" \\
    "peft>=0.14" "accelerate>=1.2" "bitsandbytes>=0.45" jsonschema
import transformers, peft, bitsandbytes, accelerate, jsonschema
print("transformers", transformers.__version__, "| peft", peft.__version__,
      "| bitsandbytes", bitsandbytes.__version__, "| accelerate", accelerate.__version__)"""))

cells.append(md("""## 3. Data generator

Record-first synthesis: a world state is sampled, a subset of its fields is marked
present, **only present fields are rendered into the text**, and the target JSON is
projected from the world state. The target is therefore correct by construction, and
absent fields are the null-handling signal. 12 domains x 3 schema variants = 36
schemas; 18 are held out so generalisation to unseen schemas can be measured."""))
for fname, rel in [("core.py", "data/gen/core.py"),
                   ("domains.py", "data/gen/domains.py"),
                   ("build.py", "data/gen/build.py"),
                   ("audit.py", "data/gen/audit.py"),
                   ("evaluate.py", "eval/evaluate.py")]:
    cells.append(code("%%writefile " + fname + "\n" + read(rel)))

cells.append(md("""### Build and audit the dataset

`audit.py` re-checks every non-null value in every target against its text. Anything
it flags would be a generator bug teaching the model to hallucinate, so this must come
out at 0 rows before training."""))
cells.append(code("""!python build.py --train 4000 --val 450 --unseen 450 --seed 7 --out out
print("\\n================ GROUNDEDNESS AUDIT ================")
!python audit.py out/train.jsonl out/val_seen.jsonl out/val_unseen.jsonl"""))

cells.append(code("""import json
stats = json.load(open("out/stats.json"))
for split in ["train", "val_seen", "val_unseen"]:
    s = stats[split]
    print("%-11s n=%-5d schemas=%-3d null_field_rate=%.3f all_null=%-4d fully_populated=%-5d avg_chars=%d"
          % (split, s["examples"], s["schemas"], s["null_field_rate"],
             s["all_null_examples"], s["fully_populated_examples"], s["avg_prompt_chars"]))
print("\\ntrain schemas :", ", ".join(stats["train_schema_ids"]))
print("\\nUNSEEN schemas:", ", ".join(stats["unseen_schema_ids"]))"""))

cells.append(md("### One example, end to end"))
cells.append(code("""rows = [json.loads(l) for l in open("out/train.jsonl", encoding="utf-8")]
ex = rows[7]
print(ex["messages"][1]["content"][:1800])
print("\\n--- TARGET ---\\n" + ex["messages"][2]["content"])"""))

cells.append(md("## 4. Configuration"))
cells.append(code('''# Qwen3-4B where bf16 is available (L4/A100); Qwen2.5-3B on a T4, which is fp16-only.
MODEL_ID   = "Qwen/Qwen3-4B-Instruct-2507" if BF16 else "Qwen/Qwen2.5-3B-Instruct"
MAX_LEN    = 2048
EPOCHS     = 1            # 1 epoch over 4000 is ~1h55m on a free T4; 2 would not fit a session
LR         = 1e-4
LORA_R     = 32
LORA_ALPHA = 64
BATCH      = 2            # keep gradient checkpointing on: a T4 OOMs at 15.6 GB without it
ACCUM      = 16 // BATCH
EVAL_LIMIT = 150          # examples per split at generation time
SMOKE      = False        # True = 200 examples / 1 epoch, to validate the pipeline fast
OUT_DIR    = "/content/schemaforge-v1"
print("model:", MODEL_ID, "| effective batch:", BATCH * ACCUM, "| max_len:", MAX_LEN,
      "| smoke:", SMOKE)
# T4 reference: ~27.7 s/optimizer step (16 examples) => ~1h55m for 1 epoch over 4000.'''))

cells.append(md("""## 5. Tokenise with prompt masking

Loss is computed on the JSON completion only: prompt tokens are labelled `-100`. The
prompt and the target are tokenised separately and concatenated, so the mask boundary
is exact and does not depend on chat-template string matching."""))
cells.append(code('''from transformers import AutoTokenizer
import numpy as np

tok = AutoTokenizer.from_pretrained(MODEL_ID)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
END_ID = tok.convert_tokens_to_ids("<|im_end|>")
if END_ID is None or END_ID == tok.unk_token_id:
    END_ID = tok.eos_token_id
print("pad:", tok.pad_token, "| turn-end id:", END_ID)


def encode(ex):
    prompt = tok.apply_chat_template(ex["messages"][:2], tokenize=False,
                                     add_generation_prompt=True)
    p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    t_ids = tok(ex["messages"][2]["content"], add_special_tokens=False)["input_ids"] + [END_ID]
    ids = p_ids + t_ids
    labels = [-100] * len(p_ids) + t_ids
    return {"input_ids": ids, "labels": labels, "n_prompt": len(p_ids),
            "n_target": len(t_ids)}


def load_split(path, limit=0):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    if limit:
        rows = rows[:limit]
    return rows

train_rows = load_split("out/train.jsonl", 200 if SMOKE else 0)
val_rows   = load_split("out/val_seen.jsonl", 60 if SMOKE else 300)

train_enc = [encode(r) for r in train_rows]
val_enc   = [encode(r) for r in val_rows]
lens = np.array([len(e["input_ids"]) for e in train_enc])
print("token length: mean %d | p95 %d | p99 %d | max %d"
      % (lens.mean(), np.percentile(lens, 95), np.percentile(lens, 99), lens.max()))
kept = [e for e in train_enc if len(e["input_ids"]) <= MAX_LEN]
print("kept %d/%d train examples within MAX_LEN=%d" % (len(kept), len(train_enc), MAX_LEN))
train_enc = kept
val_enc = [e for e in val_enc if len(e["input_ids"]) <= MAX_LEN]
print("target tokens: mean %.0f | max %d"
      % (np.mean([e["n_target"] for e in train_enc]), max(e["n_target"] for e in train_enc)))'''))

cells.append(code('''import torch
from torch.utils.data import Dataset


class JsonlDS(Dataset):
    def __init__(self, enc):
        self.enc = enc

    def __len__(self):
        return len(self.enc)

    def __getitem__(self, i):
        e = self.enc[i]
        return {"input_ids": e["input_ids"], "labels": e["labels"]}


def collate(batch):
    n = max(len(b["input_ids"]) for b in batch)
    pad = tok.pad_token_id
    out = {"input_ids": [], "attention_mask": [], "labels": []}
    for b in batch:
        k = n - len(b["input_ids"])
        out["input_ids"].append(b["input_ids"] + [pad] * k)
        out["attention_mask"].append([1] * len(b["input_ids"]) + [0] * k)
        out["labels"].append(b["labels"] + [-100] * k)
    return dict((k, torch.tensor(v, dtype=torch.long)) for k, v in out.items())


train_ds, val_ds = JsonlDS(train_enc), JsonlDS(val_enc)
# sanity: the unmasked span must be exactly the JSON target
s = train_enc[0]
print(tok.decode([t for t, l in zip(s["input_ids"], s["labels"]) if l != -100]))'''))

cells.append(md("## 6. Load the base model in 4-bit and attach LoRA"))
cells.append(code('''from transformers import AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

COMPUTE_DTYPE = torch.bfloat16 if BF16 else torch.float16
bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_use_double_quant=True,
                         bnb_4bit_compute_dtype=COMPUTE_DTYPE)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, quantization_config=bnb, device_map={"": 0},
    attn_implementation="sdpa", torch_dtype=COMPUTE_DTYPE)
model.config.use_cache = False
model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
model.enable_input_require_grads()

lora = LoraConfig(
    r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=0.05, bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"])
model = get_peft_model(model, lora)
model.print_trainable_parameters()'''))

cells.append(md("## 7. Train"))
cells.append(code('''from transformers import Trainer, TrainingArguments

args = TrainingArguments(
    output_dir=OUT_DIR + "/ckpt",
    per_device_train_batch_size=BATCH,
    gradient_accumulation_steps=ACCUM,
    num_train_epochs=1 if SMOKE else EPOCHS,
    learning_rate=LR,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    max_grad_norm=0.3,
    weight_decay=0.0,
    logging_steps=10,
    optim="paged_adamw_8bit",
    bf16=BF16, fp16=not BF16,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    per_device_eval_batch_size=1,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=1,
    report_to="none",
    seed=7,
)
trainer = Trainer(model=model, args=args, train_dataset=train_ds,
                  eval_dataset=val_ds, data_collator=collate)
print("optimizer steps:", len(train_ds) // (BATCH * ACCUM) * args.num_train_epochs)
train_out = trainer.train()
print(train_out.metrics)'''))

cells.append(code('''import os
os.makedirs(OUT_DIR, exist_ok=True)
model.save_pretrained(OUT_DIR + "/adapter")
tok.save_pretrained(OUT_DIR + "/adapter")
json.dump({"base_model": MODEL_ID, "max_len": MAX_LEN, "epochs": args.num_train_epochs,
           "lr": LR, "lora_r": LORA_R, "lora_alpha": LORA_ALPHA,
           "effective_batch": BATCH * ACCUM, "train_examples": len(train_ds),
           "train_metrics": train_out.metrics},
          open(OUT_DIR + "/train_config.json", "w"), indent=2)
print(os.listdir(OUT_DIR + "/adapter"))'''))

cells.append(md("""## 8. Evaluate

Same harness for the tuned model and the untuned base model, on seen schemas and on
schemas held out of training. Metrics: valid-JSON rate, schema pass rate, field
accuracy, hallucination rate (a value invented for a field the text does not state),
missed-as-null rate, and set-F1 for list fields."""))
cells.append(code('''import importlib, evaluate as ev
importlib.reload(ev)
from jsonschema import Draft202012Validator

model.config.use_cache = True
model.eval()
tok_gen = AutoTokenizer.from_pretrained(MODEL_ID, padding_side="left")
if tok_gen.pad_token is None:
    tok_gen.pad_token = tok_gen.eos_token

results = {}


def run_eval(m, t, split, tag, limit=EVAL_LIMIT, bs=8):
    rows = load_split("out/%s.jsonl" % split, limit)
    V = {}
    for r in rows:
        V.setdefault(r["schema_id"], Draft202012Validator(r["schema"]))
    preds = ev.generate_all(m, t, rows, max_new_tokens=600, batch_size=bs, verbose=False)
    res = ev.score(rows, preds, V)
    results[tag] = res
    json.dump(res, open("%s/metrics_%s.json" % (OUT_DIR, tag), "w"), indent=2)
    with open("%s/preds_%s.jsonl" % (OUT_DIR, tag), "w", encoding="utf-8") as f:
        for r, p in zip(rows, preds):
            f.write(json.dumps({"id": r["id"], "raw": p}, ensure_ascii=False) + "\\n")
    print("%-18s valid_json=%.3f schema_pass=%.3f field_acc=%.3f halluc=%.3f exact=%.3f"
          % (tag, res["valid_json_rate"], res["schema_pass_rate"], res["field_accuracy"],
             res["hallucination_rate"], res["exact_record_rate"]))
    return res


run_eval(model, tok_gen, "val_seen", "tuned_seen")
run_eval(model, tok_gen, "val_unseen", "tuned_unseen")'''))

cells.append(md("### Untuned baseline (same prompts, same scoring)"))
cells.append(code('''import gc
for _n in ["model", "trainer", "base"]:
    globals().pop(_n, None)
gc.collect(); torch.cuda.empty_cache()

base = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, quantization_config=bnb, device_map={"": 0},
    attn_implementation="sdpa", torch_dtype=COMPUTE_DTYPE)
base.eval()
run_eval(base, tok_gen, "val_seen", "base_seen")
run_eval(base, tok_gen, "val_unseen", "base_unseen")
del base
gc.collect(); torch.cuda.empty_cache()'''))

cells.append(md("### Comparison"))
cells.append(code('''keys = ["valid_json_rate", "schema_pass_rate", "field_accuracy",
        "nonnull_field_accuracy", "null_abstention_rate", "hallucination_rate",
        "missed_as_null_rate", "list_set_f1", "exact_record_rate"]
cols = ["base_seen", "tuned_seen", "base_unseen", "tuned_unseen"]
cols = [c for c in cols if c in results]
print("%-24s %s" % ("metric", "".join("%-14s" % c for c in cols)))
print("-" * (24 + 14 * len(cols)))
for k in keys:
    print("%-24s %s" % (k, "".join("%-14s" % results[c].get(k) for c in cols)))
json.dump(results, open(OUT_DIR + "/metrics_all.json", "w"), indent=2)

print("\\nWeakest fields, tuned on unseen schemas:")
for f in results.get("tuned_unseen", {}).get("weakest_fields", [])[:10]:
    print("  %-52s acc=%.2f (n=%d)" % (f["field"], f["accuracy"], f["n"]))
print("\\nFirst failures, tuned on unseen schemas:")
for f in results.get("tuned_unseen", {}).get("failures", [])[:3]:
    print("  %s -> %s\\n    %s" % (f["id"], f["why"], f["got"][:220].replace("\\n", " ")))'''))

cells.append(md("## 9. Manual spot-check (read these yourself)"))
cells.append(code('''rows = load_split("out/val_unseen.jsonl", EVAL_LIMIT)
preds = [json.loads(l) for l in open(OUT_DIR + "/preds_tuned_unseen.jsonl", encoding="utf-8")]
by_id = {p["id"]: p["raw"] for p in preds}
for r in rows[:5]:
    print("=" * 90)
    print(r["id"], "|", r["schema_id"], "| noise:", r["noise"])
    print("--- TEXT ---\\n" + r["text"][:700])
    print("--- EXPECTED ---\\n" + json.dumps(r["expected"], ensure_ascii=False))
    print("--- MODEL ---\\n" + by_id.get(r["id"], "")[:900])'''))

cells.append(md("""## 10. Merge, export, publish

The merged fp16 model can be served with vLLM, or converted to GGUF for Ollama /
llama.cpp. Keep the adapter separate if you would rather swap it at serving time."""))
cells.append(code('''from peft import PeftModel

fp16_base = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, torch_dtype=torch.float16, device_map="cpu")
merged = PeftModel.from_pretrained(fp16_base, OUT_DIR + "/adapter").merge_and_unload()
merged.save_pretrained(OUT_DIR + "/merged", safe_serialization=True)
tok.save_pretrained(OUT_DIR + "/merged")
print("merged ->", OUT_DIR + "/merged")'''))

cells.append(code('''# Optional: push to the Hugging Face Hub (needs your token; set the repo id first).
# from huggingface_hub import login
# login()  # paste a write token
# REPO = "your-username/qwen-schemaforge-v1"
# merged.push_to_hub(REPO); tok.push_to_hub(REPO)'''))

cells.append(code('''!cd /content && zip -qr schemaforge-v1-artifacts.zip \\
    schemaforge-v1/adapter schemaforge-v1/*.json schemaforge-v1/preds_*.jsonl out/stats.json
from google.colab import files
print("download: /content/schemaforge-v1-artifacts.zip")
files.download("/content/schemaforge-v1-artifacts.zip")'''))

cells.append(md("""## 11. Serving contract

Request: the JSON Schema plus the text, using the same system prompt the model was
trained with (`SYSTEM` in `build.py`). Always validate the response against the schema
in your application, retry once on failure, then fall back to manual review. For hard
guarantees, turn on constrained decoding - vLLM guided JSON, Outlines, or a llama.cpp
grammar - which forces schema-valid output during generation."""))
cells.append(code('''from build import SYSTEM, USER_TMPL

demo_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "vendor": {"type": ["string", "null"]},
        "invoice_total": {"type": ["number", "null"]},
        "currency": {"type": ["string", "null"], "enum": ["USD", "EUR", "GBP", None]},
        "due_date": {"type": ["string", "null"], "format": "date"},
        "po_number": {"type": ["string", "null"]},
    },
    "required": ["vendor", "invoice_total", "currency", "due_date", "po_number"],
    "additionalProperties": False,
}
demo_text = ("Brightmill sent over invoice 8841 for EUR 12,480.50, payment due "
             "14 March 2026. No PO was quoted on it.")
print(USER_TMPL % (json.dumps(demo_schema, indent=2), demo_text))
print("\\n(expected: po_number null, currency EUR, due_date 2026-03-14)")'''))

nb = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"provenance": [], "gpuType": "T4", "toc_visible": True},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}

out = os.path.join(HERE, "schemaforge_v1_qlora.ipynb")
with io.open(out, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("wrote %s (%d cells, %.1f KB)" % (out, len(cells), os.path.getsize(out) / 1024))
