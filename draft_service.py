
# draft_service.py — build a factual draft from CSVs (stdlib only)

import csv, re, os
from typing import List, Dict, Optional

CSV_PATHS = ["law_raw.csv", "law_whirlpool_2018_2025.csv", "raw_all.csv"]

# --- minimal cleaner (same spirit as our filters) ---
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

MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"

def has(t: str, keys: List[str]) -> bool:
    t = t.lower(); return any(k in t for k in keys)

def detect_steps(t: str) -> List[str]:
    t = t.lower(); found=[]
    for label, keys in STEP_TOKENS:
        if any(k in t for k in keys): found.append(label)
    order = [s for s,_ in STEP_TOKENS]
    return [s for s in order if s in found]

def guess_type(t: str) -> Optional[str]:
    for label, keys in TYPE_TOKENS:
        if has(t, keys): return label
    return None

def parse_salary(t: str) -> List[int]:
    t = t.lower().replace(",", "")
    out=[]
    out += [int(m.group(1)) for m in re.finditer(r"\$\s*(\d{5,6})", t)]
    out += [int(m.group(1))*1000 for m in re.finditer(r"\b(\d{2,3})\s*k\b", t)]
    return out

def parse_hours(t: str) -> List[int]:
    out=[]
    for m in re.finditer(r"\b(\d{2,3})\s*hours?\b", t.lower()):
        v=int(m.group(1)); 
        if 20<=v<=120: out.append(v)
    for m in re.finditer(r"\b(\d{3,4})\s*billable\b", t.lower()):
        out.append(int(m.group(1))//52)
    return out

def load_rows_for_firm(firm: str) -> List[Dict]:
    rows=[]
    target = firm.lower().replace("&","and").strip()
    for p in CSV_PATHS:
        if not os.path.exists(p): continue
        with open(p, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                raw = (row.get("content") or "").strip()
                if not raw: continue
                txt = clean_text(raw)
                hay = (txt + " " + (row.get("thread_title") or "") + " " + (row.get("firm_name") or "")).lower()
                if target in hay.replace("&","and"):
                    row = dict(row); row["content"] = txt
                    rows.append(row)
    return rows

def top(items: List[str], n=2) -> List[str]:
    # keep order of first appearance but cap to n
    seen=set(); out=[]
    for x in items:
        if x and x not in seen:
            seen.add(x); out.append(x)
        if len(out)>=n: break
    return out

def build_draft(firm: str) -> Dict:
    rows = load_rows_for_firm(firm)
    if not rows:
        return {"company": firm, "evidence_count": 0}

    salaries, hours = [], []
    types, outcomes, steps_all, tips, pos_sents, neg_sents = [], [], [], [], [], []
    themes_counts: Dict[str,int] = {}

    for row in rows:
        t = row["content"]
        salaries += parse_salary(t)
        hours    += parse_hours(t)
        steps    = detect_steps(t); 
        if steps: steps_all.append(" → ".join(steps))
        typ = guess_type(t); 
        if typ: types.append(typ)
        if re.search(r"\boffer(s|ed)?\b", t, re.I): outcomes.append("Offer")
        elif re.search(r"\breject(ed|ion)\b|\bunsuccessful\b", t, re.I): outcomes.append("Rejected")
        elif re.search(r"\bwaitlist|on hold\b", t, re.I): outcomes.append("Waitlist")
        elif re.search(r"\binterview|assessment\b", t, re.I): outcomes.append("Interviewed")

        # themes
        def add(th): themes_counts[th] = themes_counts.get(th, 0)+1
        if re.search(rf"\b({MONTHS})\b|\b\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}\b|\b20\d{{2}}\b", t, re.I): add("Application timeline")
        if steps: add("Selection process")
        if parse_salary(t): add("Pay & benefits")
        if parse_hours(t):  add("Hours & workload")
        if has(t, ["rotation","rotations","seat","program"]): add("Program structure")
        if has(t, ["mentor","buddy","training","plt","admission","onboarding"]): add("Training & support")
        if has(t, ["secondment","client secondment","international"]): add("Secondments & mobility")
        if has(t, ["penultimate","final year","gpa","citizenship","visa"]): add("Eligibility & requirements")
        if has(t, ["culture","collegial","supportive","toxic","pressure","burnout","micromanage","team"]): add("Culture & environment")
        if has(t, ["tip","advice","be ready","expect","they asked","case","group exercise","writing test"]): add("Interview tips")

        # snippets
        sents = [s.strip() for s in re.split(r"[.!?]\s*", t) if s.strip() and not s.strip().endswith("?")]
        if has(t, POS): pos_sents += sents[:1]
        if has(t, NEG): neg_sents += sents[:1]
        if has(t, ["tip","advice","be ready","expect","they asked","case","group exercise","writing test"]): tips += sents[:1]

    # summaries
    from statistics import median, mean
    med_salary = int(median(salaries)) if salaries else None
    avg_hours  = int(mean(hours)) if hours else None
    exp_type   = types[0] if types else ""
    outcome    = outcomes[0] if outcomes else ""
    process    = steps_all[0] if steps_all else ""
    top_themes = [k for k,_ in sorted(themes_counts.items(), key=lambda x:(-x[1], x[0]))[:5]]

    culture_line = ""
    if pos_sents: culture_line += "Positives: " + "; ".join(top(pos_sents,2))
    if neg_sents: culture_line += (" " if culture_line else "") + "Watchouts: " + "; ".join(top(neg_sents,2))

    return {
        "company": firm,
        "experience_type": exp_type,
        "outcome": outcome,
        "salary": med_salary,
        "avg_hours": avg_hours,
        "key_themes": top_themes,
        "process_line": process,
        "pay_line": (f"Base around ${med_salary:,} incl. super (from posts)" if med_salary else ""),
        "hours_line": (f"Typical hours ~{avg_hours}/week (from posts)" if avg_hours else ""),
        "culture_para": culture_line,
        "tips_line": " • ".join(top(tips,4)),
        "evidence_count": len(rows)
    }
