"""Three v4 domains whose targets are QUALIFIED spans.

The independent eval (RESULTS_ood_v3.md) showed v3 shortening values like 'Fall 2025' to
'Fall', 'Track B' to 'B', 'Room 204' to '204' and 'Cafe Aurora' to 'Aurora'. A check of the
v3 training targets found 0 of 25,185 string values starting 'Track ', 'Fall ', 'Spring ' or
'Cafe ', and only 43 starting 'Room ': the model was never shown a target that keeps its
qualifier, so it learned to drop it.

These domains put qualifiers in the target on purpose: 'Screen 3', 'Row F', 'Seat 12',
'Bay 12', 'Aisle C', 'SKU-88213', 'Flat 7C', 'Block B', 'Floor 3', 'Spring 2026', 'Week 32',
and organisation names that begin with a generic word ('Cinema ...', 'Studio ...', 'Cafe ...').

None of them is a domain in eval/ood, so that set stays a test of transfer: it measures
whether the SKILL (keep the whole span) carries over, not whether a domain was memorised.
"""
from core import (LIST_KEY, atomic, date, fmt_date, fmt_money, fmt_time, iso, money,
                  name, phone, root, s_arr, s_bool, s_date, s_enum, s_int, s_num, s_obj,
                  s_str)


def date_of(isostr):
    import datetime
    return datetime.date.fromisoformat(isostr)


LETTERS = "ABCDEFGHJKLM"


# =============================================================== 13. cinema booking
FILMS = ["Paper Moons", "The Salt Meridian", "Night Ferry", "Glass Orchard",
         "Echoes of Linden Bay", "The Tin Kingdom", "Small Hours", "Cold Harbour",
         "A Quiet Revolution", "Driftwood Summer"]
CINEMAS = ["Cinema Lumiere", "Picturehall Eastgate", "The Regent Cinema",
           "Studio Cinema Ashford", "Cinema Verdant", "Grand Odeum Waterside"]
CIN_FORMAT = ["2D", "3D", "IMAX", "4DX"]
CERTS = ["PG-13", "Rated 15", "U", "PG", "Rated 18", "12A"]


def w_cinema(rng):
    row = rng.choice(LETTERS)
    first = rng.randrange(1, 18)
    n = rng.randrange(1, 5)
    return {
        "film": rng.choice(FILMS), "cinema": rng.choice(CINEMAS),
        "screen": "Screen %d" % rng.randrange(1, 13), "row": "Row %s" % row,
        "seats": ["Seat %d" % (first + i) for i in range(n)],
        "show_date": iso(date(rng, -20, 60)),
        "show_time": (rng.randrange(11, 22), rng.choice([0, 15, 30, 45])),
        "fmt": rng.choice(CIN_FORMAT), "cert": rng.choice(CERTS),
        "ref": "BK-%06d" % rng.randrange(100000, 999999), "customer": name(rng),
        "tickets": n, "total": money(rng, 8, 90), "currency": rng.choice(["GBP", "EUR", "USD"]),
        "snacks": rng.random() < 0.4,
    }


def r_cinema(w, present, rng):
    has = present.__contains__
    style = rng.randrange(3)
    L = []
    if style == 0:
        L.append("Booking confirmation%s" % (" %s" % w["ref"] if has("ref") else ""))
        if has("customer"):
            L.append("Dear %s," % w["customer"])   # full name: the target holds it whole
        bits = []
        if has("film"):
            bits.append("you are booked to see %s" % w["film"])
        if has("cinema"):
            bits.append("at %s" % w["cinema"])
        if bits:
            L.append("Great news: " + " ".join(bits) + ".")
        when = []
        if has("show_date"):
            when.append("on %s" % fmt_date(date_of(w["show_date"]), rng))
        if has("show_time"):
            when.append("at %s" % fmt_time(w["show_time"][0], w["show_time"][1], rng))
        if when:
            L.append("Showing " + " ".join(when) + ".")
        place = []
        if has("screen"):
            place.append(w["screen"])
        if has("row"):
            place.append(w["row"])
        if has("seats"):
            place.append(", ".join(w["seats"]))
        if place:
            L.append("Your place: " + ", ".join(place) + ".")
    else:
        if has("cinema"):
            L.append("== %s ==" % w["cinema"].upper() if style == 2 else w["cinema"])
        if has("film"):
            L.append("Film: %s" % w["film"])
        meta = []
        if has("show_date"):
            meta.append("Date: %s" % fmt_date(date_of(w["show_date"]), rng))
        if has("show_time"):
            meta.append("Time: %s" % fmt_time(w["show_time"][0], w["show_time"][1], rng))
        if has("screen"):
            meta.append(w["screen"])
        L.append(" | ".join(meta)) if meta else None
        seat = [x for x in [w["row"] if has("row") else None,
                            ", ".join(w["seats"]) if has("seats") else None] if x]
        if seat:
            L.append("Seats: " + " - ".join(seat))
        if has("ref"):
            L.append("Ref %s" % w["ref"])
        if has("customer"):
            L.append("Name: %s" % w["customer"])
    if has("fmt"):
        L.append("Format: %s." % w["fmt"])
    if has("cert"):
        L.append("Certificate: %s." % w["cert"])
    if has("tickets"):
        L.append("Tickets: %d." % w["tickets"])
    if has("total"):
        L.append("Total paid %s." % fmt_money(w["total"], w["currency"], rng))
    if has("snacks"):
        L.append("Snack bundle added." if w["snacks"] else "No snack bundle.")
    return "\n".join(L)


def sc_cinema():
    a = root({
        "film_title": s_str(), "cinema": s_str(), "screen": s_str(),
        "show_date": s_date(), "show_time": s_str("HH:MM 24-hour clock"),
        "format": s_enum(CIN_FORMAT), "certificate": s_str(),
    }, title="ShowingHeader")
    ta = {"film_title": "$film", "cinema": "$cinema", "screen": "$screen",
          "show_date": "$show_date", "show_time": "$show_iso", "format": "$fmt",
          "certificate": "$cert"}
    b = root({
        "booking_reference": s_str(), "customer_name": s_str(),
        "ticket_count": s_int(), "seats": s_arr(s_str(), "every seat booked"),
        "total_price": s_num(), "currency": s_str("ISO 4217 code"),
        "snack_bundle": s_bool(),
    }, title="BookingDetails")
    tb = {"booking_reference": "$ref", "customer_name": "$customer",
          "ticket_count": "$tickets", "seats": {LIST_KEY: "seats", "item": None},
          "total_price": "$total", "currency": "$currency", "snack_bundle": "$snacks"}
    c = root({
        "film": s_str(),
        "venue": s_obj({"name": s_str(), "screen": s_str()}),
        "when": s_obj({"date": s_date(), "time": s_str("HH:MM")}),
        "row": s_str(), "ticket_count": s_int(),
    }, required=["film", "venue", "when"], title="TicketAudit")
    tc = {"film": "$film", "venue": {"name": "$cinema", "screen": "$screen"},
          "when": {"date": "$show_date", "time": "$show_iso"},
          "row": "$row", "ticket_count": "$tickets"}
    return [("showing_header", a, ta), ("booking_details", b, tb), ("ticket_audit", c, tc)]


# =============================================================== 14. warehouse goods-in
SUPPLIERS = ["Harbor & Sons Ltd", "Studio North Supplies", "Cafe Verde Provisions",
             "Kestrel Mobility GmbH", "Ironbridge Fasteners Ltd", "Hotel Linen Co",
             "Pinecrest Packaging", "Marlow & Finch Trading"]
WH_DESC = ["M8 hex bolts", "pallet wrap 500mm", "cable ties 200mm", "LED batten 1.2m",
           "safety gloves L", "box files A4", "nitrile gloves M", "foam inserts 40mm"]
WH_COND = ["intact", "damaged", "partial"]


def reg(rng):
    return "%s%02d %s" % ("".join(rng.choice("ABCDEFGHKLMNPRSTUVWXY") for _ in range(2)),
                          rng.randrange(10, 99),
                          "".join(rng.choice("ABCDEFGHKLMNPRSTUVWXY") for _ in range(3)))


def w_warehouse(rng):
    items = []
    for sku in rng.sample(range(10000, 99999), rng.randrange(1, 5)):
        items.append({"sku": "SKU-%05d" % sku, "desc": rng.choice(WH_DESC),
                      "qty": rng.randrange(1, 40) * rng.choice([1, 5, 10])})
    return {
        "supplier": rng.choice(SUPPLIERS), "dn": "DN-%05d" % rng.randrange(10000, 99999),
        "po": "PO-2025-%04d" % rng.randrange(1000, 9999),
        "date": iso(date(rng, -30, 5)), "bay": "Bay %d" % rng.randrange(1, 41),
        "aisle": "Aisle %s" % rng.choice("ABCDEFGH"), "pallets": rng.randrange(1, 14),
        "driver": name(rng), "vehicle": reg(rng), "items": items,
        "condition": rng.choice(WH_COND), "chilled": rng.random() < 0.3,
        "received_by": name(rng),
    }


def r_warehouse(w, present, rng):
    has = present.__contains__
    style = rng.randrange(2)
    L = []
    head = []
    if has("supplier"):
        head.append("Goods in from %s" % w["supplier"])
    if has("date"):
        head.append("on %s" % fmt_date(date_of(w["date"]), rng))
    if head:
        L.append(" ".join(head) + ".")
    refs = []
    if has("dn"):
        refs.append("Delivery note %s" % w["dn"])
    if has("po"):
        refs.append("order %s" % w["po"])
    if refs:
        L.append(", ".join(refs) + ".")
    place = []
    if has("bay"):
        place.append(w["bay"])
    if has("aisle"):
        place.append(w["aisle"])
    if place:
        L.append("Put away: " + ", ".join(place) + ".")
    if has("pallets"):
        L.append("%d pallet%s received." % (w["pallets"], "" if w["pallets"] == 1 else "s"))
    if has("items"):
        rows = []
        for it in w["items"]:
            if style == 0:
                rows.append("%s  %-22s qty %d" % (it["sku"], it["desc"], it["qty"]))
            else:
                rows.append("- %s: %s x%d" % (it["sku"], it["desc"], it["qty"]))
        L.extend(atomic([""] + rows))
    if has("condition"):
        L.append("Condition on arrival: %s." % w["condition"])
    if has("chilled"):
        L.append("Chilled load, temperature log attached." if w["chilled"]
                 else "Ambient load.")
    if has("driver") or has("vehicle"):
        bits = []
        if has("driver"):
            bits.append("driver %s" % w["driver"])
        if has("vehicle"):
            bits.append("vehicle %s" % w["vehicle"])
        L.append("Delivered by " + ", ".join(bits) + ".")
    if has("received_by"):
        L.append("Signed for by %s." % w["received_by"])
    return "\n".join(L)


def sc_warehouse():
    a = root({
        "supplier": s_str(), "delivery_note": s_str(), "po_number": s_str(),
        "received_date": s_date(), "bay": s_str(), "aisle": s_str(),
    }, title="GoodsInHeader")
    ta = {"supplier": "$supplier", "delivery_note": "$dn", "po_number": "$po",
          "received_date": "$date", "bay": "$bay", "aisle": "$aisle"}
    b = root({
        "lines": s_arr(s_obj({"sku": s_str(), "description": s_str(), "quantity": s_int()}),
                       "every stock line received"),
        "pallets": s_int(), "condition": s_enum(WH_COND), "chilled": s_bool(),
    }, title="GoodsInLines")
    tb = {"lines": {LIST_KEY: "items", "item": {"sku": "$sku", "description": "$desc",
                                                "quantity": "$qty"}},
          "pallets": "$pallets", "condition": "$condition", "chilled": "$chilled"}
    c = root({
        "supplier": s_str(),
        "goods_in": s_obj({"date": s_date(), "bay": s_str()}),
        "vehicle": s_obj({"driver": s_str(), "registration": s_str()}),
        "received_by": s_str(),
    }, required=["supplier", "goods_in"], title="GoodsInAudit")
    tc = {"supplier": "$supplier", "goods_in": {"date": "$date", "bay": "$bay"},
          "vehicle": {"driver": "$driver", "registration": "$vehicle"},
          "received_by": "$received_by"}
    return [("goods_in_header", a, ta), ("goods_in_lines", b, tb), ("goods_in_audit", c, tc)]


# =============================================================== 15. maintenance request
CATEGORY = ["plumbing", "electrical", "heating", "pest control", "structural", "appliance"]
ISSUES = {
    "plumbing": ["tap in the kitchen is dripping", "toilet keeps running"],
    "electrical": ["socket by the bed sparks", "hallway light flickers"],
    "heating": ["radiator stays cold", "boiler loses pressure overnight"],
    "pest control": ["mice noticed behind the cooker", "wasp nest under the eaves"],
    "structural": ["crack above the window", "ceiling stain is spreading"],
    "appliance": ["washing machine will not drain", "oven door will not close"],
}
PRIORITY = ["low", "normal", "urgent"]
WINDOWS = ["Week 32", "Week 8", "Q3 2025", "Q1 2026", "Spring 2026", "Autumn 2025",
           "Summer 2025", "Winter 2026"]
CONTRACTORS = ["Studio North Repairs", "Fernhill Plumbing Ltd", "Kestrel Electrical",
               "Bluebell Heating Co", "Hotel Linen Maintenance"]


def w_maintenance(rng):
    cat = rng.choice(CATEGORY)
    return {
        "ref": "WO-%05d" % rng.randrange(10000, 99999), "tenant": name(rng),
        "flat": "Flat %d%s" % (rng.randrange(1, 25), rng.choice("ABCD")),
        "block": "Block %s" % rng.choice("ABCDEF"), "floor": "Floor %d" % rng.randrange(1, 10),
        "category": cat, "issue": rng.choice(ISSUES[cat]),
        "priority": rng.choice(PRIORITY), "reported": iso(date(rng, -30, 0)),
        "window": rng.choice(WINDOWS), "contractor": rng.choice(CONTRACTORS),
        "access": rng.random() < 0.6, "phone": phone(rng),
    }


def r_maintenance(w, present, rng):
    has = present.__contains__
    style = rng.randrange(2)
    L = []
    if has("ref"):
        L.append("Repair request %s" % w["ref"] if style == 0 else "Work order %s" % w["ref"])
    who = []
    if has("tenant"):
        who.append("from %s" % w["tenant"])
    loc = [w[k] for k in ("flat", "block", "floor") if has(k)]
    if loc:
        who.append("(" + ", ".join(loc) + ")")
    if who:
        L.append("Raised " + " ".join(who) + ".")
    if has("category"):
        L.append("Category: %s." % w["category"])
    if has("issue"):
        L.append("Problem: the %s." % w["issue"] if not w["issue"].startswith(("the ",))
                 else "Problem: %s." % w["issue"])
    if has("priority"):
        L.append("Priority: %s." % w["priority"])
    if has("reported"):
        L.append("Reported on %s." % fmt_date(date_of(w["reported"]), rng))
    if has("access"):
        L.append("Someone needs to let the contractor in." if w["access"]
                 else "No access needed, the contractor has keys.")
    if has("window"):
        L.append("Planned for %s." % w["window"])
    if has("contractor"):
        L.append("Contractor: %s." % w["contractor"])
    if has("phone"):
        L.append("Tenant phone %s." % w["phone"])
    return "\n".join(L)


def sc_maintenance():
    a = root({
        "reference": s_str(), "tenant": s_str(), "flat": s_str(), "block": s_str(),
        "floor": s_str(),
    }, title="RepairHeader")
    ta = {"reference": "$ref", "tenant": "$tenant", "flat": "$flat", "block": "$block",
          "floor": "$floor"}
    b = root({
        "category": s_enum(CATEGORY), "issue": s_str(),
        "priority": s_enum(PRIORITY), "reported_date": s_date(),
        "access_required": s_bool(),
    }, title="RepairIssue")
    tb = {"category": "$category", "issue": "$issue", "priority": "$priority",
          "reported_date": "$reported", "access_required": "$access"}
    c = root({
        "reference": s_str(),
        "location": s_obj({"flat": s_str(), "block": s_str(), "floor": s_str()}),
        "scheduled_window": s_str(), "contractor": s_str(), "contact_phone": s_str(),
    }, required=["reference", "location"], title="RepairAudit")
    tc = {"reference": "$ref",
          "location": {"flat": "$flat", "block": "$block", "floor": "$floor"},
          "scheduled_window": "$window", "contractor": "$contractor",
          "contact_phone": "$phone"}
    return [("repair_header", a, ta), ("repair_issue", b, tb), ("repair_audit", c, tc)]


DOMAINS_V4 = {
    "cinema": {"world": w_cinema, "render": r_cinema, "schemas": sc_cinema()},
    "warehouse": {"world": w_warehouse, "render": r_warehouse, "schemas": sc_warehouse()},
    "maintenance": {"world": w_maintenance, "render": r_maintenance,
                    "schemas": sc_maintenance()},
}
