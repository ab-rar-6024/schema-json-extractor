"""Groundedness audit.

For every non-null scalar in the expected JSON, check that some surface form of that
value really appears in the input text.  Anything flagged here is a generator bug: the
target states something the text does not, which would teach the model to hallucinate.
Booleans are not checkable this way and are skipped.

    python audit.py ../out/train.jsonl
"""
import datetime
import json
import re
import sys
from collections import Counter

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]

# Currency codes are stated by their symbol, which is an unambiguous mapping in this
# dataset, so accept either form.
SYMBOL = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹",
          "JPY": "¥", "BRL": "R$", "SEK": "kr"}
# Fields the text states semantically rather than verbatim: these are deliberate
# inference targets, not groundedness bugs.
PARAPHRASED = {"request_type", "intent", "listing_status", "status", "payment_state",
               "delivery_state", "sentiment", "overall_sentiment"}
WORD_NUM = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def num_grounded(v, text, low):
    cands = set()
    if int(v) in WORD_NUM and abs(v - int(v)) < 1e-9:
        cands.add(WORD_NUM[int(v)])
    if abs(v - round(v)) < 1e-9:
        iv = int(round(v))
        cands |= {"%d" % iv, "{:,}".format(iv), "%.2f" % v, "{:,.2f}".format(v),
                  "%.1f" % v}
    else:
        cands |= {"%.2f" % v, "{:,.2f}".format(v), "%.1f" % v, repr(v), "%g" % v}
    return any(c.lower() in low for c in cands)


def str_grounded(v, text, low):
    s = v.strip()
    if not s:
        return True
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try:
            d = datetime.date.fromisoformat(s)
        except ValueError:
            return False
        if s in text:
            return True
        y, dd = str(d.year), str(d.day)
        month_ok = (MONTHS[d.month - 1][:3] in low or ("%02d" % d.month) in text
                    or str(d.month) in text)
        return y in text and (dd in text or ("%02d" % d.day) in text) and month_ok
    if re.fullmatch(r"\d{2}:\d{2}", s):
        h, m = int(s[:2]), int(s[3:])
        h12 = h % 12 or 12
        return any(p in text for p in ["%02d:%02d" % (h, m), "%d:%02d" % (h, m),
                                       "%d:%02d" % (h12, m)]) or \
            (m == 0 and re.search(r"\b%d\s*(AM|PM)" % h12, text) is not None)
    variants = {s.lower(), s.lower().replace("-", " "), s.lower().replace(" ", "-"),
                s.lower().replace("_", " ")}
    return any(v2 in low for v2 in variants)


# A count has no surface form of its own, so v1 exempted every *count field from
# the audit entirely. That was the one class the quality gate never checked, and
# it turned out to be the class v1 scored worst on (item_count 41.7%,
# line_count 50.0%). Counts that summarise a rendered table are now verified by
# counting the rows; counts stated outright in the text (retry_count, headcount,
# attendee_count, followup_count) go through the ordinary numeric check.
#
# A count is grounded if the number is stated outright ("7 item(s) in this
# shipment") OR it equals the number of "<qty> x <rate> <amount>" rows rendered.
# Checking both, rather than keying on where the field sits, keeps this correct
# when a synthesised schema moves the field or renames it.
ROW_COUNTED = {"item_count", "line_count"}
# x{1,2} because the typo layer doubles characters: "1 x" becomes "1 xx" and the
# row would otherwise go uncounted, flagging a correct target.
ROW_RE = re.compile(r"\d+\s*x{1,2}\s", re.I)
# Counts over a list that the renderer always emits in full, and that noise
# cannot add to now that the blocks are atomic ("Present: a, b, c" on one line,
# "  * action" bullets). They have no surface form and no row shape to count, so
# they stay exempt - but named explicitly, not by a blanket *count suffix.
LIST_DERIVED_COUNTS = {"participant_count", "attendee_count",
                       "action_count", "followup_count"}


def rows_in(text):
    return sum(1 for ln in text.split("\n") if ROW_RE.search(ln))


def norm(name):
    """Match field names across naming styles: requestType == request_type."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


PARAPHRASED_N = set(norm(x) for x in PARAPHRASED)
LIST_DERIVED_N = set(norm(x) for x in LIST_DERIVED_COUNTS)
ROW_COUNTED_N = set(norm(x) for x in ROW_COUNTED)


def exempt(obj, path):
    leaf = path[-1] if path else ""
    if norm(leaf) in PARAPHRASED_N or norm(leaf) in LIST_DERIVED_N:
        return True
    if isinstance(obj, str) and obj in SYMBOL and "curren" in leaf.lower():
        return True
    return False


def walk(obj, text, low, path, bad):
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, text, low, path + [k], bad)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, text, low, path + ["[]"], bad)
    elif isinstance(obj, bool) or obj is None:
        return
    elif exempt(obj, path):
        if isinstance(obj, str) and obj in SYMBOL and SYMBOL[obj].lower() not in low \
                and obj.lower() not in low:
            bad.append((".".join(path), obj))
        return
    elif isinstance(obj, (int, float)):
        leaf = path[-1] if path else ""
        if norm(leaf) in ROW_COUNTED_N:
            seen = rows_in(text)
            if int(obj) != seen and not num_grounded(float(obj), text, low):
                bad.append((".".join(path), "%s but text shows %d rows" % (obj, seen)))
        elif not num_grounded(float(obj), text, low):
            bad.append((".".join(path), obj))
    elif isinstance(obj, str):
        if not str_grounded(obj, text, low):
            bad.append((".".join(path), obj))


def main(paths):
    for path in paths:
        rows = [json.loads(l) for l in open(path, encoding="utf-8")]
        offenders = Counter()
        examples = {}
        total_fields = 0
        bad_rows = 0
        for r in rows:
            bad = []
            low = r["text"].lower()
            walk(r["expected"], r["text"], low, [], bad)
            total_fields += r["total_fields"]
            if bad:
                bad_rows += 1
                for p, v in bad:
                    key = "%s :: %s" % (r["schema_id"], p)
                    offenders[key] += 1
                    examples.setdefault(key, (r["id"], v, r["noise"]))
        print("\n== %s" % path)
        print("rows=%d  rows_with_ungrounded_values=%d (%.2f%%)  fields=%d" %
              (len(rows), bad_rows, 100.0 * bad_rows / max(len(rows), 1), total_fields))
        for key, n in offenders.most_common(25):
            rid, v, noise = examples[key]
            print("  %4d  %-46s e.g. %r  (%s, noise=%s)" % (n, key, v, rid, noise))


if __name__ == "__main__":
    main(sys.argv[1:] or ["../out/train.jsonl"])
