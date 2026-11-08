# SchemaForge v3 - evaluation results

Adapter: `sf-v3-ckpt/checkpoint-250` (Qwen3-4B-Instruct-2507, Apache 2.0).
Eval data: `data/out_v3/val_seen.jsonl` and `val_unseen.jsonl` (450 each) - the data v3 was
trained against, NOT the rebuilt `out_v3b`.

## Provenance - read this first

These numbers are transcribed from the Colab notebook output (`authuser=4`, notebook
`Untitled1`). The runtime was reclaimed by the GPU usage limit while the fourth pass was at
448/450, so:

- `base_seen` is **missing** (it never wrote its metrics file).
- The `preds_*.jsonl` files went with the VM, so **`slice.py` has not been run on v3** -
  there is no per-noise-profile or per-domain breakdown yet.
- `report.py` was not run; this table was assembled by hand from the three printed JSON
  blocks.

## Results (n = 450 per cell)

```
metric                    base_unseen   tuned_seen   tuned_unseen
-----------------------------------------------------------------
valid_json_rate               100.0%       100.0%        100.0%
schema_pass_rate               97.3%       100.0%        100.0%
field_accuracy                 88.6%        99.7%         97.9%
nonnull_field_accuracy         91.6%        99.7%         98.0%
null_abstention_rate           82.1%        99.6%         98.2%
hallucination_rate             17.9%         0.4%          1.8%
missed_as_null_rate             3.4%         0.0%          0.6%
list_set_f1                    97.3%        99.5%        100.0%
exact_record_rate              43.1%        97.3%         86.0%
extra_keys_total                  35            0             8
missing_keys_total                62            0             9
```

All 900 tuned generations parsed directly (parse_modes: direct = 450 in both passes).

## Against v2 (different base model, different eval draw)

```
                          v2 base   v3 base   v2 tuned   v3 tuned     (unseen)
field_accuracy             81.6%     88.6%     94.7%      97.9%
hallucination_rate         29.0%     17.9%      1.9%       1.8%
missed_as_null_rate         7.8%      3.4%      4.0%       0.6%
exact_record_rate          24.4%     43.1%     67.3%      86.0%
```

What the comparison does and does not say:

- The unseen sets are not the same examples: v3's came from the generator after the
  `inject` profile was added, which changes the random stream. Schemas are the same 54.
- The base model also changed (Qwen2.5-3B -> Qwen3-4B). Qwen3-4B untuned is already 7 points
  better on field accuracy (81.6% -> 88.6%) and has far fewer hallucinations (29.0% ->
  17.9%). That alone accounts for roughly twice the improvement the tuned model shows
  (94.7% -> 97.9%), so the stronger base is the larger part of v3's number.
- Tuning still adds a lot over its own base: +9.3 points field accuracy, hallucination
  17.9% -> 1.8% (10x), exact-record 43% -> 86%. That is smaller than v2's gain over its
  base (+13.1 points) because there is less headroom.
- `missed_as_null_rate` is the one metric where v3 tuned moved most on its own: 4.0% -> 0.6%
  while hallucination held flat. That is the over-abstention fix v2 needed.

## Caveat that still applies

This eval shares a generator with the training data. The hand-written four-case test (same
adapter) tied v3 with its own untuned base at 39/41, and both obeyed the injected
instruction. See `FINDINGS_v3.md`. These numbers describe fit to the synthetic
distribution, not general extraction skill.

## Not yet done

1. `base_seen` (needs a GPU session; ~27 min).
2. `slice.py` per-profile / per-domain breakdown - needs the predictions regenerated, i.e.
   re-running the tuned passes (~1 h for both).
3. `incident` / `users` follow-up from `FINDINGS_v2.md`: unknown whether v3 fixed it,
   because the domain breakdown needs the slice run.
