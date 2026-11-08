# Where v1 is actually weak

Produced by `eval/slice.py`, which re-scores the predictions v1 already wrote
(`eval_results/preds_*.jsonl`) over subsets. No GPU, no regeneration.

Caveat on every number below: 120 examples sliced 12 ways gives cells of n=5-26.
These are directional. Re-run at the full 450 before trusting any single cell.

## Seen schemas: saturated

Hallucination is 0.0% in every domain but email (3.7%). Field accuracy 98.5-100%.
There is nothing left to learn on this distribution - more epochs would only overfit
the templates.

## Unseen, by noise profile (the stress tests from the plan)

| profile | n | hallucination base -> v1 | field acc base -> v1 |
| --- | --- | --- | --- |
| clean | 44 | 35.4% -> 8.3% | 84.4% -> 94.2% |
| distract | 18 | 46.7% -> 0.0% | 85.7% -> 95.9% |
| typos | 12 | 38.9% -> 5.6% | 81.0% -> 93.7% |
| foreign | 15 | 34.5% -> 10.3% | 77.9% -> 91.8% |
| long | 15 | 34.2% -> 2.6% | 81.0% -> 94.8% |
| contradict | 16 | 31.8% -> 0.0% | 77.9% -> 97.7% |

Distractor sentences and contradictory text are handled cleanly. **Mixed-language text
is the weakest profile** on both metrics.

## Unseen, by domain

Fully held-out domains (never trained at all): incident 0.0% halluc / 98.1% acc,
shipment 2.2% / 98.5%, invoice 7.7% / 93.1%.

Unseen *third schema variant* of a trained domain: job 21.4% / 89.8%,
property 20.0% / 95.8%, meeting 10.0% / 87.5%; the rest 0.0% halluc.

A whole new domain is not the hard case. Specific schema shapes are.

## Weakest fields (unseen)

| field | accuracy | n |
| --- | --- | --- |
| meeting_audit.owner_of_first_action | 33.3% | 6 |
| receipt_expense.item_count | 41.7% | 12 |
| review_summary.headline | 42.9% | 7 |
| invoice_ap.line_count | 50.0% | 10 |
| news_digest.quote | 50.0% | 8 |
| job_screen.closes_on | 57.1% | 7 |
| property_agent.amenities | 66.7% | 6 |
| meeting_audit.subject | 66.7% | 6 |

Two clear classes, neither of which is copy-the-value extraction:

1. **Derived fields** - `item_count`, `line_count`, `owner_of_first_action`. These require
   counting or selecting, not copying.
2. **Span fields** - `headline`, `quote`, `subject`, `amenities`. Free text, scored by
   exact match, so a near-miss scores zero.

## The data defect this exposes

`audit.py:71` exempts any field whose leaf name ends in `count` from the groundedness
check:

```python
if leaf in PARAPHRASED or leaf.endswith("count"):
```

So the one class of field the quality gate never verified is the class the model is worst
at. Those targets were never confirmed to be derivable from the text at all - for some
rows the model may have been trained on noise. Fix this before anything else in v2; it is
cheap and it is a known-bad input rather than a guess.

---

# v2 progress: data fixes (done)

## 1. Noise could land inside a structured block

`core.apply_noise` inserted at `rng.randrange(len(lines) + 1)` - a uniformly random
line - so a distractor could be dropped between two product rows of a receipt tape or
two billed lines of an invoice, where it is indistinguishable from a line item. The
target said 5 because the record held 5 items; the rendered text genuinely showed 6.

Renderers now wrap such runs with `core.atomic(...)` and the noise layer only inserts at
points outside those blocks. Verified on the held-out receipts: injected lines inside the
tape went **2 -> 0**.

Note on an earlier mis-read: the derived-count *presence* logic was never broken.
`build.py:155-159` already mirrors each derived count to its source list, so a count is
non-null only when the list is rendered. The defect was purely in where noise landed.

## 2. The audit never checked counts

`audit.py` exempted every field whose name ends in `count`. That was the one class the
quality gate skipped, and the class v1 scored worst on. Replaced with:

- **tabular counts** (`item_count`, `line_count` at the top level) - verified by counting
  the `<qty> x <rate> <amount>` rows in the text;
- **list-derived counts** (`participant_count`, `action_count`, ...) - named explicitly in
  `LIST_DERIVED_COUNTS` and exempt with a stated reason, since the renderer always emits
  the whole list and noise can no longer add to it;
- **stated counts** (shipment's `parcel.item_count`, `retry_count`, `headcount`) - now go
  through the ordinary numeric groundedness check, which they previously skipped.

Running the new audit against the **v1** data flags 29 rows (6.44% of `val_unseen`).
Against the rebuilt data: **0**.

## 3. Ambiguous count descriptions

`line_count` was described as "number of billed lines". On an invoice reading
`support retainer  23 x 657.68 EUR`, v1 answered 23 - it took the quantity. The three
count descriptions now say "count the lines, not the quantities on them".

## Result

Rebuilt to `data/out_v2/` (same 4000/450/450 split, seed 7). Audit: 0 ungrounded values
across all 7,900 rows, with the count fields actually being checked for the first time.

## Still to do for v2

- Expand 36 -> ~100 schemas, deeper nesting, longer documents.
- Retrain and re-evaluate at the full 450 per split (v1's per-slice cells were n=5-26).
