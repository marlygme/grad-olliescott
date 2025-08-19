
# csv_to_submission_draft.py
# Build a factual draft from forum CSVs to paste into the "Share Your Graduate Experience" form.
# stdlib only.

import csv, re, os, argparse, statistics
from typing import List, Dict, Tuple, Optional

# ---- Basic cleaner ----------------------------------------------------------
NOISE = [
    r"User\s?#\d+.*?(Forum (Regular|Participant)|Enthusiast|Addict).*?(?=posted|$)",
    r"\bO\.P\.\b",
    r"\bref:\s*whrl\.pl/\S+", r"\bwhrl\.pl/\S+",
    r"https?://\S+",
    r"posted\s+\d{4}-[A-Za-z]{3}-\d{1,2},\s+\d{1,2}:\d{2}\s*[ap]m\s*(AEST|AEDT)",
    r"\b(AEST|AEDT)\b",
    r"\b(edit(ed)?|last updated)\b[^\n]*",
]
def clean_text(t: str) -> str:
    if not isinstance(t, str): return ""
    for pat in NOISE: t = re.sub(pat, "", t, flags=re.IGNORECASE)
    t = re.sub(r"@\w+", "", t)
    t = re.sub(r"(?m)^\s*[>\-\•]+\s*", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t

# ---- Simple signals ---------------------------------------------------------
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
STEP_TOKENS = [
    ("Online Assessment", ["online assessment","oa"]),
    ("Video Interview",   ["video interview","vi","one-way video"]),
    ("Assessment Centre", ["assessment centre","assessment center","ac","superday"]),
    ("Partner Interview", ["partner interview","panel"]),
]
TYPE_TOKENS = [
    ("Clerkship", ["clerkship","vacation program","vac program","seasonal clerk"]),
    ("Graduate Program", ["graduate program","grad program"]),
    ("Internship", ["internship","intern"]),
    ("Paralegal", ["paralegal"]),
]
POS = ["supportive","great","good","friendly","collegial","helpful","nice","fair"]
NEG = ["toxic","long hours","late","weekend","overworked","burnout","pressure","micromanage","stress"]
TIP_HINTS = ["be ready","expect","they asked","question was","case","behavioural","behavioral","group exercise","writing test","tips","advice","prepare"]

def has_any(t: str, terms: List[str]) -> bool:
    t = t.lower()
    return any(x in t for x in terms)

def guess_type(t: str) -> Optional[str]:
    t = t.lower()
    for label, keys in TYPE_TOKENS:
        if any(k in t for k in keys): return label
    return None

def parse_salary(t: str) -> List[int]:
    t = t.lower().replace(",", "")
    out = []
    for m in re.finditer(r"\$\s*(\d{5,6})", t):
        out.append(int(m.group(1)))
    for m in re.finditer(r"\b(\d{2,3})\s*k\b", t):
        out.append(int(m.group(1)) * 1000)
    return out

def parse_hours(t: str) -> List[int]:
    out = []
    for m in re.finditer(r"\b(\d{2,3})\s*hours?\b", t.lower()):
        val = int(m.group(1))
        if 20 <= val <= 120: out.append(val)
    # billable targets
    for m in re.finditer(r"\b(\d{3,4})\s*billable\b", t.lower()):
        out.append(int(m.group(1))//52)
    return out

def parse_dates(t: str) -> List[str]:
    out = []
    for m in re.finditer(rf"\b({MONTHS})\b", t, flags=re.IGNORECASE):
        out.append(m.group(0).title())
    for m in re.finditer(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", t):
        out.append(m.group(0))
    for m in re.finditer(r"\b20\d{2}\b", t):
        out.append(m.group(0))
    return out

def detect_steps(t: str) -> List[str]:
    t = t.lower()
    found = []
    for label, keys in STEP_TOKENS:
        if any(k in t for k in keys):
            found.append(label)
    # keep natural order OA -> VI -> AC -> Partner
    order = [s for s,_ in STEP_TOKENS]
    return [s for s in order if s in found]

def outcome_hint(t: str) -> Optional[str]:
    tt = t.lower()
    if "offer" in tt or "accepted" in tt: return "Offer"
    if "rejected" in tt or "unsuccessful" in tt: return "Rejected"
    if "waitlist" in tt or "on hold" in tt: return "Waitlist"
    if "interview" in tt or "ac" in tt or "assessment" in tt: return "Interviewed"
    return None

def key_themes(t: str) -> List[str]:
    themes = []
    if has_any(t, ["deadline","close","open","intake"]) or parse_dates(t): themes.append("Application timeline")
    if detect_steps(t): themes.append("Selection process")
    if parse_salary(t): themes.append("Pay & benefits")
    if parse_hours(t):  themes.append("Hours & workload")
    if has_any(t, POS+NEG): themes.append("Culture & environment")
    if has_any(t, ["rotation","rotations","seat","program"]): themes.append("Program structure")
    if has_any(t, ["mentor","buddy","training","plt","admission","onboarding"]): themes.append("Training & support")
    if has_any(t, ["secondment","client secondment","international"]): themes.append("Secondments & mobility")
    if has_any(t, ["penultimate","final year","gpa","citizenship","visa"]): themes.append("Eligibility & requirements")
    if has_any(t, TIP_HINTS): themes.append("Interview tips")
    return list(dict.fromkeys(themes))  # unique in order

def good_sentences(t: str) -> List[str]:
    sents = [s.strip() for s in re.split(r"[.!?]\s*", t) if s.strip()]
    # exclude questions
    sents = [s for s in sents if not s.endswith("?")]
    return sents[:3]

# ---- Aggregate a firm -------------------------------------------------------
def aggregate_for_firm(inputs: List[str], firm: str) -> Dict:
    rows = []
    for p in inputs:
        if not os.path.exists(p): continue
        with open(p, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                raw = (row.get("content") or "").strip()
                if not raw: continue
                txt = clean_text(raw)
                # firm detection: prefer firm_name column, else look in text/title
                firm_col = (row.get("firm_name") or row.get("firm") or "").strip()
                hay = f"{txt} {(row.get('thread_title') or '')}".lower()
                hit = False
                if firm_col and firm_col.lower() == firm.lower(): hit = True
                if not hit and re.search(rf"\b{re.escape(firm.lower())}\b", hay): hit = True
                if not hit: continue
                rows.append({**row, "content": txt})

    # signals
    salaries, hours = [], []
    steps_counts: Dict[str,int] = {}
    dates, tips, cultures_pos, cultures_neg = [], [], [], []
    types, outcomes = [], []
    themes_counter: Dict[str,int] = {}

    for row in rows:
        t = row["content"]
        salaries += parse_salary(t)
        hours    += parse_hours(t)
        for s in detect_steps(t): steps_counts[s] = steps_counts.get(s,0)+1
        dates   += parse_dates(t)
        types.append(guess_type(t) or "")
        oc = outcome_hint(t)
        if oc: outcomes.append(oc)
        for th in key_themes(t): themes_counter[th] = themes_counter.get(th,0)+1
        # quick culture/tips
        if has_any(t, POS): cultures_pos += good_sentences(t)
        if has_any(t, NEG): cultures_neg += good_sentences(t)
        if has_any(t, TIP_HINTS): tips += good_sentences(t)

    # summaries
    exp_type = (max(set(types), key=types.count) if any(types) else "")
    outcome  = (max(set(outcomes), key=outcomes.count) if outcomes else "")
    step_order = [s for s,_ in STEP_TOKENS]
    steps = [s for s in step_order if steps_counts.get(s)]
    themes_sorted = sorted(themes_counter.items(), key=lambda x: (-x[1], x[0]))
    top_themes = [t for t,_ in themes_sorted[:5]]

    med_salary = int(statistics.median(salaries)) if salaries else None
    avg_hours  = int(statistics.mean(hours)) if hours else None

    # draft paragraphs
    process_line = " → ".join(steps) if steps else ""
    pay_line = f"Base around ${med_salary:,} including super (from posts)" if med_salary else ""
    hours_line = f"Typical hours around {avg_hours} per week (from posts)" if avg_hours else ""
    culture_bits = []
    if cultures_pos: culture_bits.append("Positives: " + "; ".join(cultures_pos[:2]))
    if cultures_neg: culture_bits.append("Watchouts: " + "; ".join(cultures_neg[:2]))

    # tips (short)
    tips = list(dict.fromkeys(tips))[:4]
    tips_line = " • ".join(tips)

    return {
        "company": firm,
        "experience_type": exp_type,
        "outcome": outcome,
        "salary": med_salary,
        "avg_hours": avg_hours,
        "key_themes": top_themes,
        "process_line": process_line,
        "pay_line": pay_line,
        "hours_line": hours_line,
        "culture_para": " ".join(culture_bits),
        "tips_line": tips_line,
        "evidence_count": len(rows)
    }

# ---- Output helpers ---------------------------------------------------------
def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+","-", name.lower()).strip("-")

def write_txt(d: Dict, out_path: str):
    lines = []
    lines.append(f"Company: {d['company']}")
    if d['experience_type']: lines.append(f"Experience Type: {d['experience_type']}")
    if d['outcome']: lines.append(f"Outcome: {d['outcome']}")
    if d['salary']: lines.append(f"Total Salary (incl. super): ${d['salary']:,}")
    if d['key_themes']: lines.append("Key Themes: " + ", ".join(d['key_themes']))
    lines.append("")
    if d['process_line']: lines.append(f"Selection process: {d['process_line']}")
    if d['pay_line']:     lines.append(f"Pay & benefits: {d['pay_line']}")
    if d['hours_line']:   lines.append(f"Hours & workload: {d['hours_line']}")
    if d['culture_para']: lines.append(f"Culture & environment: {d['culture_para']}")
    if d['tips_line']:    lines.append(f"Interview tips: {d['tips_line']}")
    lines.append("")
    lines.append("Note: Draft auto-generated from public posts; please review before submitting.")
    txt = "\n".join(lines)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(txt)

# ---- CLI --------------------------------------------------------------------
def generate_submission_for_firm(firm_name: str) -> Dict:
    """Generate a submission draft for a specific firm using available data"""
    inputs = ["law_raw.csv", "law_whirlpool_2018_2025.csv", "raw_all.csv"]
    return aggregate_for_firm(inputs, firm_name)

def format_submission_html(data: Dict) -> str:
    """Format submission data as HTML for web display"""
    html_parts = []
    
    html_parts.append(f"<h3>Generated Experience for {data['company']}</h3>")
    
    if data['experience_type']:
        html_parts.append(f"<p><strong>Experience Type:</strong> {data['experience_type']}</p>")
    
    if data['outcome']:
        html_parts.append(f"<p><strong>Outcome:</strong> {data['outcome']}</p>")
    
    if data['salary']:
        html_parts.append(f"<p><strong>Total Salary (incl. super):</strong> ${data['salary']:,}</p>")
    
    if data['key_themes']:
        html_parts.append(f"<p><strong>Key Themes:</strong> {', '.join(data['key_themes'])}</p>")
    
    html_parts.append("<hr>")
    
    if data['process_line']:
        html_parts.append(f"<p><strong>Selection process:</strong> {data['process_line']}</p>")
    
    if data['pay_line']:
        html_parts.append(f"<p><strong>Pay & benefits:</strong> {data['pay_line']}</p>")
    
    if data['hours_line']:
        html_parts.append(f"<p><strong>Hours & workload:</strong> {data['hours_line']}</p>")
    
    if data['culture_para']:
        html_parts.append(f"<p><strong>Culture & environment:</strong> {data['culture_para']}</p>")
    
    if data['tips_line']:
        html_parts.append(f"<p><strong>Interview tips:</strong> {data['tips_line']}</p>")
    
    html_parts.append(f"<p><em>Note: Draft auto-generated from {data['evidence_count']} public posts; please review before submitting.</em></p>")
    
    return "\n".join(html_parts)

def main():
    ap = argparse.ArgumentParser(description="Generate a data-assisted submission draft from CSVs")
    ap.add_argument("--firm", required=True, help="Firm canonical name as shown on site (e.g., 'Gilbert + Tobin')")
    ap.add_argument("--in", dest="inputs", nargs="+", required=True, help="Input CSVs (e.g., law_raw.csv ...)")
    ap.add_argument("--out", help="Write text draft to this path (default: out/submission_<firm>.txt)")
    args = ap.parse_args()

    d = aggregate_for_firm(args.inputs, args.firm)
    os.makedirs("out", exist_ok=True)
    out_path = args.out or f"out/submission_{slugify(args.firm)}.txt"
    write_txt(d, out_path)
    print(f"Wrote draft: {out_path}")
    print(f"Evidence posts used: {d['evidence_count']}")

if __name__ == "__main__":
    main()
