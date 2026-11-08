"""Twelve source domains, each with a world-state sampler, three schema variants
and a multi-style renderer.

The record is sampled first, a subset of its fields is marked "present", and only
present fields are rendered into the text.  The expected JSON is therefore correct
by construction, and absent fields are the null-handling training signal.
"""
from core import (CITIES, COUNTRIES, COMPANIES, CURRENCIES, DEPARTMENTS, JOB_TITLES,
                  PRODUCTS, SKILLS, STREETS, LIST_KEY, COLLAPSE,
                  atomic, date, email, fmt_date, fmt_money, fmt_time, iso, money,
                  name, phone,
                  root, s_arr, s_bool, s_date, s_enum, s_int, s_num, s_obj, s_str)


def j(parts, sep=" "):
    return sep.join(p for p in parts if p)


# =============================================================== 1. review
REV_SENT = ["positive", "neutral", "negative"]


def w_review(rng):
    prod, cat = rng.choice(PRODUCTS)
    rating = rng.randrange(1, 6)
    cur = rng.choice(CURRENCIES)
    pros = rng.sample(["light", "well built", "good battery life", "quiet", "easy to clean",
                       "fast delivery", "great value", "looks premium", "simple setup"],
                      rng.randrange(1, 4))
    cons = rng.sample(["pricey", "flimsy lid", "loud fan", "short cable", "poor manual",
                       "slow to heat", "scratches easily", "awkward buttons"],
                      rng.randrange(1, 3))
    return {
        "product": prod, "category": cat, "rating": rating,
        "reviewer": name(rng), "review_date": iso(date(rng)),
        "verified": rng.random() < 0.7,
        "pros": pros, "cons": cons,
        "recommend": rating >= 4,
        "price": money(rng, 9, 480), "currency": cur,
        "sentiment": REV_SENT[0] if rating >= 4 else (REV_SENT[1] if rating == 3 else REV_SENT[2]),
        "title": rng.choice(["Does the job", "Not what I hoped", "Excellent buy",
                             "Mixed feelings", "Would buy again", "Broke in a week"]),
        "store": rng.choice(COMPANIES),
    }


def r_review(w, present, rng):
    has = present.__contains__
    style = rng.randrange(3)
    stars = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}[w["rating"]] if has("rating") else None
    rate_txt = None
    if has("rating"):
        rate_txt = rng.choice(["%d/5" % w["rating"], "%d out of 5 stars" % w["rating"],
                               "%s stars" % stars, "Rating: %d" % w["rating"]])
    if style == 0:
        L = []
        if has("title"):
            L.append("**%s**" % w["title"])
        L.append(j([rate_txt, ("- " + w["product"]) if has("product") else None]))
        if has("category"):
            L.append("Category: %s" % w["category"])
        if has("reviewer"):
            L.append("By %s%s" % (w["reviewer"], ", verified purchase" if has("verified") and w["verified"]
                                 else (", unverified" if has("verified") else "")))
        elif has("verified"):
            L.append("Verified purchase" if w["verified"] else "Unverified purchase")
        if has("review_date"):
            L.append("Posted %s" % fmt_date(date_of(w["review_date"]), rng))
        if has("price"):
            L.append("Paid %s" % fmt_money(w["price"], w["currency"] if has("currency") else "USD", rng))
        if has("store"):
            L.append("Bought from %s" % w["store"])
        if has("pros"):
            L.append("What I liked: " + ", ".join(w["pros"]) + ".")
        if has("cons"):
            L.append("Downsides: " + ", ".join(w["cons"]) + ".")
        if has("recommend"):
            L.append("Would I recommend it? %s." % ("Yes" if w["recommend"] else "No"))
        if has("sentiment"):
            L.append("Overall tone: %s." % w["sentiment"])
        return "\n".join(L)
    if style == 1:
        s = []
        if has("title"):
            s.append("%s." % w["title"])
        s.append(j(["I bought the %s" % w["product"] if has("product") else "I bought this",
                    "from %s" % w["store"] if has("store") else None,
                    "on %s" % fmt_date(date_of(w["review_date"]), rng) if has("review_date") else None]) + ".")
        if has("price"):
            s.append("It cost me %s." % fmt_money(w["price"], w["currency"] if has("currency") else "USD", rng))
        if has("pros"):
            s.append("Good points: it is %s." % ", ".join(w["pros"]))
        if has("cons"):
            s.append("Less good: %s." % ", ".join(w["cons"]))
        if rate_txt:
            s.append("I would give it %s." % rate_txt.lower())
        if has("recommend"):
            s.append("I %s recommend it to a friend." % ("would" if w["recommend"] else "would not"))
        if has("verified"):
            s.append("(Purchase %s by the store.)" % ("confirmed" if w["verified"] else "not confirmed"))
        if has("reviewer"):
            s.append("- %s" % w["reviewer"])
        if has("category"):
            s.append("Filed under %s." % w["category"])
        if has("sentiment"):
            s.append("Sentiment label: %s." % w["sentiment"])
        return " ".join(s)
    L = ["=== CUSTOMER FEEDBACK ==="]
    for label, key, fn in [("Item", "product", str), ("Dept", "category", str),
                           ("Score", "rating", lambda v: "%d" % v),
                           ("Author", "reviewer", str),
                           ("Date", "review_date", lambda v: fmt_date(date_of(v), rng)),
                           ("Verified", "verified", lambda v: "Y" if v else "N"),
                           ("Retailer", "store", str),
                           ("Headline", "title", str),
                           ("Tone", "sentiment", str),
                           ("Recommends", "recommend", lambda v: "yes" if v else "no")]:
        if has(key):
            L.append("%-10s: %s" % (label, fn(w[key])))
    if has("price"):
        L.append("%-10s: %s" % ("Price", fmt_money(w["price"], w["currency"] if has("currency") else "USD", rng)))
    if has("pros"):
        L += ["+ %s" % p for p in w["pros"]]
    if has("cons"):
        L += ["- %s" % c for c in w["cons"]]
    return "\n".join(L)


def date_of(isostr):
    import datetime
    return datetime.date.fromisoformat(isostr)


def sc_review():
    a = root({
        "product_name": s_str("name of the product reviewed"),
        "rating": s_int("star rating 1-5", minimum=1, maximum=5),
        "reviewer_name": s_str(),
        "review_date": s_date(),
        "verified_purchase": s_bool(),
        "recommended": s_bool(),
        "sentiment": s_enum(REV_SENT),
    }, title="ProductReview")
    ta = {"product_name": "$product", "rating": "$rating", "reviewer_name": "$reviewer",
          "review_date": "$review_date", "verified_purchase": "$verified",
          "recommended": "$recommend", "sentiment": "$sentiment"}
    b = root({
        "item": s_obj({"name": s_str(), "category": s_str()}, nullable_obj=True),
        "score": s_int(minimum=1, maximum=5),
        "pricePaid": s_num("numeric amount only, no currency symbol"),
        "currency": s_enum(CURRENCIES, "ISO 4217 code"),
        "pros": s_arr(s_str(), "short positive points, empty-safe"),
        "cons": s_arr(s_str()),
        "retailer": s_str(),
    }, required=["item", "score", "pricePaid", "currency", "pros", "cons", "retailer"],
        title="ReviewDetail")
    tb = {"item": {COLLAPSE: True, "name": "$product", "category": "$category"},
          "score": "$rating", "pricePaid": "$price", "currency": "$currency",
          "pros": {LIST_KEY: "pros", "item": None}, "cons": {LIST_KEY: "cons", "item": None},
          "retailer": "$store"}
    c = root({
        "headline": s_str("the review title if one is given"),
        "author": s_str(),
        "posted_on": s_date(),
        "stars": s_int(minimum=1, maximum=5),
        "overall_sentiment": s_enum(REV_SENT),
        "positives": s_arr(s_str()),
        "negatives": s_arr(s_str()),
        "would_recommend": s_bool(),
        "amount_paid": s_num(),
    }, title="ReviewSummary")
    tc = {"headline": "$title", "author": "$reviewer", "posted_on": "$review_date",
          "stars": "$rating", "overall_sentiment": "$sentiment",
          "positives": {LIST_KEY: "pros", "item": None},
          "negatives": {LIST_KEY: "cons", "item": None},
          "would_recommend": "$recommend", "amount_paid": "$price"}
    return [("review_core", a, ta), ("review_detail", b, tb), ("review_summary", c, tc)]


# =============================================================== 2. ticket
TK_PRIO = ["low", "medium", "high", "urgent"]
TK_CAT = ["billing", "shipping", "technical", "account", "returns", "other"]
TK_STATUS = ["open", "pending", "escalated", "resolved", "closed"]


def w_ticket(rng):
    who = name(rng)
    prod, _ = rng.choice(PRODUCTS)
    return {
        "ticket_id": "TK-%05d" % rng.randrange(10000, 99999),
        "customer": who, "customer_email": email(rng, who),
        "customer_phone": phone(rng),
        "product": prod,
        "summary": rng.choice([
            "device will not power on after update",
            "charged twice for the same order",
            "parcel marked delivered but not received",
            "cannot reset account password",
            "wrong size shipped, needs exchange",
            "app crashes when opening settings",
            "refund still not credited after two weeks"]),
        "priority": rng.choice(TK_PRIO), "category": rng.choice(TK_CAT),
        "status": rng.choice(TK_STATUS),
        "created": iso(date(rng, -200, 0)),
        "order_id": "ORD-%d" % rng.randrange(100000, 999999),
        "agent": name(rng), "department": rng.choice(DEPARTMENTS),
        "eta": iso(date(rng, 1, 40)),
        "refund_amount": money(rng, 5, 600), "currency": rng.choice(CURRENCIES),
    }


def r_ticket(w, present, rng):
    has = present.__contains__
    style = rng.randrange(3)
    if style == 0:
        L = []
        if has("ticket_id"):
            L.append("Ticket: %s" % w["ticket_id"])
        if has("created"):
            L.append("Opened: %s" % fmt_date(date_of(w["created"]), rng))
        if has("customer"):
            L.append("Customer: %s" % w["customer"])
        if has("customer_email"):
            L.append("Email: %s" % w["customer_email"])
        if has("customer_phone"):
            L.append("Phone: %s" % w["customer_phone"])
        if has("order_id"):
            L.append("Order: %s" % w["order_id"])
        if has("product"):
            L.append("Product: %s" % w["product"])
        if has("category"):
            L.append("Queue: %s" % w["category"])
        if has("priority"):
            L.append("Priority: %s" % w["priority"].upper())
        if has("status"):
            L.append("Status: %s" % w["status"])
        if has("agent"):
            L.append("Assigned to: %s%s" % (w["agent"], " (%s)" % w["department"] if has("department") else ""))
        elif has("department"):
            L.append("Team: %s" % w["department"])
        if has("eta"):
            L.append("Target resolution: %s" % fmt_date(date_of(w["eta"]), rng))
        if has("refund_amount"):
            L.append("Refund requested: %s" % fmt_money(w["refund_amount"],
                     w["currency"] if has("currency") else "USD", rng))
        if has("summary"):
            L.append("")
            L.append("Issue: %s." % w["summary"].capitalize())
        return "\n".join(L)
    if style == 1:
        s = ["Hi,"]
        s.append(j(["My name is %s" % w["customer"] if has("customer") else "I am writing",
                    "and I have a problem with %s" % (w["product"] if has("product") else "my order")]) + ".")
        if has("summary"):
            s.append("The problem: %s." % w["summary"])
        if has("order_id"):
            s.append("My order number is %s." % w["order_id"])
        if has("refund_amount"):
            s.append("I would like a refund of %s." % fmt_money(w["refund_amount"],
                     w["currency"] if has("currency") else "USD", rng))
        if has("priority"):
            s.append("Please treat this as %s priority." % w["priority"])
        if has("customer_email"):
            s.append("You can reach me at %s." % w["customer_email"])
        if has("customer_phone"):
            s.append("Or by phone on %s." % w["customer_phone"])
        if has("created"):
            s.append("I first contacted you on %s." % fmt_date(date_of(w["created"]), rng))
        body = " ".join(s)
        tail = []
        if has("ticket_id"):
            tail.append("[auto-reply: your reference is %s]" % w["ticket_id"])
        if has("category"):
            tail.append("[routed to: %s]" % w["category"])
        if has("status"):
            tail.append("[state: %s]" % w["status"])
        if has("agent"):
            tail.append("[owner: %s]" % w["agent"])
        if has("department"):
            tail.append("[team: %s]" % w["department"])
        if has("eta"):
            tail.append("[eta: %s]" % fmt_date(date_of(w["eta"]), rng))
        return body + ("\n\n" + "\n".join(tail) if tail else "")
    L = ["--- CRM NOTE ---"]
    if has("customer"):
        L.append("Spoke with %s today." % w["customer"])
    if has("summary"):
        L.append("They report: %s." % w["summary"])
    if has("product"):
        L.append("Item involved is the %s." % w["product"])
    if has("order_id"):
        L.append("Linked order %s." % w["order_id"])
    if has("ticket_id"):
        L.append("Logged under %s." % w["ticket_id"])
    if has("priority") and has("category"):
        L.append("Set to %s priority in the %s queue." % (w["priority"], w["category"]))
    elif has("priority"):
        L.append("Set to %s priority." % w["priority"])
    elif has("category"):
        L.append("Filed in the %s queue." % w["category"])
    if has("status"):
        L.append("Current status is %s." % w["status"])
    if has("agent"):
        L.append("I have handed it to %s." % w["agent"])
    if has("department"):
        L.append("%s will own the follow-up." % w["department"])
    if has("eta"):
        L.append("Promised an answer by %s." % fmt_date(date_of(w["eta"]), rng))
    if has("refund_amount"):
        L.append("Possible refund value %s." % fmt_money(w["refund_amount"],
                 w["currency"] if has("currency") else "USD", rng))
    if has("customer_email"):
        L.append("Contact: %s" % w["customer_email"])
    if has("customer_phone"):
        L.append("Tel: %s" % w["customer_phone"])
    if has("created"):
        L.append("Case created %s." % fmt_date(date_of(w["created"]), rng))
    return "\n".join(L)


def sc_ticket():
    a = root({
        "ticket_id": s_str(),
        "customer_name": s_str(),
        "customer_email": s_str("email address exactly as written"),
        "issue_summary": s_str("one short sentence describing the problem"),
        "priority": s_enum(TK_PRIO),
        "category": s_enum(TK_CAT),
        "created_date": s_date(),
    }, title="SupportTicket")
    ta = {"ticket_id": "$ticket_id", "customer_name": "$customer",
          "customer_email": "$customer_email", "issue_summary": "$summary",
          "priority": "$priority", "category": "$category", "created_date": "$created"}
    b = root({
        "reference": s_str(),
        "contact": s_obj({"name": s_str(), "email": s_str(), "phone": s_str()}),
        "order": s_obj({"order_id": s_str(), "product": s_str()}, nullable_obj=True),
        "severity": s_enum(TK_PRIO),
        "state": s_enum(TK_STATUS),
        "assignee": s_obj({"agent": s_str(), "department": s_str()}, nullable_obj=True),
        "resolution_due": s_date(),
    }, title="TicketRouting")
    tb = {"reference": "$ticket_id",
          "contact": {"name": "$customer", "email": "$customer_email", "phone": "$customer_phone"},
          "order": {COLLAPSE: True, "order_id": "$order_id", "product": "$product"},
          "severity": "$priority", "state": "$status",
          "assignee": {COLLAPSE: True, "agent": "$agent", "department": "$department"},
          "resolution_due": "$eta"}
    c = root({
        "caseNumber": s_str(),
        "problem": s_str(),
        "refund": s_obj({"amount": s_num(), "currency": s_enum(CURRENCIES)}, nullable_obj=True),
        "queue": s_enum(TK_CAT),
        "status": s_enum(TK_STATUS),
        "openedOn": s_date(),
        "ownerName": s_str(),
    }, required=["caseNumber", "problem", "refund", "queue", "status"], title="RefundCase")
    tc = {"caseNumber": "$ticket_id", "problem": "$summary",
          "refund": {COLLAPSE: True, "amount": "$refund_amount", "currency": "$currency"},
          "queue": "$category", "status": "$status", "openedOn": "$created",
          "ownerName": "$agent"}
    return [("ticket_core", a, ta), ("ticket_routing", b, tb), ("ticket_refund", c, tc)]


# =============================================================== 3. email
EM_REQ = ["approval", "information", "scheduling", "payment", "complaint", "introduction"]
EM_URG = ["low", "normal", "high"]


def w_email(rng):
    sender = name(rng)
    rec = name(rng)
    comp = rng.choice(COMPANIES)
    return {
        "sender": sender, "sender_email": email(rng, sender, comp),
        "recipient": rec, "recipient_email": email(rng, rec),
        "company": comp,
        "subject": rng.choice([
            "Q3 budget sign-off needed", "Revised supplier contract",
            "Site visit next week", "Invoice query", "New starter equipment",
            "Pricing for the Lisbon pilot", "Follow-up from Tuesday"]),
        "request_type": rng.choice(EM_REQ),
        "urgency": rng.choice(EM_URG),
        "due_date": iso(date(rng, 1, 90)),
        "meeting_date": iso(date(rng, 1, 60)),
        "meeting_time": (rng.randrange(8, 18), rng.choice([0, 15, 30, 45])),
        "amount": money(rng, 200, 90000), "currency": rng.choice(CURRENCIES),
        "attachments": rng.sample(["budget_v3.xlsx", "contract_draft.pdf", "floorplan.png",
                                   "invoice_8841.pdf", "notes.docx", "quote.pdf"],
                                  rng.randrange(1, 3)),
        "cc": [name(rng) for _ in range(rng.randrange(1, 3))],
        "phone": phone(rng),
    }


def r_email(w, present, rng):
    has = present.__contains__
    hdr = []
    if has("sender"):
        hdr.append("From: %s%s" % (w["sender"], " <%s>" % w["sender_email"] if has("sender_email") else ""))
    elif has("sender_email"):
        hdr.append("From: %s" % w["sender_email"])
    if has("recipient"):
        hdr.append("To: %s%s" % (w["recipient"], " <%s>" % w["recipient_email"] if has("recipient_email") else ""))
    elif has("recipient_email"):
        hdr.append("To: %s" % w["recipient_email"])
    if has("cc"):
        hdr.append("Cc: %s" % ", ".join(w["cc"]))
    if has("subject"):
        hdr.append("Subject: %s" % w["subject"])
    if has("urgency"):
        hdr.append("Importance: %s" % w["urgency"])
    if has("attachments"):
        hdr.append("Attachments: %s" % ", ".join(w["attachments"]))
    b = []
    b.append("Hi%s," % (" %s" % w["recipient"].split()[0] if has("recipient") else ""))
    if has("request_type"):
        b.append({"approval": "I need your approval on the item below.",
                  "information": "Could you send over the details below?",
                  "scheduling": "I would like to get a time in the diary.",
                  "payment": "This is about an outstanding payment.",
                  "complaint": "I have to raise a complaint about this.",
                  "introduction": "I wanted to introduce myself and my team."}[w["request_type"]])
    if has("amount"):
        b.append("The figure in question is %s." % fmt_money(w["amount"],
                 w["currency"] if has("currency") else "USD", rng))
    if has("due_date"):
        b.append("I need this closed off by %s." % fmt_date(date_of(w["due_date"]), rng))
    if has("meeting_date"):
        t = " at %s" % fmt_time(w["meeting_time"][0], w["meeting_time"][1], rng) if has("meeting_time") else ""
        b.append("Can we meet on %s%s?" % (fmt_date(date_of(w["meeting_date"]), rng), t))
    elif has("meeting_time"):
        b.append("Any chance of a call at %s?" % fmt_time(w["meeting_time"][0], w["meeting_time"][1], rng))
    if has("company"):
        b.append("Everything goes through %s on our side." % w["company"])
    b.append("Best regards,")
    if has("sender"):
        b.append(w["sender"])
    if has("phone"):
        b.append("Tel %s" % w["phone"])
    if has("sender_email"):
        b.append(w["sender_email"])
    return "\n".join(hdr) + "\n\n" + "\n".join(b)


def sc_email():
    a = root({
        "from_name": s_str(),
        "from_email": s_str(),
        "subject": s_str(),
        "request_type": s_enum(EM_REQ),
        "urgency": s_enum(EM_URG),
        "due_date": s_date(),
    }, title="EmailIntent")
    ta = {"from_name": "$sender", "from_email": "$sender_email", "subject": "$subject",
          "request_type": "$request_type", "urgency": "$urgency", "due_date": "$due_date"}
    b = root({
        "sender": s_obj({"name": s_str(), "email": s_str(), "phone": s_str(),
                         "organisation": s_str()}),
        "recipients": s_obj({"to": s_str(), "cc": s_arr(s_str())}),
        "money": s_obj({"amount": s_num(), "currency": s_enum(CURRENCIES)}, nullable_obj=True),
        "attachments": s_arr(s_str(), "file names mentioned as attached"),
    }, title="EmailParties")
    tb = {"sender": {"name": "$sender", "email": "$sender_email", "phone": "$phone",
                     "organisation": "$company"},
          "recipients": {"to": "$recipient", "cc": {LIST_KEY: "cc", "item": None}},
          "money": {COLLAPSE: True, "amount": "$amount", "currency": "$currency"},
          "attachments": {LIST_KEY: "attachments", "item": None}}
    c = root({
        "topic": s_str("the subject line"),
        "proposed_meeting": s_obj({"date": s_date(), "time": s_str("HH:MM 24-hour")},
                                  nullable_obj=True),
        "deadline": s_date(),
        "intent": s_enum(EM_REQ),
        "contact_name": s_str(),
        "copied_in": s_arr(s_str()),
    }, title="EmailAction")
    tc = {"topic": "$subject",
          "proposed_meeting": {COLLAPSE: True, "date": "$meeting_date", "time": "$meeting_time_iso"},
          "deadline": "$due_date", "intent": "$request_type", "contact_name": "$sender",
          "copied_in": {LIST_KEY: "cc", "item": None}}
    return [("email_intent", a, ta), ("email_parties", b, tb), ("email_action", c, tc)]


# =============================================================== 4. receipt
PAY = ["card", "cash", "mobile", "voucher", "bank transfer"]


def w_receipt(rng):
    cur = rng.choice(CURRENCIES)
    n = rng.randrange(2, 6)
    items = []
    for _ in range(n):
        nm, _c = rng.choice(PRODUCTS)
        q = rng.randrange(1, 4)
        up = money(rng, 2, 90)
        items.append({"name": nm, "qty": q, "unit_price": up,
                      "line_total": round(q * up, 2)})
    sub = round(sum(i["line_total"] for i in items), 2)
    rate = rng.choice([0.0, 0.05, 0.07, 0.19, 0.2, 0.23])
    tax = round(sub * rate, 2)
    return {
        "merchant": rng.choice(COMPANIES), "city": rng.choice(CITIES),
        "date": iso(date(rng, -300, 0)),
        "time": (rng.randrange(7, 22), rng.choice([0, 5, 12, 17, 23, 34, 41, 55])),
        "items": items, "subtotal": sub, "tax": tax,
        "total": round(sub + tax, 2), "currency": cur,
        "payment_method": rng.choice(PAY), "card_last4": "%04d" % rng.randrange(10000),
        "cashier": name(rng).split()[0], "receipt_no": "R%08d" % rng.randrange(10 ** 8),
        "tax_rate": round(rate * 100, 2),
    }


def r_receipt(w, present, rng):
    has = present.__contains__
    cur = w["currency"] if has("currency") else "USD"
    style = rng.randrange(2)
    L = []
    if has("merchant"):
        L.append(w["merchant"].upper() if style == 0 else w["merchant"])
    if has("city"):
        L.append("%s branch" % w["city"])
    if has("date") or has("time"):
        d = fmt_date(date_of(w["date"]), rng) if has("date") else ""
        t = fmt_time(w["time"][0], w["time"][1], rng) if has("time") else ""
        L.append(j([d, t]))
    if has("receipt_no"):
        L.append("Receipt no. %s" % w["receipt_no"])
    # The tape is one atomic block: a distractor line landing between two
    # products would read as a sixth item and silently contradict item_count.
    rows = []
    if has("items"):
        for it in w["items"]:
            if style == 0:
                rows.append("%-26s %d x %s  %s" % (it["name"], it["qty"],
                            fmt_money(it["unit_price"], cur, rng), fmt_money(it["line_total"], cur, rng)))
            else:
                rows.append("%d x %s @ %s = %s" % (it["qty"], it["name"],
                            fmt_money(it["unit_price"], cur, rng), fmt_money(it["line_total"], cur, rng)))
    L.extend(atomic(["-" * 28] + rows + ["-" * 28]))
    if has("subtotal"):
        L.append("Subtotal: %s" % fmt_money(w["subtotal"], cur, rng))
    if has("tax"):
        L.append("Tax%s: %s" % (" (%.2f%%)" % w["tax_rate"] if has("tax_rate") else "",
                                fmt_money(w["tax"], cur, rng)))
    elif has("tax_rate"):
        L.append("Tax rate %.2f%%" % w["tax_rate"])
    if has("total"):
        L.append("TOTAL: %s" % fmt_money(w["total"], cur, rng))
    if has("payment_method"):
        L.append("Paid by %s%s" % (w["payment_method"],
                 " ending %s" % w["card_last4"] if has("card_last4") else ""))
    elif has("card_last4"):
        L.append("Card ****%s" % w["card_last4"])
    if has("cashier"):
        L.append("Served by %s" % w["cashier"])
    return "\n".join(L)


def sc_receipt():
    a = root({
        "merchant": s_str(),
        "purchase_date": s_date(),
        "total": s_num("grand total paid"),
        "currency": s_enum(CURRENCIES),
        "payment_method": s_enum(PAY),
        "receipt_number": s_str(),
    }, title="ReceiptHeader")
    ta = {"merchant": "$merchant", "purchase_date": "$date", "total": "$total",
          "currency": "$currency", "payment_method": "$payment_method",
          "receipt_number": "$receipt_no"}
    b = root({
        "store": s_obj({"name": s_str(), "city": s_str()}),
        "line_items": s_arr(s_obj({"description": s_str(), "quantity": s_int(),
                                   "unit_price": s_num(), "line_total": s_num()}),
                            "one entry per purchased line"),
        "totals": s_obj({"subtotal": s_num(), "tax": s_num(), "total": s_num()}),
        "currency": s_enum(CURRENCIES),
    }, title="ReceiptItemised")
    tb = {"store": {"name": "$merchant", "city": "$city"},
          "line_items": {LIST_KEY: "items", "item": {"description": "$name", "quantity": "$qty",
                                                     "unit_price": "$unit_price",
                                                     "line_total": "$line_total"}},
          "totals": {"subtotal": "$subtotal", "tax": "$tax", "total": "$total"},
          "currency": "$currency"}
    c = root({
        "vendor": s_str(),
        "when": s_obj({"date": s_date(), "time": s_str("HH:MM 24-hour clock")}),
        "amount_due": s_num(),
        "tax_amount": s_num(),
        "tax_rate_percent": s_num(),
        "card_last_four": s_str("last four digits only"),
        "served_by": s_str(),
        "item_count": s_int("how many distinct product lines the receipt lists; count the lines, not the quantities on them"),
    }, required=["vendor", "when", "amount_due", "tax_amount", "card_last_four"],
        title="ExpenseClaim")
    tc = {"vendor": "$merchant", "when": {"date": "$date", "time": "$time_iso"},
          "amount_due": "$total", "tax_amount": "$tax", "tax_rate_percent": "$tax_rate",
          "card_last_four": "$card_last4", "served_by": "$cashier",
          "item_count": "$item_count"}
    return [("receipt_header", a, ta), ("receipt_itemised", b, tb), ("receipt_expense", c, tc)]


# =============================================================== 5. log line
LOG_LEVEL = ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]
LOG_ERR = ["TimeoutError", "ConnectionReset", "NullPointer", "OutOfMemory",
           "ValidationError", "RateLimited", "DiskFull", "AuthFailure"]
REGIONS = ["eu-west-1", "us-east-1", "ap-south-1", "sa-east-1", "eu-central-1"]
SERVICES = ["checkout-api", "auth-gateway", "search-indexer", "billing-worker",
            "notify-dispatch", "image-resizer", "report-builder"]


def w_log(rng):
    lvl = rng.choice(LOG_LEVEL)
    return {
        "ts_date": iso(date(rng, -120, 0)),
        "ts_time": (rng.randrange(24), rng.randrange(60)),
        "level": lvl, "service": rng.choice(SERVICES),
        "host": "ip-10-%d-%d-%d" % (rng.randrange(256), rng.randrange(256), rng.randrange(256)),
        "region": rng.choice(REGIONS),
        "message": rng.choice([
            "upstream did not respond within budget",
            "failed to acquire database connection",
            "payload rejected by validator",
            "cache miss storm detected",
            "retry budget exhausted for downstream call",
            "request completed after retry"]),
        "status_code": rng.choice([200, 201, 204, 400, 401, 403, 404, 429, 500, 502, 503]),
        "latency_ms": rng.randrange(3, 9000),
        "request_id": "req_%012x" % rng.randrange(16 ** 12),
        "user_id": "usr_%d" % rng.randrange(10000, 999999),
        "error_type": rng.choice(LOG_ERR) if lvl in ("ERROR", "FATAL", "WARN") else None,
        "retry_count": rng.randrange(0, 5),
    }


def r_log(w, present, rng):
    has = present.__contains__
    style = rng.randrange(3)
    secs = rng.randrange(60)
    if has("ts_date") and has("ts_time"):
        ts = "%sT%02d:%02d:%02dZ" % (w["ts_date"], w["ts_time"][0], w["ts_time"][1], secs)
    elif has("ts_date"):
        ts = w["ts_date"]
    else:
        ts = "%02d:%02d:%02dZ" % (w["ts_time"][0], w["ts_time"][1], secs)
    if style == 0:
        parts = []
        if has("ts_date") or has("ts_time"):
            parts.append(ts)
        if has("level"):
            parts.append(w["level"])
        if has("service"):
            parts.append("[%s]" % w["service"])
        if has("host"):
            parts.append("host=%s" % w["host"])
        if has("region"):
            parts.append("region=%s" % w["region"])
        if has("request_id"):
            parts.append("req=%s" % w["request_id"])
        if has("user_id"):
            parts.append("user=%s" % w["user_id"])
        if has("status_code"):
            parts.append("status=%d" % w["status_code"])
        if has("latency_ms"):
            parts.append("latency=%dms" % w["latency_ms"])
        if has("retry_count"):
            parts.append("retries=%d" % w["retry_count"])
        if has("error_type") and w["error_type"]:
            parts.append("err=%s" % w["error_type"])
        if has("message"):
            parts.append('msg="%s"' % w["message"])
        return " ".join(parts)
    if style == 1:
        d = {}
        if has("ts_date") or has("ts_time"):
            d["timestamp"] = ts
        for k, src in [("level", "level"), ("service", "service"), ("host", "host"),
                       ("region", "region"), ("requestId", "request_id"), ("userId", "user_id")]:
            if has(src):
                d[k] = w[src]
        if has("status_code"):
            d["status"] = w["status_code"]
        if has("latency_ms"):
            d["latencyMs"] = w["latency_ms"]
        if has("retry_count"):
            d["retries"] = w["retry_count"]
        if has("error_type") and w["error_type"]:
            d["error"] = w["error_type"]
        if has("message"):
            d["message"] = w["message"]
        inner = ", ".join('"%s": %s' % (k, ('"%s"' % v) if isinstance(v, str) else v)
                          for k, v in d.items())
        return "{" + inner + "}"
    L = ["ALERT from log pipeline"]
    if has("ts_date"):
        L.append("Occurred on %s%s." % (fmt_date(date_of(w["ts_date"]), rng),
                 " at %02d:%02d UTC" % (w["ts_time"][0], w["ts_time"][1]) if has("ts_time") else ""))
    if has("service"):
        L.append("Service %s is affected." % w["service"])
    if has("level"):
        L.append("Log level %s." % w["level"])
    if has("host"):
        L.append("Reported by host %s%s." % (w["host"], " in %s" % w["region"] if has("region") else ""))
    elif has("region"):
        L.append("Region %s." % w["region"])
    if has("message"):
        L.append('Message: "%s".' % w["message"])
    if has("error_type") and w["error_type"]:
        L.append("Error class %s." % w["error_type"])
    if has("status_code"):
        L.append("HTTP status returned was %d." % w["status_code"])
    if has("latency_ms"):
        L.append("Observed latency %d ms." % w["latency_ms"])
    if has("retry_count"):
        L.append("The call was retried %d time(s)." % w["retry_count"])
    if has("request_id"):
        L.append("Trace %s." % w["request_id"])
    if has("user_id"):
        L.append("Affected account %s." % w["user_id"])
    return "\n".join(L)


def sc_log():
    a = root({
        "timestamp_date": s_date(),
        "level": s_enum(LOG_LEVEL),
        "service": s_str(),
        "message": s_str("the human-readable log message"),
        "status_code": s_int(),
        "latency_ms": s_int(),
    }, title="LogEvent")
    ta = {"timestamp_date": "$ts_date", "level": "$level", "service": "$service",
          "message": "$message", "status_code": "$status_code", "latency_ms": "$latency_ms"}
    b = root({
        "source": s_obj({"service": s_str(), "host": s_str(), "region": s_enum(REGIONS)}),
        "severity": s_enum(LOG_LEVEL),
        "error": s_obj({"type": s_enum(LOG_ERR), "retries": s_int()}, nullable_obj=True),
        "trace": s_obj({"request_id": s_str(), "user_id": s_str()}),
        "occurred_on": s_date(),
    }, title="LogDiagnostics")
    tb = {"source": {"service": "$service", "host": "$host", "region": "$region"},
          "severity": "$level",
          "error": {COLLAPSE: True, "type": "$error_type", "retries": "$retry_count"},
          "trace": {"request_id": "$request_id", "user_id": "$user_id"},
          "occurred_on": "$ts_date"}
    c = root({
        "svc": s_str(),
        "lvl": s_enum(LOG_LEVEL),
        "http_status": s_int(),
        "duration_ms": s_int(),
        "error_class": s_enum(LOG_ERR),
        "summary": s_str(),
        "node": s_str("hostname"),
    }, required=["svc", "lvl", "http_status", "error_class"], title="LogTriage")
    tc = {"svc": "$service", "lvl": "$level", "http_status": "$status_code",
          "duration_ms": "$latency_ms", "error_class": "$error_type",
          "summary": "$message", "node": "$host"}
    return [("log_event", a, ta), ("log_diagnostics", b, tb), ("log_triage", c, tc)]


# =============================================================== 6. job posting
JOB_MODE = ["onsite", "hybrid", "remote"]
JOB_TYPE = ["full-time", "part-time", "contract", "internship"]
SENIORITY = ["junior", "mid", "senior", "lead"]


def w_job(rng):
    lo = money(rng, 28000, 90000, cents=False)
    return {
        "title": rng.choice(JOB_TITLES), "company": rng.choice(COMPANIES),
        "city": rng.choice(CITIES), "country": rng.choice(COUNTRIES),
        "mode": rng.choice(JOB_MODE), "employment_type": rng.choice(JOB_TYPE),
        "seniority": rng.choice(SENIORITY),
        "salary_min": lo, "salary_max": lo + money(rng, 6000, 50000, cents=False),
        "currency": rng.choice(CURRENCIES),
        "skills": rng.sample(SKILLS, rng.randrange(2, 6)),
        "experience_years": rng.randrange(0, 12),
        "department": rng.choice(DEPARTMENTS),
        "posted": iso(date(rng, -90, 0)), "deadline": iso(date(rng, 5, 90)),
        "contact": name(rng), "contact_email": email(rng),
        "headcount": rng.randrange(1, 5),
        "visa_sponsorship": rng.random() < 0.4,
    }


def r_job(w, present, rng):
    has = present.__contains__
    style = rng.randrange(2)
    L = []
    if has("title"):
        L.append("%s%s" % (("%s " % w["seniority"].capitalize()) if has("seniority") else "", w["title"]))
    elif has("seniority"):
        L.append("Seniority: %s" % w["seniority"])
    if has("company"):
        L.append("at %s" % w["company"])
    loc = j([w["city"] if has("city") else None, w["country"] if has("country") else None], ", ")
    if loc:
        L.append("Location: %s%s" % (loc, " (%s)" % w["mode"] if has("mode") else ""))
    elif has("mode"):
        L.append("This role is %s." % w["mode"])
    if has("employment_type"):
        L.append("Contract: %s" % w["employment_type"])
    if has("department"):
        L.append("Team: %s" % w["department"])
    if has("headcount"):
        L.append("We are hiring %d people into this role." % w["headcount"])
    if has("salary_min") and has("salary_max"):
        cur = w["currency"] if has("currency") else "USD"
        L.append("Salary: %s - %s per year" % (fmt_money(w["salary_min"], cur, rng),
                                               fmt_money(w["salary_max"], cur, rng)))
    elif has("salary_min"):
        L.append("Salary from %s" % fmt_money(w["salary_min"], w["currency"] if has("currency") else "USD", rng))
    elif has("salary_max"):
        L.append("Salary up to %s" % fmt_money(w["salary_max"], w["currency"] if has("currency") else "USD", rng))
    if has("experience_years"):
        L.append("Experience: %d+ years" % w["experience_years"])
    if has("skills"):
        if style == 0:
            L.append("Required skills:")
            L += ["  - %s" % s for s in w["skills"]]
        else:
            L.append("You will need %s." % ", ".join(w["skills"]))
    if has("visa_sponsorship"):
        L.append("Visa sponsorship %s available." % ("is" if w["visa_sponsorship"] else "is not"))
    if has("posted"):
        L.append("Posted on %s." % fmt_date(date_of(w["posted"]), rng))
    if has("deadline"):
        L.append("Applications close %s." % fmt_date(date_of(w["deadline"]), rng))
    if has("contact"):
        L.append("Questions to %s%s." % (w["contact"], " (%s)" % w["contact_email"]
                 if has("contact_email") else ""))
    elif has("contact_email"):
        L.append("Apply by email to %s." % w["contact_email"])
    return "\n".join(L)


def sc_job():
    a = root({
        "job_title": s_str(),
        "company": s_str(),
        "location": s_str("city only"),
        "work_mode": s_enum(JOB_MODE),
        "employment_type": s_enum(JOB_TYPE),
        "posted_date": s_date(),
        "application_deadline": s_date(),
    }, title="JobPosting")
    ta = {"job_title": "$title", "company": "$company", "location": "$city",
          "work_mode": "$mode", "employment_type": "$employment_type",
          "posted_date": "$posted", "application_deadline": "$deadline"}
    b = root({
        "role": s_obj({"title": s_str(), "seniority": s_enum(SENIORITY),
                       "department": s_str(), "openings": s_int()}),
        "compensation": s_obj({"min": s_num(), "max": s_num(),
                               "currency": s_enum(CURRENCIES)}, nullable_obj=True),
        "requirements": s_obj({"skills": s_arr(s_str()), "years_experience": s_int()}),
        "place": s_obj({"city": s_str(), "country": s_str(), "mode": s_enum(JOB_MODE)}),
    }, title="JobDetail")
    tb = {"role": {"title": "$title", "seniority": "$seniority", "department": "$department",
                   "openings": "$headcount"},
          "compensation": {COLLAPSE: True, "min": "$salary_min", "max": "$salary_max",
                           "currency": "$currency"},
          "requirements": {"skills": {LIST_KEY: "skills", "item": None},
                           "years_experience": "$experience_years"},
          "place": {"city": "$city", "country": "$country", "mode": "$mode"}}
    c = root({
        "position": s_str(),
        "employer": s_str(),
        "visa_sponsorship": s_bool(),
        "tech_stack": s_arr(s_str()),
        "max_annual_salary": s_num("upper end of the salary range, numeric only"),
        "recruiter_email": s_str(),
        "closes_on": s_date(),
    }, required=["position", "employer", "visa_sponsorship", "tech_stack"], title="JobScreen")
    tc = {"position": "$title", "employer": "$company", "visa_sponsorship": "$visa_sponsorship",
          "tech_stack": {LIST_KEY: "skills", "item": None}, "max_annual_salary": "$salary_max",
          "recruiter_email": "$contact_email", "closes_on": "$deadline"}
    return [("job_posting", a, ta), ("job_detail", b, tb), ("job_screen", c, tc)]


# =============================================================== 7. news
NEWS_TOPIC = ["business", "technology", "politics", "health", "sport", "environment"]
NEWS_EVENT = ["acquisition", "funding", "product-launch", "layoffs", "partnership",
              "regulation", "outage"]
PUBS = ["The Harbour Times", "Veltro Daily", "Northern Wire", "Civic Ledger",
        "Techline Weekly", "The Meridian"]


def w_news(rng):
    org1 = rng.choice(COMPANIES)
    org2 = rng.choice([c for c in COMPANIES if c != org1])
    ev = rng.choice(NEWS_EVENT)
    return {
        "headline": {
            "acquisition": "%s buys %s" % (org1, org2),
            "funding": "%s raises new round" % org1,
            "product-launch": "%s unveils new line" % org1,
            "layoffs": "%s cuts jobs" % org1,
            "partnership": "%s and %s join forces" % (org1, org2),
            "regulation": "Regulator opens review of %s" % org1,
            "outage": "%s hit by day-long outage" % org1,
        }[ev],
        "publication": rng.choice(PUBS), "author": name(rng),
        "published": iso(date(rng, -400, 0)),
        "city": rng.choice(CITIES), "country": rng.choice(COUNTRIES),
        "topic": rng.choice(NEWS_TOPIC), "event_type": ev,
        "orgs": [org1, org2], "people": [name(rng) for _ in range(rng.randrange(1, 3))],
        "amount": money(rng, 1, 900, cents=True), "currency": rng.choice(CURRENCIES),
        "amount_unit": rng.choice(["million", "billion"]),
        "headcount": rng.randrange(20, 4000),
        "quote": rng.choice(["This is a decisive step for the group.",
                             "We did not take this decision lightly.",
                             "Customers will see the benefit within months."]),
    }


def r_news(w, present, rng):
    has = present.__contains__
    L = []
    if has("headline"):
        L.append(w["headline"].upper() if rng.random() < 0.3 else w["headline"])
    by = j([("By %s" % w["author"]) if has("author") else None,
            w["publication"] if has("publication") else None,
            fmt_date(date_of(w["published"]), rng) if has("published") else None], " | ")
    if by:
        L.append(by)
    loc = j([w["city"] if has("city") else None, w["country"] if has("country") else None], ", ")
    first = []
    if loc:
        first.append("%s -" % loc.upper())
    if has("orgs"):
        first.append("%s was at the centre of the story" % w["orgs"][0]
                     if len(w["orgs"]) == 1 else
                     "%s and %s are both involved" % (w["orgs"][0], w["orgs"][1]))
    if has("event_type"):
        first.append("in what the companies described as a %s." % w["event_type"].replace("-", " "))
    if first:
        L.append(" ".join(first))
    if has("amount"):
        unit = " %s" % w["amount_unit"] if has("amount_unit") else ""
        L.append("The deal is valued at about %s%s." %
                 (fmt_money(w["amount"], w["currency"] if has("currency") else "USD", rng), unit))
    if has("headcount"):
        L.append("Around %d staff are affected." % w["headcount"])
    if has("people"):
        L.append("%s commented on the record." % " and ".join(w["people"]))
    if has("quote"):
        L.append('"%s"' % w["quote"])
    if has("topic"):
        L.append("Filed under: %s." % w["topic"])
    return "\n".join(L)


def sc_news():
    a = root({
        "headline": s_str(),
        "publication": s_str(),
        "author": s_str(),
        "published_date": s_date(),
        "topic": s_enum(NEWS_TOPIC),
    }, title="NewsMeta")
    ta = {"headline": "$headline", "publication": "$publication", "author": "$author",
          "published_date": "$published", "topic": "$topic"}
    b = root({
        "event": s_obj({"type": s_enum(NEWS_EVENT), "value_amount": s_num(),
                        "value_currency": s_enum(CURRENCIES),
                        "value_unit": s_enum(["million", "billion"])}),
        "entities": s_obj({"organisations": s_arr(s_str()), "people": s_arr(s_str())}),
        "place": s_obj({"city": s_str(), "country": s_str()}, nullable_obj=True),
        "people_affected": s_int(),
    }, title="NewsEntities")
    tb = {"event": {"type": "$event_type", "value_amount": "$amount",
                    "value_currency": "$currency", "value_unit": "$amount_unit"},
          "entities": {"organisations": {LIST_KEY: "orgs", "item": None},
                       "people": {LIST_KEY: "people", "item": None}},
          "place": {COLLAPSE: True, "city": "$city", "country": "$country"},
          "people_affected": "$headcount"}
    c = root({
        "title": s_str(),
        "outlet": s_str(),
        "date": s_date(),
        "category": s_enum(NEWS_TOPIC),
        "companies_mentioned": s_arr(s_str()),
        "quote": s_str("a single quoted sentence if present, without quote marks"),
        "byline": s_str(),
    }, title="NewsDigest")
    tc = {"title": "$headline", "outlet": "$publication", "date": "$published",
          "category": "$topic", "companies_mentioned": {LIST_KEY: "orgs", "item": None},
          "quote": "$quote", "byline": "$author"}
    return [("news_meta", a, ta), ("news_entities", b, tb), ("news_digest", c, tc)]


# =============================================================== 8. property
PROP_TYPE = ["apartment", "house", "studio", "townhouse", "bungalow"]
PROP_STATUS = ["for-sale", "for-rent", "under-offer", "sold"]


def w_property(rng):
    return {
        "address": "%d %s" % (rng.randrange(1, 240), rng.choice(STREETS)),
        "city": rng.choice(CITIES), "country": rng.choice(COUNTRIES),
        "postcode": "%s%d %d%s%s" % (rng.choice("ABCDEFGHJ"), rng.randrange(1, 20),
                                     rng.randrange(10), rng.choice("ABDEFG"), rng.choice("HJLNPQ")),
        "price": money(rng, 60000, 1400000, cents=False), "currency": rng.choice(CURRENCIES),
        "bedrooms": rng.randrange(1, 6), "bathrooms": rng.randrange(1, 4),
        "area_sqm": rng.randrange(28, 320),
        "property_type": rng.choice(PROP_TYPE), "status": rng.choice(PROP_STATUS),
        "listed": iso(date(rng, -200, 0)),
        "agent": name(rng), "agent_phone": phone(rng), "agency": rng.choice(COMPANIES),
        "features": rng.sample(["balcony", "garage", "south-facing garden", "fireplace",
                                "solar panels", "lift", "basement storage", "sea view"],
                               rng.randrange(1, 4)),
        "parking": rng.random() < 0.5,
        "year_built": rng.randrange(1890, 2025),
        "floor": rng.randrange(0, 12),
    }


def r_property(w, present, rng):
    has = present.__contains__
    L = []
    head = j([w["property_type"].capitalize() if has("property_type") else "Property",
              "for sale" if has("status") and w["status"] == "for-sale" else None,
              "to rent" if has("status") and w["status"] == "for-rent" else None])
    L.append(head)
    addr = j([w["address"] if has("address") else None, w["city"] if has("city") else None,
              w["postcode"] if has("postcode") else None,
              w["country"] if has("country") else None], ", ")
    if addr:
        L.append(addr)
    if has("status") and w["status"] in ("under-offer", "sold"):
        L.append("Status: %s" % w["status"])
    if has("price"):
        L.append("%s %s" % ("Guide price" if rng.random() < 0.5 else "Asking",
                 fmt_money(w["price"], w["currency"] if has("currency") else "USD", rng)))
    bits = []
    if has("bedrooms"):
        bits.append("%d bed" % w["bedrooms"])
    if has("bathrooms"):
        bits.append("%d bath" % w["bathrooms"])
    if has("area_sqm"):
        bits.append("%d sqm" % w["area_sqm"])
    if has("floor"):
        bits.append("floor %d" % w["floor"])
    if bits:
        L.append(" | ".join(bits))
    if has("year_built"):
        L.append("Built in %d." % w["year_built"])
    if has("features"):
        L.append("Features: %s." % ", ".join(w["features"]))
    if has("parking"):
        L.append("Off-street parking %s." % ("included" if w["parking"] else "not available"))
    if has("listed"):
        L.append("Listed %s." % fmt_date(date_of(w["listed"]), rng))
    ag = j([("Contact %s" % w["agent"]) if has("agent") else None,
            ("of %s" % w["agency"]) if has("agency") else None,
            ("on %s" % w["agent_phone"]) if has("agent_phone") else None])
    if ag:
        L.append(ag + ".")
    return "\n".join(L)


def sc_property():
    a = root({
        "address_line": s_str(),
        "city": s_str(),
        "price": s_num("numeric value only"),
        "currency": s_enum(CURRENCIES),
        "bedrooms": s_int(),
        "property_type": s_enum(PROP_TYPE),
        "listing_status": s_enum(PROP_STATUS),
    }, title="PropertyListing")
    ta = {"address_line": "$address", "city": "$city", "price": "$price",
          "currency": "$currency", "bedrooms": "$bedrooms",
          "property_type": "$property_type", "listing_status": "$status"}
    b = root({
        "location": s_obj({"street": s_str(), "city": s_str(), "postcode": s_str(),
                           "country": s_str()}),
        "specs": s_obj({"bedrooms": s_int(), "bathrooms": s_int(), "area_sqm": s_num(),
                        "year_built": s_int(), "floor": s_int()}),
        "features": s_arr(s_str()),
        "has_parking": s_bool(),
    }, title="PropertySpec")
    tb = {"location": {"street": "$address", "city": "$city", "postcode": "$postcode",
                       "country": "$country"},
          "specs": {"bedrooms": "$bedrooms", "bathrooms": "$bathrooms", "area_sqm": "$area_sqm",
                    "year_built": "$year_built", "floor": "$floor"},
          "features": {LIST_KEY: "features", "item": None},
          "has_parking": "$parking"}
    c = root({
        "listing_price": s_num(),
        "agent": s_obj({"name": s_str(), "phone": s_str(), "agency": s_str()},
                       nullable_obj=True),
        "listed_on": s_date(),
        "type": s_enum(PROP_TYPE),
        "size_sqm": s_num(),
        "amenities": s_arr(s_str()),
    }, required=["listing_price", "agent", "listed_on", "type"], title="PropertyAgent")
    tc = {"listing_price": "$price",
          "agent": {COLLAPSE: True, "name": "$agent", "phone": "$agent_phone",
                    "agency": "$agency"},
          "listed_on": "$listed", "type": "$property_type", "size_sqm": "$area_sqm",
          "amenities": {LIST_KEY: "features", "item": None}}
    return [("property_listing", a, ta), ("property_spec", b, tb), ("property_agent", c, tc)]


# =============================================================== 9. meeting
MEET_KIND = ["standup", "review", "planning", "retrospective", "client-call", "one-to-one"]


def w_meeting(rng):
    att = [name(rng) for _ in range(rng.randrange(2, 6))]
    acts = []
    for _ in range(rng.randrange(1, 4)):
        acts.append({"owner": rng.choice(att), "task": rng.choice([
            "draft the migration plan", "chase the vendor quote",
            "update the risk register", "book the test environment",
            "write the customer note", "review the pricing sheet"]),
            "due": iso(date(rng, 2, 45))})
    return {
        "title": rng.choice(["Platform sync", "Q3 planning", "Vendor review",
                             "Release readiness", "Hiring loop debrief", "Budget check-in"]),
        "kind": rng.choice(MEET_KIND),
        "date": iso(date(rng, -60, 30)),
        "start": (rng.randrange(8, 18), rng.choice([0, 15, 30, 45])),
        "duration": rng.choice([15, 30, 45, 60, 90, 120]),
        "organizer": name(rng), "attendees": att,
        "location": rng.choice(["Room 4B", "Zoom", "Google Meet", "Lisbon office",
                                "Teams call", "Cafeteria corner"]),
        "project": rng.choice(["Atlas", "Beacon", "Corvus", "Delta-7", "Elmwood"]),
        "decisions": rng.sample(["ship behind a feature flag", "delay the rollout by a week",
                                 "accept the vendor quote", "split the work in two phases",
                                 "keep the current pricing"], rng.randrange(1, 3)),
        "actions": acts,
        "next_meeting": iso(date(rng, 3, 40)),
    }


def r_meeting(w, present, rng):
    has = present.__contains__
    style = rng.randrange(2)
    L = []
    if has("title"):
        L.append("# %s%s" % (w["title"], " (%s)" % w["kind"] if has("kind") else ""))
    elif has("kind"):
        L.append("# %s" % w["kind"])
    meta = []
    if has("date"):
        meta.append("Date: %s" % fmt_date(date_of(w["date"]), rng))
    if has("start"):
        meta.append("Start: %s" % fmt_time(w["start"][0], w["start"][1], rng))
    if has("duration"):
        meta.append("Duration: %d min" % w["duration"])
    if has("location"):
        meta.append("Where: %s" % w["location"])
    if has("project"):
        meta.append("Project: %s" % w["project"])
    if has("organizer"):
        meta.append("Chair: %s" % w["organizer"])
    L += meta if style == 0 else [" | ".join(meta)] if meta else []
    if has("attendees"):
        L.append("Present: %s" % ", ".join(w["attendees"]))
    if has("decisions"):
        L.append("Decisions:")
        L += ["- We will %s." % d for d in w["decisions"]]
    if has("actions"):
        L.append("Actions:")
        for a in w["actions"]:
            L.append("- %s to %s by %s" % (a["owner"], a["task"],
                                           fmt_date(date_of(a["due"]), rng)))
    if has("next_meeting"):
        L.append("Next session: %s." % fmt_date(date_of(w["next_meeting"]), rng))
    return "\n".join(L)


def sc_meeting():
    a = root({
        "meeting_title": s_str(),
        "meeting_type": s_enum(MEET_KIND),
        "date": s_date(),
        "start_time": s_str("HH:MM 24-hour clock"),
        "duration_minutes": s_int(),
        "location": s_str(),
        "organizer": s_str(),
    }, title="MeetingHeader")
    ta = {"meeting_title": "$title", "meeting_type": "$kind", "date": "$date",
          "start_time": "$start_iso", "duration_minutes": "$duration",
          "location": "$location", "organizer": "$organizer"}
    b = root({
        "attendees": s_arr(s_str(), "every person listed as present"),
        "decisions": s_arr(s_str()),
        "action_items": s_arr(s_obj({"owner": s_str(), "task": s_str(), "due_date": s_date()})),
        "project": s_str(),
        "follow_up_date": s_date(),
    }, title="MeetingOutcomes")
    tb = {"attendees": {LIST_KEY: "attendees", "item": None},
          "decisions": {LIST_KEY: "decisions", "item": None},
          "action_items": {LIST_KEY: "actions", "item": {"owner": "$owner", "task": "$task",
                                                         "due_date": "$due"}},
          "project": "$project", "follow_up_date": "$next_meeting"}
    c = root({
        "subject": s_str(),
        "when": s_obj({"date": s_date(), "start": s_str("HH:MM"), "minutes": s_int()}),
        "chair": s_str(),
        "participant_count": s_int("how many people were present"),
        "owner_of_first_action": s_str(),
        "venue": s_str(),
    }, required=["subject", "when", "chair", "participant_count"], title="MeetingAudit")
    tc = {"subject": "$title",
          "when": {"date": "$date", "start": "$start_iso", "minutes": "$duration"},
          "chair": "$organizer", "participant_count": "$attendee_count",
          "owner_of_first_action": "$first_action_owner", "venue": "$location"}
    return [("meeting_header", a, ta), ("meeting_outcomes", b, tb), ("meeting_audit", c, tc)]


# =============================================================== 10. shipment
CARRIERS = ["DHL", "UPS", "FedEx", "Royal Mail", "DPD", "Aramex", "Japan Post"]
SHIP_STATUS = ["label-created", "in-transit", "out-for-delivery", "delivered",
               "delayed", "returned"]


def w_shipment(rng):
    who = name(rng)
    return {
        "tracking": "%s%012d" % (rng.choice("JDPZ"), rng.randrange(10 ** 12)),
        "carrier": rng.choice(CARRIERS), "order_id": "ORD-%d" % rng.randrange(100000, 999999),
        "ship_date": iso(date(rng, -60, 0)), "eta": iso(date(rng, 0, 20)),
        "recipient": who, "address": "%d %s" % (rng.randrange(1, 240), rng.choice(STREETS)),
        "city": rng.choice(CITIES), "postcode": "%05d" % rng.randrange(100000),
        "country": rng.choice(COUNTRIES),
        "weight_kg": round(rng.uniform(0.1, 32), 2),
        "status": rng.choice(SHIP_STATUS), "items_count": rng.randrange(1, 9),
        "service": rng.choice(["standard", "express", "economy", "next-day"]),
        "cost": money(rng, 3, 180), "currency": rng.choice(CURRENCIES),
        "signature_required": rng.random() < 0.3,
    }


def r_shipment(w, present, rng):
    has = present.__contains__
    style = rng.randrange(2)
    L = []
    if style == 0:
        L.append("Your parcel is on its way")
        if has("order_id"):
            L.append("Order %s" % w["order_id"])
        if has("tracking"):
            L.append("Tracking number: %s%s" % (w["tracking"],
                     " (%s)" % w["carrier"] if has("carrier") else ""))
        elif has("carrier"):
            L.append("Carrier: %s" % w["carrier"])
        if has("status"):
            L.append("Current status: %s" % w["status"])
        if has("ship_date"):
            L.append("Dispatched %s" % fmt_date(date_of(w["ship_date"]), rng))
        if has("eta"):
            L.append("Expected delivery %s" % fmt_date(date_of(w["eta"]), rng))
        if has("service"):
            L.append("Service: %s" % w["service"])
        if has("items_count"):
            L.append("%d item(s) in this shipment" % w["items_count"])
        if has("weight_kg"):
            L.append("Total weight %.2f kg" % w["weight_kg"])
        if has("cost"):
            L.append("Shipping charged: %s" % fmt_money(w["cost"],
                     w["currency"] if has("currency") else "USD", rng))
        if has("signature_required"):
            L.append("A signature %s required on delivery." % ("is" if w["signature_required"] else "is not"))
        addr = j([w["recipient"] if has("recipient") else None,
                  w["address"] if has("address") else None,
                  w["city"] if has("city") else None,
                  w["postcode"] if has("postcode") else None,
                  w["country"] if has("country") else None], ", ")
        if addr:
            L.append("Delivering to: %s" % addr)
        return "\n".join(L)
    rows = []
    for label, key, fn in [("TRACK", "tracking", str), ("CARRIER", "carrier", str),
                           ("ORDER", "order_id", str), ("STATUS", "status", str),
                           ("SHIPPED", "ship_date", lambda v: fmt_date(date_of(v), rng)),
                           ("ETA", "eta", lambda v: fmt_date(date_of(v), rng)),
                           ("SERVICE", "service", str), ("TO", "recipient", str),
                           ("ADDR", "address", str), ("CITY", "city", str),
                           ("ZIP", "postcode", str), ("COUNTRY", "country", str)]:
        if has(key):
            rows.append("%s=%s" % (label, fn(w[key])))
    if has("weight_kg"):
        rows.append("KG=%.2f" % w["weight_kg"])
    if has("items_count"):
        rows.append("UNITS=%d" % w["items_count"])
    if has("cost"):
        rows.append("FREIGHT=%s" % fmt_money(w["cost"], w["currency"] if has("currency") else "USD", rng))
    if has("signature_required"):
        rows.append("SIG=%s" % ("Y" if w["signature_required"] else "N"))
    return "SHIPMENT EVENT\n" + "\n".join(rows)


def sc_shipment():
    a = root({
        "tracking_number": s_str(),
        "carrier": s_enum(CARRIERS),
        "status": s_enum(SHIP_STATUS),
        "ship_date": s_date(),
        "expected_delivery": s_date(),
        "order_id": s_str(),
    }, title="ShipmentStatus")
    ta = {"tracking_number": "$tracking", "carrier": "$carrier", "status": "$status",
          "ship_date": "$ship_date", "expected_delivery": "$eta", "order_id": "$order_id"}
    b = root({
        "destination": s_obj({"recipient": s_str(), "address_line": s_str(), "city": s_str(),
                              "postcode": s_str(), "country": s_str()}),
        "parcel": s_obj({"weight_kg": s_num(),
                         "item_count": s_int("how many items the parcel contains"),
                         "signature_required": s_bool()}),
        "freight": s_obj({"amount": s_num(), "currency": s_enum(CURRENCIES)}, nullable_obj=True),
        "service_level": s_enum(["standard", "express", "economy", "next-day"]),
    }, title="ShipmentDetail")
    tb = {"destination": {"recipient": "$recipient", "address_line": "$address",
                          "city": "$city", "postcode": "$postcode", "country": "$country"},
          "parcel": {"weight_kg": "$weight_kg", "item_count": "$items_count",
                     "signature_required": "$signature_required"},
          "freight": {COLLAPSE: True, "amount": "$cost", "currency": "$currency"},
          "service_level": "$service"}
    c = root({
        "awb": s_str("the tracking or airway bill number"),
        "courier": s_enum(CARRIERS),
        "deliver_to_city": s_str(),
        "deliver_to_country": s_str(),
        "weight_kg": s_num(),
        "delivery_state": s_enum(SHIP_STATUS),
        "eta": s_date(),
    }, required=["awb", "courier", "delivery_state"], title="ShipmentOps")
    tc = {"awb": "$tracking", "courier": "$carrier", "deliver_to_city": "$city",
          "deliver_to_country": "$country", "weight_kg": "$weight_kg",
          "delivery_state": "$status", "eta": "$eta"}
    return [("shipment_status", a, ta), ("shipment_detail", b, tb), ("shipment_ops", c, tc)]


# =============================================================== 11. incident
SEV = ["SEV1", "SEV2", "SEV3", "SEV4"]


def w_incident(rng):
    return {
        "incident_id": "INC-%04d" % rng.randrange(1000, 9999),
        "severity": rng.choice(SEV), "service": rng.choice(SERVICES),
        "detected": iso(date(rng, -300, 0)),
        "detected_time": (rng.randrange(24), rng.randrange(60)),
        "summary": rng.choice([
            "checkout failures for card payments",
            "search results returned stale data",
            "login loop for federated accounts",
            "queue backlog delayed notifications",
            "image uploads rejected with 500s"]),
        "impact_users": rng.randrange(12, 400000),
        "duration_min": rng.randrange(4, 900),
        "root_cause": rng.choice([
            "a bad config push disabled connection pooling",
            "an expired certificate on the internal gateway",
            "an unbounded retry loop saturated the database",
            "a schema migration locked a hot table",
            "a third-party provider rate-limited our traffic"]),
        "owner": name(rng), "team": rng.choice(DEPARTMENTS),
        "resolved": rng.random() < 0.75,
        "followups": rng.sample(["add synthetic checks", "cap retries", "rotate certs automatically",
                                 "shard the hot table", "add provider fallback",
                                 "improve alert thresholds"], rng.randrange(1, 4)),
        "revenue_loss": money(rng, 500, 250000), "currency": rng.choice(CURRENCIES),
        "postmortem_due": iso(date(rng, 1, 30)),
    }


def r_incident(w, present, rng):
    has = present.__contains__
    L = ["INCIDENT REPORT"]
    if has("incident_id"):
        L.append("ID: %s" % w["incident_id"])
    if has("severity"):
        L.append("Severity: %s" % w["severity"])
    if has("service"):
        L.append("Service: %s" % w["service"])
    if has("detected"):
        L.append("Detected: %s%s" % (fmt_date(date_of(w["detected"]), rng),
                 " %02d:%02d UTC" % (w["detected_time"][0], w["detected_time"][1])
                 if has("detected_time") else ""))
    if has("summary"):
        L.append("Summary: %s." % w["summary"].capitalize())
    if has("impact_users"):
        L.append("Impact: roughly %s users affected." % "{:,}".format(w["impact_users"]))
    if has("duration_min"):
        L.append("Duration: %d minutes." % w["duration_min"])
    if has("revenue_loss"):
        L.append("Estimated revenue impact %s." % fmt_money(w["revenue_loss"],
                 w["currency"] if has("currency") else "USD", rng))
    if has("root_cause"):
        L.append("Root cause: %s." % w["root_cause"])
    if has("owner"):
        L.append("Incident commander: %s%s." % (w["owner"], " (%s)" % w["team"] if has("team") else ""))
    elif has("team"):
        L.append("Owning team: %s." % w["team"])
    if has("resolved"):
        L.append("The incident %s." % ("is now resolved" if w["resolved"] else "is still open"))
    if has("followups"):
        L.append("Follow-up actions:")
        L += ["  * %s" % f for f in w["followups"]]
    if has("postmortem_due"):
        L.append("Postmortem due %s." % fmt_date(date_of(w["postmortem_due"]), rng))
    return "\n".join(L)


def sc_incident():
    a = root({
        "incident_id": s_str(),
        "severity": s_enum(SEV),
        "affected_service": s_str(),
        "detected_date": s_date(),
        "summary": s_str(),
        "resolved": s_bool(),
    }, title="Incident")
    ta = {"incident_id": "$incident_id", "severity": "$severity",
          "affected_service": "$service", "detected_date": "$detected",
          "summary": "$summary", "resolved": "$resolved"}
    b = root({
        "impact": s_obj({"users_affected": s_int(), "duration_minutes": s_int(),
                         "revenue_loss_amount": s_num(),
                         "revenue_loss_currency": s_enum(CURRENCIES)}),
        "cause": s_str("the stated root cause"),
        "ownership": s_obj({"commander": s_str(), "team": s_str()}, nullable_obj=True),
        "follow_up_actions": s_arr(s_str()),
        "postmortem_due": s_date(),
    }, title="IncidentImpact")
    tb = {"impact": {"users_affected": "$impact_users", "duration_minutes": "$duration_min",
                     "revenue_loss_amount": "$revenue_loss", "revenue_loss_currency": "$currency"},
          "cause": "$root_cause",
          "ownership": {COLLAPSE: True, "commander": "$owner", "team": "$team"},
          "follow_up_actions": {LIST_KEY: "followups", "item": None},
          "postmortem_due": "$postmortem_due"}
    c = root({
        "ref": s_str(),
        "sev": s_enum(SEV),
        "service": s_str(),
        "minutes_down": s_int(),
        "users": s_int(),
        "is_closed": s_bool(),
        "action_count": s_int("how many follow-up actions are listed"),
    }, required=["ref", "sev", "service", "is_closed"], title="IncidentMetrics")
    tc = {"ref": "$incident_id", "sev": "$severity", "service": "$service",
          "minutes_down": "$duration_min", "users": "$impact_users",
          "is_closed": "$resolved", "action_count": "$followup_count"}
    return [("incident_core", a, ta), ("incident_impact", b, tb), ("incident_metrics", c, tc)]


# =============================================================== 12. invoice
INV_STATUS = ["draft", "sent", "paid", "overdue", "cancelled"]
TERMS = ["net 7", "net 14", "net 30", "net 60", "due on receipt"]


def w_invoice(rng):
    cur = rng.choice(CURRENCIES)
    lines = []
    for _ in range(rng.randrange(1, 5)):
        desc = rng.choice(["consulting hours", "annual licence", "onsite training",
                           "support retainer", "data migration", "design sprint"])
        q = rng.randrange(1, 40)
        up = money(rng, 40, 900)
        lines.append({"desc": desc, "qty": q, "rate": up, "amount": round(q * up, 2)})
    sub = round(sum(l["amount"] for l in lines), 2)
    rate = rng.choice([0.0, 0.05, 0.18, 0.2, 0.21])
    import datetime
    issue = date(rng, -250, 0)
    return {
        "invoice_number": "INV-%d-%04d" % (rng.choice([2024, 2025, 2026]), rng.randrange(10000)),
        "issuer": rng.choice(COMPANIES), "client": rng.choice(COMPANIES),
        "client_contact": name(rng), "client_email": email(rng),
        "issue_date": iso(issue),
        "due_date": iso(issue + datetime.timedelta(days=rng.choice([7, 14, 30, 60]))),
        "lines": lines, "subtotal": sub, "tax_rate": round(rate * 100, 2),
        "tax": round(sub * rate, 2), "total": round(sub * (1 + rate), 2),
        "currency": cur, "terms": rng.choice(TERMS),
        "po_number": "PO%06d" % rng.randrange(10 ** 6),
        "status": rng.choice(INV_STATUS),
        "bank_iban": "%s%02d%s%010d" % (rng.choice(["DE", "PT", "GB", "NL"]),
                                        rng.randrange(100), rng.choice(["ABCD", "WXYZ"]),
                                        rng.randrange(10 ** 10)),
    }


def r_invoice(w, present, rng):
    has = present.__contains__
    cur = w["currency"] if has("currency") else "USD"
    L = ["INVOICE"]
    if has("invoice_number"):
        L.append("Invoice no: %s" % w["invoice_number"])
    if has("issuer"):
        L.append("From: %s" % w["issuer"])
    cl = j([w["client"] if has("client") else None,
            ("attn. %s" % w["client_contact"]) if has("client_contact") else None,
            w["client_email"] if has("client_email") else None], ", ")
    if cl:
        L.append("To: %s" % cl)
    if has("po_number"):
        L.append("PO reference: %s" % w["po_number"])
    if has("issue_date"):
        L.append("Issued: %s" % fmt_date(date_of(w["issue_date"]), rng))
    if has("due_date"):
        L.append("Payment due: %s" % fmt_date(date_of(w["due_date"]), rng))
    if has("terms"):
        L.append("Terms: %s" % w["terms"])
    if has("status"):
        L.append("Status: %s" % w["status"])
    if has("lines"):
        # Atomic: an injected line here would read as an extra billed line and
        # contradict line_count.
        rows = ["%-18s %3d x %-10s %s" % (l["desc"], l["qty"],
                fmt_money(l["rate"], cur, rng), fmt_money(l["amount"], cur, rng))
                for l in w["lines"]]
        L.extend(atomic([""] + rows))
    if has("subtotal"):
        L.append("Subtotal %s" % fmt_money(w["subtotal"], cur, rng))
    if has("tax"):
        L.append("VAT%s %s" % (" @ %.2f%%" % w["tax_rate"] if has("tax_rate") else "",
                               fmt_money(w["tax"], cur, rng)))
    elif has("tax_rate"):
        L.append("VAT rate %.2f%%" % w["tax_rate"])
    if has("total"):
        L.append("Amount payable %s" % fmt_money(w["total"], cur, rng))
    if has("bank_iban"):
        L.append("Pay to IBAN %s" % w["bank_iban"])
    return "\n".join(L)


def sc_invoice():
    a = root({
        "invoice_number": s_str(),
        "issuer": s_str("the company sending the invoice"),
        "client": s_str(),
        "issue_date": s_date(),
        "due_date": s_date(),
        "total": s_num(),
        "currency": s_enum(CURRENCIES),
        "status": s_enum(INV_STATUS),
    }, title="Invoice")
    ta = {"invoice_number": "$invoice_number", "issuer": "$issuer", "client": "$client",
          "issue_date": "$issue_date", "due_date": "$due_date", "total": "$total",
          "currency": "$currency", "status": "$status"}
    b = root({
        "lines": s_arr(s_obj({"description": s_str(), "quantity": s_int(),
                              "unit_rate": s_num(), "amount": s_num()})),
        "amounts": s_obj({"subtotal": s_num(), "tax_rate_percent": s_num(),
                          "tax": s_num(), "total": s_num()}),
        "payment": s_obj({"terms": s_enum(TERMS), "iban": s_str(),
                          "po_number": s_str()}, nullable_obj=True),
    }, title="InvoiceLines")
    tb = {"lines": {LIST_KEY: "lines", "item": {"description": "$desc", "quantity": "$qty",
                                                "unit_rate": "$rate", "amount": "$amount"}},
          "amounts": {"subtotal": "$subtotal", "tax_rate_percent": "$tax_rate",
                      "tax": "$tax", "total": "$total"},
          "payment": {COLLAPSE: True, "terms": "$terms", "iban": "$bank_iban",
                      "po_number": "$po_number"}}
    c = root({
        "ref": s_str(),
        "billed_to": s_obj({"company": s_str(), "contact": s_str(), "email": s_str()}),
        "amount_payable": s_num(),
        "currency": s_enum(CURRENCIES),
        "payment_state": s_enum(INV_STATUS),
        "line_count": s_int("how many distinct billed lines the invoice lists; count the lines, not the quantities on them"),
        "due": s_date(),
    }, required=["ref", "billed_to", "amount_payable", "currency", "payment_state"],
        title="InvoiceAP")
    tc = {"ref": "$invoice_number",
          "billed_to": {"company": "$client", "contact": "$client_contact",
                        "email": "$client_email"},
          "amount_payable": "$total", "currency": "$currency", "payment_state": "$status",
          "line_count": "$line_count", "due": "$due_date"}
    return [("invoice_core", a, ta), ("invoice_lines", b, tb), ("invoice_ap", c, tc)]


# =============================================================== registry
DOMAINS = {
    "review": {"world": w_review, "render": r_review, "schemas": sc_review()},
    "ticket": {"world": w_ticket, "render": r_ticket, "schemas": sc_ticket()},
    "email": {"world": w_email, "render": r_email, "schemas": sc_email()},
    "receipt": {"world": w_receipt, "render": r_receipt, "schemas": sc_receipt()},
    "log": {"world": w_log, "render": r_log, "schemas": sc_log()},
    "job": {"world": w_job, "render": r_job, "schemas": sc_job()},
    "news": {"world": w_news, "render": r_news, "schemas": sc_news()},
    "property": {"world": w_property, "render": r_property, "schemas": sc_property()},
    "meeting": {"world": w_meeting, "render": r_meeting, "schemas": sc_meeting()},
    "shipment": {"world": w_shipment, "render": r_shipment, "schemas": sc_shipment()},
    "incident": {"world": w_incident, "render": r_incident, "schemas": sc_incident()},
    "invoice": {"world": w_invoice, "render": r_invoice, "schemas": sc_invoice()},
}


# v4: three more domains whose targets keep their qualifiers ('Screen 3', 'Bay 12',
# 'Flat 7C', 'Spring 2026'). Registered here so every consumer of DOMAINS sees them.
from domains_v4 import DOMAINS_V4  # noqa: E402

DOMAINS.update(DOMAINS_V4)
