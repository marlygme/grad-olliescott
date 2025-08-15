
# grad_data_v2.py
import csv
from collections import Counter
from statistics import mean
from datetime import datetime, date

PROGRAM_LABELS = {
    "graduate": "Graduate Program",
    "clerkship": "Clerkship",
    "summer_clerkship": "Summer Clerkship",
    "winter_clerkship": "Winter Clerkship",
    "seasonal_clerkship": "Seasonal Clerkship",
    "vacation": "Vacation Program",
    "internship": "Internship",
}

def _f(x):
    try: return float(x)
    except: return None

def _d(x):
    try:
        if not x or not x.strip(): return None
        return datetime.strptime(x.strip(), "%Y-%m-%d").date()
    except: return None

def load_grad_signals(csv_path):
    rows = []
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append({
                    "firm_name": r.get("firm_name","").strip(),
                    "program_type": r.get("program_type","").strip(),
                    "city": r.get("city","").strip(),
                    "intake_year": r.get("intake_year","").strip(),
                    "application_close_date": r.get("application_close_date","").strip(),
                    "salary_annual_aud": r.get("salary_annual_aud","").strip(),
                    "evidence_span": r.get("evidence_span","").strip(),
                })
    except FileNotFoundError:
        return []
    return rows

def aggregate_by_firm(rows):
    today = date.today()
    firms = {}
    for r in rows:
        name = r["firm_name"] or "Unknown"
        f = firms.setdefault(name, {
            "name": name,
            "insights_count": 0,
            "program_counts": Counter(),
            "cities": Counter(),
            "intake_years": Counter(),
            "salaries": [],
            "next_close": None,
            "evidence_samples": [],
        })
        f["insights_count"] += 1
        if r["program_type"]: f["program_counts"][r["program_type"]] += 1
        if r["city"]: f["cities"][r["city"]] += 1
        if (r["intake_year"] or "").isdigit(): f["intake_years"][int(r["intake_year"])] += 1
        s = _f(r["salary_annual_aud"]);  cd = _d(r["application_close_date"])
        if s: f["salaries"].append(s)
        if cd and cd >= today and (f["next_close"] is None or cd < f["next_close"]):
            f["next_close"] = cd
        if r["evidence_span"] and len(f["evidence_samples"]) < 2:
            f["evidence_samples"].append(r["evidence_span"])
    cards = []
    for name, f in firms.items():
        popular_programs = [PROGRAM_LABELS.get(k, k) for k, _ in f["program_counts"].most_common(2)]
        avg_salary = round(mean(f["salaries"])) if f["salaries"] else None
        top_city = f["cities"].most_common(1)[0][0] if f["cities"] else None
        top_intake = f["intake_years"].most_common(1)[0][0] if f["intake_years"] else None
        cities_count = len(f["cities"])
        cards.append({
            "name": name,
            "insights_count": f["insights_count"],
            "avg_salary": avg_salary,
            "popular_programs": popular_programs,
            "top_city": top_city,
            "top_intake": top_intake,
            "cities_count": cities_count,
            "next_close": f["next_close"].isoformat() if f["next_close"] else None,
            "evidence_samples": f["evidence_samples"],
        })
    cards.sort(key=lambda x: (-x["insights_count"], x["name"]))
    return cards

def load_cards(csv_path="out/grad_program_signals.csv"):
    return aggregate_by_firm(load_grad_signals(csv_path))
