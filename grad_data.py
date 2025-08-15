from collections import Counter
from statistics import mean
from datetime import datetime, date
import csv
import os

PROGRAM_LABELS = {
  "graduate":"Graduate Program","clerkship":"Clerkship","summer_clerkship":"Summer Clerkship",
  "winter_clerkship":"Winter Clerkship","seasonal_clerkship":"Seasonal Clerkship",
  "vacation":"Vacation Program","internship":"Internship","ambiguous":"Other"
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
  if not os.path.exists(csv_path):
    return []

  signals = []
  with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
      # Remove username/author fields for privacy
      clean_row = dict(row)
      for field in ['author', 'username', 'user', 'Author', 'User', 'USERNAME', 'name', 'Name']:
        if field in clean_row:
          del clean_row[field]
      signals.append(clean_row)
  return signals

def aggregate_by_firm(rows):
  firms = {}
  for row in rows:
    name = row["firm_name"]
    if not name: continue

    if name not in firms:
      firms[name] = {
        "name": name,
        "experiences_count": 0,
        "program_types": [],
        "cities": [],
        "salaries": [],
        "intake_years": [],
        "open_dates": [],
        "close_dates": [],
        "program_lengths": [],
        "rotation_counts": [],
        "evidence_snippets": [],
        "thread_urls": [],
        "avg_salary": None,
        "salary_range": None,
        "top_city": None,
        "popular_programs": [],
        "next_close": None,
        "top_intake": None,
        "typical_length": None,
        "rotation_info": None,
        "application_timeline": None,
        "selection_process": "Application → Assessment → Interview",
        "eligibility": "Law students in penultimate/final year",
        "locations_count": 0,
        "training_info": "Comprehensive graduate program with rotations",
        "work_culture": "Professional services environment",
        "conversion_rate": "High conversion rate for strong performers",
        "offer_timeline": "Offers typically within 2-4 weeks of interviews"
      }

    firm = firms[name]
    firm["experiences_count"] += 1

    if row["program_type"]: firm["program_types"].append(row["program_type"])
    if row["city"]: firm["cities"].append(row["city"])
    if row["intake_year"]: 
      try: firm["intake_years"].append(int(row["intake_year"]))
      except: pass
    if row["application_open_date"]: firm["open_dates"].append(row["application_open_date"])
    if row["application_close_date"]: firm["close_dates"].append(row["application_close_date"])
    if row["program_length_months"]:
      try: firm["program_lengths"].append(int(row["program_length_months"]))
      except: pass
    if row["rotations_count"]:
      try: firm["rotation_counts"].append(int(row["rotations_count"]))
      except: pass
    if row["salary_annual_aud"]:
      try: firm["salaries"].append(float(row["salary_annual_aud"]))
      except: pass
    if row["evidence_span"]: firm["evidence_snippets"].append(row["evidence_span"])
    if row["thread_url"]: firm["thread_urls"].append(row["thread_url"])

  # Process aggregated data
  for firm in firms.values():
    # Salary info
    if firm["salaries"]:
      firm["avg_salary"] = int(mean(firm["salaries"]))
      firm["salary_range"] = f"${min(firm['salaries']):,.0f} - ${max(firm['salaries']):,.0f}"

    # Location info
    if firm["cities"]:
      city_counts = Counter(firm["cities"])
      firm["top_city"] = city_counts.most_common(1)[0][0]
      firm["locations_count"] = len(set(firm["cities"]))

    # Program info
    if firm["program_types"]:
      type_counts = Counter(firm["program_types"])
      firm["popular_programs"] = [PROGRAM_LABELS.get(t, t) for t, _ in type_counts.most_common(3)]

    # Timeline info
    if firm["intake_years"]:
      firm["top_intake"] = max(set(firm["intake_years"]), key=firm["intake_years"].count)

    if firm["close_dates"]:
      # Find the next upcoming close date
      today = datetime.now().date()
      future_dates = []
      for date_str in firm["close_dates"]:
        try:
          date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
          if date_obj >= today:
            future_dates.append(date_obj)
        except:
          pass
      if future_dates:
        firm["next_close"] = min(future_dates).strftime("%b %d")

    # Program structure
    if firm["program_lengths"]:
      firm["typical_length"] = f"{int(mean(firm['program_lengths']))} months"

    if firm["rotation_counts"]:
      avg_rotations = int(mean(firm["rotation_counts"]))
      firm["rotation_info"] = f"{avg_rotations} rotations typically"

    # Enhanced info based on firm type and evidence
    firm["application_timeline"] = get_application_timeline(firm)
    firm["selection_process"] = get_selection_process(firm)
    firm["eligibility"] = get_eligibility_info(firm)
    firm["training_info"] = get_training_info(firm)
    firm["work_culture"] = get_culture_info(firm)
    firm["conversion_rate"] = get_conversion_info(firm)
    firm["offer_timeline"] = get_offer_timeline(firm)

  return list(firms.values())

def get_application_timeline(firm):
  """Generate application timeline based on evidence"""
  if "clerkship" in str(firm["popular_programs"]).lower():
    return "Applications: Jul-Aug → Interviews: Aug-Sep → Offers: Sep-Oct"
  return "Applications: Mar-May → Interviews: May-Jun → Offers: Jun-Jul"

def get_selection_process(firm):
  """Generate selection process info"""
  evidence_text = " ".join(firm["evidence_snippets"]).lower()

  processes = []
  if "application" in evidence_text:
    processes.append("Application")
  if any(word in evidence_text for word in ["test", "assessment", "psychometric", "watson"]):
    processes.append("Online Assessment")
  if any(word in evidence_text for word in ["video", "hirevue"]):
    processes.append("Video Interview")
  if any(word in evidence_text for word in ["interview", "ac", "assessment centre"]):
    processes.append("Interview/AC")
  if "partner" in evidence_text:
    processes.append("Partner Interview")

  if processes:
    return " → ".join(processes)
  return "Application → Assessment → Interview → Offer"

def get_eligibility_info(firm):
  """Generate eligibility information"""
  evidence_text = " ".join(firm["evidence_snippets"]).lower()

  if "penult" in evidence_text:
    return "Penultimate year law students"
  elif "final" in evidence_text:
    return "Final year law students & graduates"
  elif "wam" in evidence_text or "gpa" in evidence_text:
    return "Law students with strong academic record"

  return "Law students in penultimate/final year"

def get_training_info(firm):
  """Generate training and program info"""
  if firm["rotation_info"]:
    return f"Structured program with {firm['rotation_info']}"
  return "Comprehensive graduate training program"

def get_culture_info(firm):
  """Generate culture information"""
  evidence_text = " ".join(firm["evidence_snippets"]).lower()

  if any(word in evidence_text for word in ["culture", "team", "collaborative"]):
    return "Collaborative team environment"
  elif "international" in evidence_text or "global" in evidence_text:
    return "Global firm with international opportunities"

  return "Professional services environment"

def get_conversion_info(firm):
  """Generate conversion rate info"""
  evidence_text = " ".join(firm["evidence_snippets"]).lower()

  if any(word in evidence_text for word in ["offer", "grad", "conversion"]):
    return "Strong conversion rate for high performers"

  return "Competitive conversion to graduate roles"

def get_offer_timeline(firm):
  """Generate offer timeline info"""
  if "clerkship" in str(firm["popular_programs"]).lower():
    return "Offers: October (priority offer day)"
  return "Offers: 2-4 weeks post final interview"

def load_cards(csv_path="out/grad_program_signals.csv"):
  return aggregate_by_firm(load_grad_signals(csv_path))