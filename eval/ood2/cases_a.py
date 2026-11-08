from core2 import C

# ---------------- plain / absent / distractor / array / nested ----------------

C("parcel", ["plain", "absent"],
  "Your parcel 7Q-4410-NX left the Rotterdam depot on 3 March 2026 and is expected on 6 March. "
  "It weighs 2.4 kg. Signature on delivery is required.",
  {"tracking_id": "s", "origin_depot": "s", "dispatched": "s", "eta": "s", "weight_kg": "n",
   "signature_required": "b", "insured_value": "n", "carrier": "s"},
  {"tracking_id": "7Q-4410-NX", "origin_depot": "Rotterdam", "dispatched": "2026-03-03",
   "eta": "2026-03-06", "weight_kg": 2.4, "signature_required": True, "insured_value": None,
   "carrier": None})

C("apartment", ["plain", "absent"],
  "To let: bright 2-bedroom flat on Harrow Lane, third floor, no lift. Rent is 1,450 per month, "
  "deposit equal to five weeks. Available from 1 June 2026. Pets by agreement.",
  {"street": "s", "bedrooms": "i", "floor": "s", "monthly_rent": "n", "available_from": "s",
   "furnished": "b", "parking": "s"},
  {"street": "Harrow Lane", "bedrooms": 2, "floor": "third", "monthly_rent": 1450,
   "available_from": "2026-06-01", "furnished": None, "parking": None})

C("job_post", ["plain", "absent"],
  "Senior Backend Engineer at Lumenfield Ltd, based in Leeds with two days a week remote. "
  "Salary 68,000 to 82,000 a year. Apply before 15 April 2026. Five years of Go experience required.",
  {"title": "s", "company": "s", "city": "s", "salary_min": "n", "salary_max": "n",
   "deadline": "s", "years_experience": "i", "remote_days": "i", "visa_sponsorship": "b"},
  {"title": "Senior Backend Engineer", "company": "Lumenfield Ltd", "city": "Leeds",
   "salary_min": 68000, "salary_max": 82000, "deadline": "2026-04-15", "years_experience": 5,
   "remote_days": 2, "visa_sponsorship": None})

C("clinic_appt", ["plain", "absent"],
  "Reminder: Ms Ana Prieto has an appointment with Dr Okafor at the Eastgate Clinic on "
  "12 May 2026 at 09:40. Please arrive ten minutes early and bring your referral letter.",
  {"patient": "s", "doctor": "s", "clinic": "s", "date": "s", "time": "s", "department": "s",
   "fasting_required": "b"},
  {"patient": "Ana Prieto", "doctor": "Okafor", "clinic": "Eastgate Clinic", "date": "2026-05-12",
   "time": "09:40", "department": None, "fasting_required": None})

C("scholarship", ["plain", "absent"],
  "The Marlowe Trust Award offers 4,000 to undergraduates in engineering. Closing date: "
  "30 November 2026. Applicants must hold a GPA of at least 3.5. No application fee.",
  {"name": "s", "amount": "n", "field": "s", "deadline": "s", "min_gpa": "n", "fee": "n",
   "essay_required": "b"},
  {"name": "Marlowe Trust Award", "amount": 4000, "field": "engineering",
   "deadline": "2026-11-30", "min_gpa": 3.5, "fee": 0, "essay_required": None})

C("concert", ["plain", "absent"],
  "The Velvet Harbour tour stops at the Grand Arcade, Manchester on 21 September 2026. "
  "Doors 18:30, tickets from 45. The venue is fully seated.",
  {"artist_or_tour": "s", "venue": "s", "city": "s", "date": "s", "doors": "s",
   "min_price": "n", "support_act": "s", "seated": "b"},
  {"artist_or_tour": "Velvet Harbour", "venue": "Grand Arcade", "city": "Manchester",
   "date": "2026-09-21", "doors": "18:30", "min_price": 45, "support_act": None, "seated": True})

C("bike_repair", ["plain", "absent"],
  "Job card 2291. Customer: Tomas Weil. Bike: Orbea Gain, size M. Work: replaced rear derailleur "
  "and fitted new chain. Labour 35, parts 112. Ready for collection on Friday 8 May 2026.",
  {"job": "s", "customer": "s", "bike": "s", "work_done": "s", "labour": "n", "parts": "n",
   "ready_on": "s", "warranty": "b"},
  {"job": "2291", "customer": "Tomas Weil", "bike": "Orbea Gain", "work_done":
   "replaced rear derailleur and fitted new chain", "labour": 35, "parts": 112,
   "ready_on": "2026-05-08", "warranty": None})

C("hike", ["plain", "absent"],
  "Trail report, Cairn Ridge loop: 14.2 km, about 5 hours. Boggy near the second stile. "
  "Lowest temperature on the summit was -3. Dogs allowed on a lead.",
  {"trail": "s", "distance_km": "n", "duration_hours": "n", "summit_temp_c": "n",
   "dogs_allowed": "b", "difficulty": "s", "elevation_gain_m": "n"},
  {"trail": "Cairn Ridge loop", "distance_km": 14.2, "duration_hours": 5, "summit_temp_c": -3,
   "dogs_allowed": True, "difficulty": None, "elevation_gain_m": None})

C("invoice", ["plain", "absent"],
  "INVOICE 0415 from Quillon Print to Harbour Bakery, dated 2 February 2026. "
  "500 flyers at 0.12 each, delivery 15. Total due 75 within 30 days. VAT not charged.",
  {"number": "s", "supplier": "s", "buyer": "s", "date": "s", "quantity": "i", "unit_price": "n",
   "delivery_fee": "n", "total": "n", "po_number": "s"},
  {"number": "0415", "supplier": "Quillon Print", "buyer": "Harbour Bakery", "date": "2026-02-02",
   "quantity": 500, "unit_price": 0.12, "delivery_fee": 15, "total": 75, "po_number": None})

C("vaccine", ["plain", "absent"],
  "Vaccination record: Leo Marchetti, born 4 July 2019. Tetanus booster given 18 January 2026 "
  "by nurse Ruth Adeyemi at Southfield Surgery. Batch TB-7731.",
  {"patient": "s", "dob": "s", "vaccine": "s", "given_on": "s", "administered_by": "s",
   "site": "s", "batch": "s", "next_due": "s"},
  {"patient": "Leo Marchetti", "dob": "2019-07-04", "vaccine": "Tetanus booster",
   "given_on": "2026-01-18", "administered_by": "Ruth Adeyemi", "site": "Southfield Surgery",
   "batch": "TB-7731", "next_due": None})

C("volunteer", ["plain", "absent"],
  "Hi, it's Dana. I can cover the Saturday morning shift at the food bank, 9 to 1, on 14 June 2026. "
  "I will bring my own gloves.",
  {"volunteer": "s", "site": "s", "date": "s", "shift": "s",
   "needs_transport": "b", "phone": "s"},
  {"volunteer": "Dana", "site": "food bank", "date": "2026-06-14", "shift": "Saturday morning",
   "needs_transport": None, "phone": None})

C("ride_receipt", ["plain", "absent"],
  "Thanks for riding, Priya. Trip on 9 October 2026, 14.7 km, 31 minutes. Fare 18.40, "
  "tip 2.00. Driver: Marcus. Paid by card.",
  {"rider": "s", "date": "s", "distance_km": "n", "minutes": "i", "fare": "n", "tip": "n",
   "driver": "s", "surge": "b"},
  {"rider": "Priya", "date": "2026-10-09", "distance_km": 14.7, "minutes": 31, "fare": 18.4,
   "tip": 2.0, "driver": "Marcus", "surge": None})

C("warranty", ["plain", "absent"],
  "Claim WC-5560: the Halden blender model HB-300 stopped working after 8 months. "
  "Purchased 12 August 2025 from Kitchenworld. Receipt available. Customer asks for a replacement.",
  {"claim_id": "s", "product": "s", "model": "s", "purchase_date": "s", "retailer": "s",
   "months_in_use": "i", "resolution_requested": "s", "price_paid": "n"},
  {"claim_id": "WC-5560", "product": "blender", "model": "HB-300", "purchase_date": "2025-08-12",
   "retailer": "Kitchenworld", "months_in_use": 8, "resolution_requested": "replacement",
   "price_paid": None})

C("noise", ["plain", "absent"],
  "Complaint filed by resident of Flat 4B, Ashgrove Court, regarding loud music from the flat "
  "above after 23:00 on three nights last week. No contact has been made with the neighbour.",
  {"unit": "s", "building": "s", "issue": "s", "time_after": "s", "nights": "i",
   "neighbour_contacted": "b", "police_called": "b"},
  {"unit": "Flat 4B", "building": "Ashgrove Court", "issue": "loud music", "time_after": "23:00",
   "nights": 3, "neighbour_contacted": False, "police_called": None})

C("book_review", ["plain", "absent"],
  "Review of The Salt Orchard by Nadia Verhoeven, 412 pages. I gave it four stars; "
  "the middle drags but the ending lands.",
  {"title": "s", "author": "s", "pages": "i", "stars": "i", "publisher": "s", "isbn": "s"},
  {"title": "The Salt Orchard", "author": "Nadia Verhoeven", "pages": 412, "stars": 4,
   "publisher": None, "isbn": None})

C("store_opening", ["plain", "absent"],
  "Great news: Fenwick & Dale opens its new store at 22 Mill Street, Bath on Saturday "
  "3 October 2026. First 100 customers get a free tote. Open 9 to 6 daily.",
  {"brand": "s", "address": "s", "city": "s", "opening_date": "s", "hours": "s",
   "giveaway": "s", "parking": "b"},
  {"brand": "Fenwick & Dale", "address": "22 Mill Street", "city": "Bath",
   "opening_date": "2026-10-03", "hours": "9 to 6 daily", "giveaway": "free tote", "parking": None})

C("quiz", ["plain", "absent"],
  "Quiz night results: the Brain Trust scored 41 out of 50 and came second. "
  "The winners were Quizzly Bears with 44. Next quiz is 19 March 2026.",
  {"team": "s", "score": "i", "max_score": "i", "position": "s", "winner": "s",
   "winner_score": "i", "next_quiz": "s", "venue": "s"},
  {"team": "Brain Trust", "score": 41, "max_score": 50, "position": "second",
   "winner": "Quizzly Bears", "winner_score": 44, "next_quiz": "2026-03-19", "venue": None})

C("boat_rental", ["plain", "absent"],
  "Booking BR-208 for the sloop Marigold, 8 metres, from 20 July to 27 July 2026. "
  "Skipper included. Deposit 600 taken. Departure from Falmouth marina.",
  {"booking": "s", "vessel": "s", "length_m": "n", "start": "s", "end": "s",
   "skipper_included": "b", "deposit": "n", "port": "s", "fuel_included": "b"},
  {"booking": "BR-208", "vessel": "Marigold", "length_m": 8, "start": "2026-07-20",
   "end": "2026-07-27", "skipper_included": True, "deposit": 600, "port": "Falmouth marina",
   "fuel_included": None})

C("solar", ["plain", "absent"],
  "Quote for a 6.5 kW rooftop solar system at 17 Birch Close. Estimated output 6,200 kWh a year. "
  "Price 8,900 installed. Panels by Helio; inverter brand to be confirmed.",
  {"address": "s", "capacity_kw": "n", "annual_kwh": "n", "price": "n", "panel_brand": "s",
   "inverter_brand": "s", "battery_included": "b"},
  {"address": "17 Birch Close", "capacity_kw": 6.5, "annual_kwh": 6200, "price": 8900,
   "panel_brand": "Helio", "inverter_brand": None, "battery_included": None})

# ---------------- spans with qualifiers (never in v4 training or set 1) ----------------

C("gate_change", ["plain", "span"],
  "Gate change: flight VY 902 to Lisbon now boards at Gate B14, Terminal 2, departing 17:25.",
  {"flight": "s", "destination": "s", "gate": "s", "terminal": "s", "departure": "s"},
  {"flight": "VY 902", "destination": "Lisbon", "gate": "B14", "terminal": "2",
   "departure": "17:25"})

C("lecture", ["plain", "span"],
  "Lecture 7 of Organic Chemistry II will be held in Hall C, Building 5, on Tuesday "
  "17 February 2026. Reading: Chapter 9.",
  {"course": "s", "lecture_no": "i", "room": "s", "building": "s", "date": "s", "reading": "s"},
  {"course": "Organic Chemistry II", "lecture_no": 7, "room": "Hall C", "building": "Building 5",
   "date": "2026-02-17", "reading": "Chapter 9"})

C("shelf_move", ["plain", "span"],
  "Relocate the paint stock from Shelf 3D in Zone 6 to Shelf 1A in Zone 2. Authorised by Hana. "
  "Pallet tag P-90412.",
  {"item": "s", "from_location": "s", "to_location": "s", "authorised_by": "s", "pallet": "s"},
  {"item": "paint stock", "from_location": "Shelf 3D in Zone 6",
   "to_location": "Shelf 1A in Zone 2", "authorised_by": "Hana", "pallet": "P-90412"})

C("exam_slot", ["plain", "span"],
  "Candidate 30418 sits Paper 2 in Room 12 at Greenfield Academy on 4 June 2026 at 13:30. "
  "Extra time of 25 per cent has been approved.",
  {"candidate": "s", "paper": "s", "room": "s", "venue": "s", "date": "s", "time": "s",
   "extra_time_percent": "n"},
  {"candidate": "30418", "paper": "Paper 2", "room": "Room 12", "venue": "Greenfield Academy",
   "date": "2026-06-04", "time": "13:30", "extra_time_percent": 25})

C("seat_chart", ["plain", "span"],
  "Ticket for the Orchestra Hall: Section Balcony West, Row K, Seat 22. Event: Spring Gala "
  "Concert, 11 April 2026.",
  {"hall": "s", "section": "s", "row": "s", "seat": "s", "event": "s", "date": "s"},
  {"hall": "Orchestra Hall", "section": "Balcony West", "row": "Row K", "seat": "Seat 22",
   "event": "Spring Gala Concert", "date": "2026-04-11"})

# ---------------- arrays / nested ----------------

C("shopping_list", ["array", "plain"],
  "Dinner party shopping: two kilos of potatoes, a bunch of rosemary, 6 lemons, and one jar of "
  "capers. Budget is 40.",
  {"items": ["L", {"name": "s", "quantity": "s"}], "budget": "n", "store": "s"},
  {"items": [{"name": "potatoes", "quantity": "two kilos"},
             {"name": "rosemary", "quantity": "a bunch"},
             {"name": "lemons", "quantity": "6"},
             {"name": "capers", "quantity": "one jar"}], "budget": 40, "store": None})

C("meeting_attendees", ["array", "plain"],
  "Minutes of the budget review on 5 May 2026. Present: Elena Costa (chair), Raj Patel, "
  "Mei Lin Tran. Apologies from Ben Archer. Next meeting 2 June 2026.",
  {"date": "s", "attendees": ["L", {"name": "s", "role": "s"}], "apologies": "LS",
   "next_meeting": "s"},
  {"date": "2026-05-05", "attendees": [{"name": "Elena Costa", "role": "chair"},
                                       {"name": "Raj Patel", "role": None},
                                       {"name": "Mei Lin Tran", "role": None}],
   "apologies": ["Ben Archer"], "next_meeting": "2026-06-02"})

C("tour_stops", ["array", "plain"],
  "The Highland coach tour: day 1 Inverness, day 2 Skye, day 3 Fort William. "
  "Price per person 389, single supplement 95.",
  {"stops": ["L", {"day": "i", "place": "s"}], "price_pp": "n", "single_supplement": "n",
   "operator": "s"},
  {"stops": [{"day": 1, "place": "Inverness"}, {"day": 2, "place": "Skye"},
             {"day": 3, "place": "Fort William"}], "price_pp": 389, "single_supplement": 95,
   "operator": None})

C("tags_post", ["array", "plain"],
  "Posted by marco_r on 1 December 2025: tips for first-time sourdough bakers. "
  "Tags: bread, baking, beginner.",
  {"author": "s", "date": "s", "topic": "s", "tags": "LS", "likes": "i"},
  {"author": "marco_r", "date": "2025-12-01", "topic": "tips for first-time sourdough bakers",
   "tags": ["bread", "baking", "beginner"], "likes": None})

C("empty_array", ["array", "absent"],
  "Pickup order for Hollis, 3 sandwiches. No allergies were mentioned and no extras were requested.",
  {"customer": "s", "sandwiches": "i", "extras": "LS", "allergies": "LS", "total": "n"},
  {"customer": "Hollis", "sandwiches": 3, "extras": None, "allergies": None, "total": None})

C("nested_address", ["nested", "plain"],
  "Deliver to Ingrid Solheim, 9 Kirk Road, Dundee, DD2 4PL. Contact her on 07700 900123. "
  "Leave with a neighbour if out.",
  {"recipient": "s", "address": ["o", {"line1": "s", "city": "s", "postcode": "s"}],
   "phone": "s", "instructions": "s"},
  {"recipient": "Ingrid Solheim", "address": {"line1": "9 Kirk Road", "city": "Dundee",
                                              "postcode": "DD2 4PL"},
   "phone": "07700 900123", "instructions": "Leave with a neighbour if out"})

C("nested_dimensions", ["nested", "absent"],
  "Crate 88 of ceramic tiles measures 120 by 80 cm and is 40 cm high. Gross weight 64 kg. "
  "Fragile: handle with care.",
  {"crate": "s", "contents": "s", "dimensions": ["o", {"length_cm": "n", "width_cm": "n",
                                                       "height_cm": "n"}],
   "weight_kg": "n", "fragile": "b", "destination": "s"},
  {"crate": "88", "contents": "ceramic tiles", "dimensions": {"length_cm": 120, "width_cm": 80,
                                                              "height_cm": 40},
   "weight_kg": 64, "fragile": True, "destination": None})

C("distractor_price", ["distractor", "plain"],
  "The Alder jacket was 180 last season but is now 129 after the sale. Free returns within 30 days. "
  "Colours: navy and olive.",
  {"product": "s", "current_price": "n", "return_days": "i", "colours": "LS"},
  {"product": "Alder jacket", "current_price": 129, "return_days": 30, "colours": ["navy", "olive"]})

C("distractor_date", ["distractor", "plain"],
  "Following our call on 3 March, the survey of the property is booked for 20 March 2026. "
  "The surveyor, Mr J. Patterson, will bring ladders.",
  {"survey_date": "s", "surveyor": "s", "property": "s"},
  {"survey_date": "2026-03-20", "surveyor": "J. Patterson", "property": None})

C("distractor_name", ["distractor", "plain"],
  "Dear Mr Hale, as discussed with Caroline in accounts, your annual subscription of 240 renews "
  "on 1 January 2027. Regards, Support.",
  {"customer": "s", "plan_price": "n", "renewal_date": "s", "support_phone": "s"},
  {"customer": "Hale", "plan_price": 240, "renewal_date": "2027-01-01",
   "support_phone": None})
