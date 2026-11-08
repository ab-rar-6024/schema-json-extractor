# Resuming v3 — evaluation only, no retraining

The Colab runtime was reclaimed after v3 finished training. **The model is not lost.**

## What survived

`/content/drive/MyDrive/sf-v3-ckpt/` on the Google account used for the run
(`authuser=5`). With `--save-steps 25` and `save_total_limit=2`, that holds the last
two checkpoints: **`checkpoint-225` and `checkpoint-250`**.

Training ran exactly 250 steps, so **`checkpoint-250` is the finished model.** A PEFT
checkpoint contains `adapter_model.safetensors` and `adapter_config.json` alongside the
optimiser state, so it can be loaded as an adapter directly — identical weights to the
`/content/schemaforge-v3/adapter` that was lost with the VM.

Check it at drive.google.com before starting, to confirm `checkpoint-250` is there.

## What was lost (all cheap to replace)

- `/content/out3` — the dataset. Rebuilds deterministically, but see the warning below.
- The 13 uploaded source files.
- `/content/ev3` — eval results. The four passes had only just started.

## IMPORTANT: evaluate against the data v3 was trained on

v3 trained on the dataset built by the **old** `core.py`, whose `inject` profile named a
`status` field that no schema has. That generator has since been fixed, so rebuilding
with the current `core.py` produces a **different** dataset (`out_v3b`), which is the
wrong yardstick for v3.

Avoid the problem entirely: upload the two val files straight from
`D:\Forge\schemaforge\data\out_v3\` rather than rebuilding. They are 2.4 MB each, and
evaluation never needs `train.jsonl`, `build.py`, `domains.py`, `catalog.py` or
`synth.py`.

Staged and ready to upload:
`...\scratchpad\resume_v3\` — `val_seen.jsonl`, `val_unseen.jsonl`, `evaluate.py`,
`report.py`, `slice.py`, `try_schema.py`, `cases.json` (~4.9 MB total).

## Tomorrow, in order

1. New notebook, **Runtime > Change runtime type > T4 GPU**.
2. Install cell:
   ```
   !pip install -q jsonschema "transformers<5" "tokenizers<0.22" "datasets<4" "peft>=0.14" "accelerate>=1.2" "bitsandbytes>=0.45"; pip uninstall -y -q torchao; nvidia-smi -L
   ```
3. Mount Drive (click through the consent popup yourself):
   ```
   from google.colab import drive; drive.mount('/content/drive')
   ```
4. Upload the seven files above, then put the val files where the scripts expect:
   ```
   !mkdir -p /content/out3 && mv /content/val_*.jsonl /content/out3/
   ```
5. Evaluate, pointing at the surviving checkpoint:
   ```
   !cd /content; M=Qwen/Qwen3-4B-Instruct-2507; A=/content/drive/MyDrive/sf-v3-ckpt/checkpoint-250; python evaluate.py --model $M --adapter $A --load-4bit --data out3/val_unseen.jsonl --tag tuned_unseen --out ev3; python evaluate.py --model $M --adapter $A --load-4bit --data out3/val_seen.jsonl --tag tuned_seen --out ev3; python evaluate.py --model $M --load-4bit --data out3/val_unseen.jsonl --tag base_unseen --out ev3; python evaluate.py --model $M --load-4bit --data out3/val_seen.jsonl --tag base_seen --out ev3
   ```
   ~2 h for 1800 generations. Results land in `ev3/` after each pass, so a disconnect
   only costs the pass in flight.
6. Report and slices:
   ```
   !cd /content; python report.py --dir ev3 --out MODEL_CARD_v3.md --name "SchemaForge v3"; cat MODEL_CARD_v3.md; python slice.py --data-dir out3 --dir ev3 --limit 450 --name "SchemaForge v3"
   ```
   (No `--data-dir` on `report.py`: that needs `train.jsonl`, which we are not uploading.
   The schema/domain/null-rate lines will fall back to generic text; the metrics table is
   unaffected.)
7. **First thing after the evals:** copy the adapter somewhere durable.
   ```
   !cp -r /content/drive/MyDrive/sf-v3-ckpt/checkpoint-250 /content/drive/MyDrive/schemaforge-v3-adapter
   !cd /content && tar -czf /content/drive/MyDrive/sf-v3-evals.tgz ev3
   ```

## Already done, nothing to redo

- v3 trained: `train_loss 0.00973`, `eval_loss 0.00066`, 174.9 min, no NaN in fp16.
- Hand-written four-case test run for both v3 and base Qwen3-4B: 39/41 (95.1%) each.
- Injection failure diagnosed and fixed in `core.py` / `build.py`; fix verified in the
  data (266/266 valid) but **not yet tested against a model** — that is a v4 run.
- Written up in `FINDINGS_v3.md`.
