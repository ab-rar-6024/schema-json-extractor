# Schema JSON Extractor

A small model fine-tune for one job: **given a JSON Schema and a text, return one JSON object that
validates against the schema, with `null` for anything the text does not state.**

- Model (LoRA adapter on Qwen3-4B-Instruct-2507): https://huggingface.co/abr-6024/schema-json-extractor-4B
- Training data + generator: https://huggingface.co/datasets/abr-6024/schema-json-extractor-synthetic
- Write-up of the whole process, including what did not work: [`BLOG.md`](BLOG.md)

## What it does and does not do (measured)

Tuned adapter vs the **untuned base model**, same weights, same decoding, on hand-written cases the
training generator never produced, scored by a rule fixed before any result existed
([`eval/ood/eval_ood.py`](eval/ood/eval_ood.py)).

| | tuned | untuned base |
|---|---|---|
| Set 1: 48 cases, 393 fields - accuracy | 98.0% | 95.7% |
| Set 2 (fresh, written after v4 was frozen): 44 cases, 289 fields - accuracy | 93.4% | 90.0% |
| Hidden instruction in the text obeyed (set 1 / set 2) | 2/9, 0/9 | 8/9, 9/9 |
| Errors on cases with no hidden instruction, both sets | 21 | 22 |

**Read this honestly:** the accuracy gain is almost entirely resistance to instructions embedded in
the document. On ordinary extraction the tuned model is about equal to the base. Set 2 alone is not
statistically significant (p = 0.12); set 1 informed v4's design. Prompt injection is reduced, not
solved. Details and failure modes: [`docs/RESULTS_ood_fresh_v4.md`](docs/RESULTS_ood_fresh_v4.md),
[`docs/RESULTS_ood_v4.md`](docs/RESULTS_ood_v4.md).

## Layout

```
data/gen/core.py        vocabulary, surface-form formatters, noise layer (incl. inject), schema DSL
data/gen/domains.py     12 domains x hand-written schema variants
data/gen/domains_v4.py  cinema, warehouse, maintenance (qualified-span targets, e.g. "Screen 3")
data/gen/catalog.py     inverts schemas into a per-domain field catalog
data/gen/synth.py       synthesises more schemas per domain from the catalog
data/gen/build.py       dataset builder (presence sampling, projection, schema validation)
data/gen/audit.py       groundedness audit: every non-null target value must be findable in its text
notebooks/train_sf.py   QLoRA training (4-bit NF4, LoRA r=32, checkpoint/resume, NaN guard)
eval/evaluate.py        generation + metrics on the synthetic splits
eval/ood/               48-case independent set + scorer + pre-registered rule (eval_ood.py)
eval/ood2/              44-case fresh set (never used for any design decision)
results/                raw model outputs for both sets (tuned and base)
docs/                   findings and results notes for v1 -> v4, in order
```

## Reproduce

Dataset (byte-identical to the published one):

```
cd data/gen
python build.py --train 4000 --val 450 --unseen 450 --seed 7 --out ../out
python audit.py ../out/train.jsonl ../out/val_seen.jsonl ../out/val_unseen.jsonl   # 0 ungrounded
```

Rebuild and validate the eval sets (answer keys are checked against their own schema and the
groundedness audit):

```
python eval/ood/build_ood.py
python eval/ood2/build_fresh.py
```

Run tuned vs base (needs a GPU; about 25 minutes on a free T4):

```
pip install jsonschema "transformers<5" peft accelerate bitsandbytes
python eval/ood/eval_ood.py --model Qwen/Qwen3-4B-Instruct-2507 \
    --adapter abr-6024/schema-json-extractor-4B --cases eval/ood2/ood_cases_fresh.json
```

Train (about 70 minutes on a T4 for 250 steps; see `notebooks/train_sf.py --help`):

```
python notebooks/train_sf.py --model Qwen/Qwen3-4B-Instruct-2507 --dtype fp16 --epochs 1 \
    --batch 1 --accum 16 --data ../out --out ./schema-extractor --ckpt-dir ./ckpt --save-steps 25
```

## Limits

Trained on template-rendered synthetic text; English only; small evaluation sets that resolve
roughly 3-4 points; the answer keys are mine and inconsistent on label spans. The 450-example
synthetic validation sets were not run for the final adapter. Always validate output against your
schema and use constrained decoding when you need hard guarantees.

## Licence

Apache-2.0 (code, data, adapter). Base model Qwen3-4B-Instruct-2507 is Apache-2.0.
