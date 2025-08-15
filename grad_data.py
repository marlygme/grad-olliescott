
import csv
import os
from collections import defaultdict, Counter
from statistics import mean
from datetime import datetime, date

CSV_COLUMNS = [
    "firm_name","firm_alias","program_type","city","intake_year",
    "application_open_date","application_close_date","program_length_months","rotations_count",
    "salary_annual_aud","evidence_span","thread_title","thread_url","post_number","post_timestamp",
    "source_file","confidence","created_at"
]

PROGRAM_LABELS = {
    "graduate": "Graduate Program",
    "clerkship": "Clerkship",
    "summer_clerkship": "Summer Clerkship",
    "winter_clerkship": "Winter Clerkship",
    "seasonal_clerkship": "Seasonal Clerkship",
    "vacation": "Vacation Program",
    "internship": "Internship",
    "ambiguous": "Other"
}

def _parse_float(x):
    try:
        return float(x)
    except Exception:
        return None

def _parse_date(x):
    # Expecting YYYY-MM-DD
    try:
        if not x or x.strip() == "":
            return None
        return datetime.strptime(x.strip(), "%Y-%m-%d").date()
    except Exception:
        return None

def load_grad_signals(csv_path):
    """Load raw signals rows into a list of dicts (no heavy deps)."""
    rows = []
    if not os.path.exists(csv_path):
        return rows
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "firm_name": r.get("firm_name","").strip(),
                "program_type": r.get("program_type","").strip(),
                "city": r.get("city","").strip(),
                "intake_year": r.get("intake_year","").strip(),
                "application_open_date": r.get("application_open_date","").strip(),
                "application_close_date": r.get("application_close_date","").strip(),
                "salary_annual_aud": r.get("salary_annual_aud","").strip(),
                "evidence_span": r.get("evidence_span","").strip(),
                "thread_title": r.get("thread_title","").strip(),
                "thread_url": r.get("thread_url","").strip(),
                "confidence": r.get("confidence","").strip(),
            })
    return rows

def aggregate_by_firm(rows):
    """Aggregate rows into firm cards consumable by the website."""
    firms = {}
    today = date.today()
    for r in rows:
        name = r["firm_name"] or "Unknown"
        firm = firms.setdefault(name, {
            "name": name,
            "experiences_count": 0,
            "program_counts": Counter(),
            "cities": Counter(),
            "intake_years": Counter(),
            "salaries": [],
            "next_close": None,
            "evidence_samples": [],
        })
        firm["experiences_count"] += 1
        if r["program_type"]:
            firm["program_counts"][r["program_type"]] += 1
        if r["city"]:
            firm["cities"][r["city"]] += 1
        if r["intake_year"].isdigit():
            firm["intake_years"][int(r["intake_year"])] += 1
        s = _parse_float(r["salary_annual_aud"])
        if s: firm["salaries"].append(s)

        # Compute next close date if future
        close_d = _parse_date(r["application_close_date"])
        if close_d and close_d >= today:
            if firm["next_close"] is None or close_d < firm["next_close"]:
                firm["next_close"] = close_d

        # Keep up to 2 evidence samples
        if r["evidence_span"] and len(firm["evidence_samples"]) < 2:
            firm["evidence_samples"].append(r["evidence_span"])

    # Finalise display fields
    cards = []
    for name, f in firms.items():
        # Popular programs: top 3 by count, converted to labels
        popular_programs = [PROGRAM_LABELS.get(k, k) for k, _ in f["program_counts"].most_common(3)]
        # Avg salary
        avg_salary = round(mean(f["salaries"])) if f["salaries"] else None
        # Top city
        top_city = f["cities"].most_common(1)[0][0] if f["cities"] else None
        # Top intake year
        top_intake = f["intake_years"].most_common(1)[0][0] if f["intake_years"] else None

        cards.append({
            "name": name,
            "experiences_count": f["experiences_count"],
            "avg_salary": avg_salary,
            "popular_programs": popular_programs,
            "top_city": top_city,
            "top_intake": top_intake,
            "next_close": f["next_close"].isoformat() if f["next_close"] else None,
            "evidence_samples": f["evidence_samples"],
        })

    # Sort by experiences desc, then name
    cards.sort(key=lambda x: (-x["experiences_count"], x["name"]))
    return cards

def load_cards(csv_path="out/grad_program_signals.csv"):
    rows = load_grad_signals(csv_path)
    return aggregate_by_firm(rows)
