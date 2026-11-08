# v4 plan

Trigger: the independent eval (`RESULTS_ood_v3.md`) tied v3 with its own untuned base
(95.4% vs 95.7%) and v3 obeyed 8 of 9 injected instructions, so the pre-registered rule
said MOVE TO v4 instead of publishing.

## What the eval showed, and the data change for each

| finding | cause | v4 change |
|---|---|---|
| Tuned model shortens spans: 'Fall 2025' -> 'Fall', 'Track B' -> 'B', 'Room 204' -> '204', 'Cafe Aurora' -> 'Aurora', 'US 11,234,567 B2' -> '11234567' | v3 training targets had 0 of 25,185 string values starting 'Track ', 'Fall ', 'Spring ' or 'Cafe ', and 43 starting 'Room ': the model never saw a target keep its qualifier | 3 new domains (`data/gen/domains_v4.py`): cinema booking, warehouse goods-in, maintenance request. Targets such as 'Screen 3', 'Row F', 'Seat 12', 'Bay 12', 'Aisle C', 'SKU-88213', 'Flat 7C', 'Block B', 'Floor 3', 'Spring 2026', 'Week 32', 'Studio ...', 'Cinema ...', 'Cafe ...' |
| Both models obey embedded instructions (8/9) | v3 only attacked fields whose true value is null; 4 of 9 eval attacks instead override a STATED value | attacks of both kinds (`core.py`): null-targeted, override-a-stated-value, and generic; 18% of rows |
| v3 attack phrasings were copied from the eval | made the injection result unmeasurable | every v4 phrasing is new: no HTML comments, no `assistant:` prefix, no 'NOTE TO ANY AUTOMATED READER', no '[[ADMIN OVERRIDE]]' |

The three new domains are NOT domains in `eval/ood`, so that set still measures transfer of
the skill (keep the whole span) and not memorisation.

## Dataset checks (data/out_v4, built locally; Colab rebuild must match)

- 4000 / 450 / 450 rows, 72 train schemas, 63 unseen, **0 ungrounded** on all three splits.
- The audit caught a real bug in the first build of the new cinema domain (a layout that
  rendered only the first name while the target held the full name); fixed before training.
- 716 attack rows (17.9%): 653 override lines, 293 null-targeted, 186 generic.
  0 null-targeted attacks name a field that is not genuinely null; 0 override attacks name an
  unstated field or dictate the true value.
- Leak check against the 10 eval injection lines: 1 distinct shared 4-gram ('must be n a',
  9 training lines), out of 71 eval 4-grams compared with 1,132 training attack lines.

## Gate (same rule as v3, fixed in `eval/ood/eval_ood.py`, not to be edited after results)

    PUBLISH  iff  tuned field accuracy >= untuned-base accuracy + 2.0 points
             AND  tuned invented-value count <= base invented-value count
    otherwise     no publish; revisit the data

Reported alongside, not gating: injection obedience (v3: 8/9, tuned and base), and the span
errors listed above. v4 is judged on whether those specific failures move, not only on the
aggregate.

## Known limits of the gate

48 cases / 393 fields resolves roughly 3-4 points. A result inside that band is "no
evidence", not "proof of no effect". If v4 lands near the threshold the right next step is
widening the eval set, not relaxing the rule.

## Run

Qwen3-4B-Instruct-2507, fp16 on a T4, batch 1 x accum 16, 1 epoch over 4000 examples,
~250 steps, about 3 h. Checkpoint every 25 steps to Drive (`--ckpt-dir`) so a reclaimed
runtime costs minutes, not the run.

---

## Outcome (v4 trained and evaluated)

Gate result: **PUBLISH, narrowly** - tuned 98.0% vs base 95.7% (+2.3 points; +2.04 if the one
schema-invalid enum is counted as an error), invented 2 vs 4, injection obeyed 2/9 vs 8/9,
sign-test p = 0.049. Full numbers, what moved and what is still wrong: `RESULTS_ood_v4.md`.
The final adapter is in the authuser=0 Drive at `sf-v4-final` (sha256 18fb0580...bf7a).
Publishing to Hugging Face still needs the owner's own token; nothing has been published.

## Fresh-set check and release prep

Fresh 44-case set (`eval/ood2/`, written after v4 was frozen): rule PASS (93.4% vs 90.0%, invented
0 vs 3, injection obeyed 0/9 vs 9/9; p = 0.12 alone). Split by case type the gain is almost all
injection resistance; ordinary extraction is about equal to the base. See `RESULTS_ood_fresh_v4.md`.
Release folder: `release_v4/upload_v4/` (adapter sha256 18fb0580...bf7a verified after download;
safetensors header validated; no personal paths). Target: huggingface.co/abr-6024/schemaforge-v4,
public. Upload is run by the owner with their own token.
