"""Out-of-distribution cases, part B: plain extraction in domains the generator lacks."""
from make_cases import C

C("restaurant", ["plain", "absent"],
  "Hi, confirming a table for 6 under the name Okonkwo at Bella Notte this Saturday, 14 June 2025 at 7:30 pm. Please note one guest is vegetarian. A deposit of 60 euros was taken at booking. Call us on 0161 555 0142 if plans change.",
  {"guest_name": "s", "party_size": "i", "date": "s", "time": "s", "restaurant": "s",
   "phone": "s", "has_vegetarian_guest": "b", "deposit_paid": "n", "occasion": "s"},
  {"guest_name": "Okonkwo", "party_size": 6, "date": "2025-06-14", "time": "19:30",
   "restaurant": "Bella Notte", "phone": "0161 555 0142", "has_vegetarian_guest": True,
   "deposit_paid": 60, "occasion": None})

C("recipe", ["plain", "absent"],
  "Lemon Herb Roast Chicken. Serves 4. Prep 15 minutes, then roast at 200C for 55 minutes. Rest for 10 before carving.",
  {"dish": "s", "servings": "i", "prep_minutes": "i", "cook_minutes": "i",
   "oven_temp_c": "i", "vegetarian": "b", "calories_per_serving": "i"},
  {"dish": "Lemon Herb Roast Chicken", "servings": 4, "prep_minutes": 15,
   "cook_minutes": 55, "oven_temp_c": 200, "vegetarian": None,
   "calories_per_serving": None})

C("hotel", ["plain"],
  "Booking HX-77421 for Ms Lindqvist. Arrive 3 October 2025, depart 6 October (three nights). Deluxe double, SEK 1,450 per night, breakfast not included. Total payable at the hotel: SEK 4,350.",
  {"confirmation_code": "s", "guest": "s", "check_in": "s", "check_out": "s",
   "nights": "i", "room_type": "s", "rate_per_night": "n", "currency": "s",
   "breakfast_included": "b", "total_payable": "n"},
  {"confirmation_code": "HX-77421", "guest": "Lindqvist", "check_in": "2025-10-03",
   "check_out": "2025-10-06", "nights": 3, "room_type": "Deluxe double",
   "rate_per_night": 1450, "currency": "SEK", "breakfast_included": False,
   "total_payable": 4350})

C("event", ["plain", "absent"],
  "JAZZ AT THE DOCKS - Friday 21 November 2025, The Warehouse, Rotterdam. Doors 19:00, music from 20:15. Tickets EUR 28 at the door.",
  {"title": "s", "venue": "s", "city": "s", "date": "s", "doors_time": "s",
   "start_time": "s", "ticket_price": "n", "currency": "s", "sold_out": "b"},
  {"title": "JAZZ AT THE DOCKS", "venue": "The Warehouse", "city": "Rotterdam",
   "date": "2025-11-21", "doors_time": "19:00", "start_time": "20:15",
   "ticket_price": 28, "currency": "EUR", "sold_out": None})

C("insurance", ["plain", "absent"],
  "Claim CL-2025-88213 lodged by Maria Gonzalez for the water damage to her kitchen on 2 March 2025. Estimated repair cost GBP 3,200. Assigned to adjuster T. Rahman.",
  {"claim_number": "s", "policyholder": "s", "incident_date": "s",
   "loss_type": ("e", ["theft", "fire", "water", "collision", "other"]),
   "amount_claimed": "n", "currency": "s", "adjuster": "s", "settlement_date": "s",
   "status": "s"},
  {"claim_number": "CL-2025-88213", "policyholder": "Maria Gonzalez",
   "incident_date": "2025-03-02", "loss_type": "water", "amount_claimed": 3200,
   "currency": "GBP", "adjuster": "T. Rahman", "settlement_date": None, "status": None})

C("bank_statement", ["array", "nested"],
  "Statement for J. Moreau, period ending 31 January 2025. Opening balance 1,204.50.\n03 Jan 2025  Tesco Metro  -23.40\n09 Jan 2025  Salary Acme Ltd  +2,150.00\n15 Jan 2025  Netflix  -12.99\nClosing balance 3,318.11",
  {"account_holder": "s", "period_end": "s", "opening_balance": "n",
   "closing_balance": "n",
   "transactions": ("L", {"date": "s", "description": "s", "amount": "n"})},
  {"account_holder": "J. Moreau", "period_end": "2025-01-31", "opening_balance": 1204.50,
   "closing_balance": 3318.11,
   "transactions": [{"date": "2025-01-03", "description": "Tesco Metro", "amount": -23.40},
                    {"date": "2025-01-09", "description": "Salary Acme Ltd", "amount": 2150.00},
                    {"date": "2025-01-15", "description": "Netflix", "amount": -12.99}]})

C("course", ["plain", "absent"],
  "CS 3410 Operating Systems (4 credits), taught by Anita Desai, Fall 2025. Prerequisite: CS 2110. Enrollment: 112 of 120 seats filled.",
  {"code": "s", "title": "s", "credits": "i", "instructor": "s", "semester": "s",
   "prerequisite": "s", "capacity": "i", "enrolled": "i", "room": "s"},
  {"code": "CS 3410", "title": "Operating Systems", "credits": 4, "instructor": "Anita Desai",
   "semester": "Fall 2025", "prerequisite": "CS 2110", "capacity": 120, "enrolled": 112,
   "room": None})

C("prescription", ["plain", "absent"],
  "Rx for Tomasz Wrona, 12 May 2025: amoxicillin 500 mg three times daily for 7 days. No refills. Prescribed by Helen Park, MD.",
  {"patient": "s", "drug": "s", "dose_mg": "i", "doses_per_day": "i",
   "duration_days": "i", "refills": "i", "prescriber": "s", "date": "s", "pharmacy": "s"},
  {"patient": "Tomasz Wrona", "drug": "amoxicillin", "dose_mg": 500, "doses_per_day": 3,
   "duration_days": 7, "refills": 0, "prescriber": "Helen Park", "date": "2025-05-12",
   "pharmacy": None})

C("match_report", ["plain", "absent"],
  "Final: Northgate Rovers 2, Eastfield United 1 at Brook Park on Sunday 4 May 2025 before a crowd of 8,412. Both goals for Rovers came in the second half; Eastfield's lone goal was an own goal.",
  {"home_team": "s", "away_team": "s", "home_score": "i", "away_score": "i", "venue": "s",
   "date": "s", "attendance": "i", "man_of_the_match": "s", "red_cards": "i"},
  {"home_team": "Northgate Rovers", "away_team": "Eastfield United", "home_score": 2,
   "away_score": 1, "venue": "Brook Park", "date": "2025-05-04", "attendance": 8412,
   "man_of_the_match": None, "red_cards": None})

C("weather", ["plain", "absent"],
  "Lisbon, Tuesday 17 June 2025: a sunny day with highs near 29 and lows around 18. Light breeze at 12 km/h. Slight chance of showers (10%).",
  {"city": "s", "date": "s", "high_c": "i", "low_c": "i", "rain_probability_pct": "i",
   "wind_kph": "i", "condition": ("e", ["sunny", "cloudy", "rain", "snow", "storm"]),
   "uv_index": "i"},
  {"city": "Lisbon", "date": "2025-06-17", "high_c": 29, "low_c": 18,
   "rain_probability_pct": 10, "wind_kph": 12, "condition": "sunny", "uv_index": None})

C("contract", ["plain"],
  "Services Agreement between Orchard Analytics Ltd and Bluebell Retail GmbH, effective 1 September 2025 for an initial term of 24 months at EUR 4,800 per month. Renews automatically unless either party gives 60 days' notice. Governed by the laws of England and Wales.",
  {"party_a": "s", "party_b": "s", "effective_date": "s", "term_months": "i",
   "monthly_fee": "n", "currency": "s", "auto_renew": "b", "notice_days": "i",
   "governing_law": "s"},
  {"party_a": "Orchard Analytics Ltd", "party_b": "Bluebell Retail GmbH",
   "effective_date": "2025-09-01", "term_months": 24, "monthly_fee": 4800,
   "currency": "EUR", "auto_renew": True, "notice_days": 60,
   "governing_law": "England and Wales"})

C("library", ["plain", "absent"],
  "Catalogue entry: 'Lanterns Over Marrow Bay' by Elsie Varga, published 2019, 342 pages, ISBN 978-1-84749-211-6. Three copies available.",
  {"title": "s", "author": "s", "isbn": "s", "publication_year": "i", "pages": "i",
   "copies_available": "i", "due_date": "s", "shelf": "s"},
  {"title": "Lanterns Over Marrow Bay", "author": "Elsie Varga",
   "isbn": "978-1-84749-211-6", "publication_year": 2019, "pages": 342,
   "copies_available": 3, "due_date": None, "shelf": None})

C("utility_bill", ["plain", "absent"],
  "Account 4420-1187. Bill for Prakash Iyer covering 1 April to 30 April 2025. You used 412 kWh. Amount due: 96.38 USD by 20 May 2025.",
  {"account_number": "s", "customer": "s", "period_start": "s", "period_end": "s",
   "usage_kwh": "i", "amount_due": "n", "currency": "s", "due_date": "s", "late_fee": "n"},
  {"account_number": "4420-1187", "customer": "Prakash Iyer", "period_start": "2025-04-01",
   "period_end": "2025-04-30", "usage_kwh": 412, "amount_due": 96.38, "currency": "USD",
   "due_date": "2025-05-20", "late_fee": None})

C("gym", ["plain", "absent"],
  "Welcome Aisha Bello! Your Premium plan starts on 1 July 2025 at GBP 39.99 a month. Locker rental is included. Cancel any time.",
  {"member": "s", "plan": ("e", ["basic", "premium", "student"]), "monthly_price": "n",
   "currency": "s", "start_date": "s", "end_date": "s", "locker_included": "b",
   "trainer_sessions": "i"},
  {"member": "Aisha Bello", "plan": "premium", "monthly_price": 39.99, "currency": "GBP",
   "start_date": "2025-07-01", "end_date": None, "locker_included": True,
   "trainer_sessions": None})

C("tax_notice", ["plain", "absent"],
  "Notice of assessment for tax year 2024 issued to Daniel Frost (reference 3918227461). Balance due: 1,872.00 payable by 31 January 2026. Interest accrues from 1 February 2026.",
  {"taxpayer": "s", "tax_year": "i", "reference": "s", "amount_owed": "n",
   "due_date": "s", "penalty": "n", "payment_plan_available": "b"},
  {"taxpayer": "Daniel Frost", "tax_year": 2024, "reference": "3918227461",
   "amount_owed": 1872.00, "due_date": "2026-01-31", "penalty": None,
   "payment_plan_available": None})

C("changelog", ["plain"],
  "Notely 4.2.0 - released 12 August 2025. Fixes 7 bugs and adds dark mode for tablets. Requires Android 11 or newer. Nothing breaking in this release.",
  {"app_name": "s", "version": "s", "release_date": "s", "bugs_fixed": "i",
   "breaking_changes": "b", "min_os": "s"},
  {"app_name": "Notely", "version": "4.2.0", "release_date": "2025-08-12", "bugs_fixed": 7,
   "breaking_changes": False, "min_os": "Android 11"})
