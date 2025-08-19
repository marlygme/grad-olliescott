
# seed_from_csv.py
# Build "seed submissions" per firm from existing CSVs (stdlib only).
import csv, re, os, json, argparse, statistics, random
from typing import List, Dict, Optional, Tuple

CSV_PATHS = ["law_raw.csv", "law_whirlpool_2018_2025.csv", "raw_all.csv"]

# Try to reuse project aliases/cleaner if present
try:
    from experience_value_filter_v4 import clean_text  # type: ignore
except Exception:
    NOISE = [
        r"User\s?#\d+.*?(Forum (Regular|Participant)|Enthusiast|Addict).*?(?=posted|$)",
        r"\bO\.P\.\b", r"\bref:\s*whrl\.pl/\S+", r"\bwhrl\.pl/\S+",
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

# Basic heuristics
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
POS = ["supportive","collegial","friendly","helpful","nice","fair","great","good"]
NEG = ["toxic","long hours","late","weekend","overworked","burnout","pressure","micromanage","stress"]
TIP_HINTS = ["be ready","expect","they asked","question was","case","group exercise","writing test","tips","advice","prepare"]

MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"

def has(t: str, keys: List[str]) -> bool:
    s = t.lower()
    return any(k in s for k in keys)

def detect_steps(t: str) -> List[str]:
    s = t.lower()
    found = []
    for label, keys in STEP_TOKENS:
        if any(k in s for k in keys): found.append(label)
    order = [x for x,_ in STEP_TOKENS]
    return [x for x in order if x in found]

def guess_type(t: str) -> Optional[str]:
    s=t.lower()
    for label, keys in TYPE_TOKENS:
        if any(k in s for k in keys): return label
    return None

def parse_salary(t: str) -> List[int]:
    s=t.lower().replace(",","")
    out = [int(m.group(1)) for m in re.finditer(r"\$\s*(\d{5,6})", s)]
    out += [int(m.group(1))*1000 for m in re.finditer(r"\b(\d{2,3})\s*k\b", s)]
    return out

def parse_hours(t: str) -> List[int]:
    s=t.lower()
    out = [int(m.group(1)) for m in re.finditer(r"\b(\d{2,3})\s*hours?\b", s) if 20<=int(m.group(1))<=120]
    out += [int(m.group(1))//52 for m in re.finditer(r"\b(\d{3,4})\s*billable\b", s)]
    return out

def sentences(t: str) -> List[str]:
    return [x.strip() for x in re.split(r"[.!?]\s*", t) if x.strip()]

def good_bits(t: str) -> List[str]:
    # short, non-question snippets
    return [s for s in sentences(t) if len(s) >= 30 and not s.endswith("?")][:2]

def load_by_firm() -> Dict[str, List[str]]:
    """Return {firm: [cleaned post text, ...]} using firm_name col or text/title match."""
    firms: Dict[str, List[str]] = {}
    for p in CSV_PATHS:
        if not os.path.exists(p): continue
        with open(p, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                raw = (row.get("content") or "").strip()
                if not raw: continue
                txt = clean_text(raw)
                if not txt: continue
                firm = (row.get("firm_name") or row.get("firm") or "").strip()
                hay  = f"{txt} {(row.get('thread_title') or '')}".lower()
                if not firm:
                    # naive fallback: pick a capitalised word pair as firm (rare path)
                    m = re.search(r"\b([A-Z][a-z]+(?:\s+[&A-Za-z][a-z]+){0,3})\b", row.get("thread_title",""))
                    firm = m.group(0) if m else ""
                if not firm: 
                    # try a few known legal brands in text
                    for candidate in ["Allens","Ashurst","MinterEllison","Clayton Utz","K&L Gates","White & Case",
                                      "Gilbert + Tobin","King & Wood Mallesons","Corrs Chambers Westgarth",
                                      "Herbert Smith Freehills","HWL Ebsworth","Hall & Wilcox"]:
                        if candidate.lower().replace("&","and") in hay.replace("&","and"):
                            firm = candidate; break
                if not firm: continue
                firms.setdefault(firm, []).append(txt)
    return firms

def summarise_firm(firm: str, posts: List[str]) -> Dict:
    random.seed(hash(firm) & 0xffff)  # deterministic sample per firm
    sample = posts[:80]  # cap processing
    salaries, hours, steps_all, tips, pos, neg, types, outcomes = [], [], [], [], [], [], [], []
    themes: Dict[str,int] = {}
    for t in sample:
        salaries += parse_salary(t); hours += parse_hours(t)
        steps = detect_steps(t)
        if steps: steps_all.append(" → ".join(steps))
        typ = guess_type(t); 
        if typ: types.append(typ)
        if re.search(r"\boffer(s|ed)?\b", t, re.I): outcomes.append("Offer")
        elif re.search(r"\breject(ed|ion)\b|\bunsuccessful\b", t, re.I): outcomes.append("Rejected")
        elif re.search(r"\bwaitlist|on hold\b", t, re.I): outcomes.append("Waitlist")
        elif re.search(r"\binterview|assessment\b", t, re.I): outcomes.append("Interviewed")

        def add(th): themes[th] = themes.get(th,0)+1
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

        if has(t, POS): pos += good_bits(t)
        if has(t, NEG): neg += good_bits(t)
        if has(t, TIP_HINTS): tips += good_bits(t)

    med_salary = int(statistics.median(salaries)) if salaries else None
    avg_hours  = int(statistics.mean(hours)) if hours else None
    process    = steps_all[0] if steps_all else ""
    exp_type   = types[0] if types else ""
    outcome    = outcomes[0] if outcomes else ""
    top_themes = [k for k,_ in sorted(themes.items(), key=lambda x:(-x[1], x[0]))[:5]]

    culture_line = ""
    if pos: culture_line += "Positives: " + "; ".join(pos[:2])
    if neg: culture_line += (" " if culture_line else "") + "Watchouts: " + "; ".join(neg[:2])

    draft = {
        "company": firm,
        "experience_type": exp_type,
        "outcome": outcome,
        "total_salary": med_salary or "",
        "key_themes": top_themes,
        "selection_process": process,
        "pay_benefits": (f"Base around ${med_salary:,} incl. super (from posts)" if med_salary else ""),
        "hours_workload": (f"Typical hours ~{avg_hours}/week (from posts)" if avg_hours else ""),
        "culture_env": culture_line,
        "interview_tips": " • ".join(list(dict.fromkeys(tips))[:4]),
        "source": "csv_seed",
        "is_seed": True,
    }
    # also a pre-rendered card body for the Experiences list
    parts = [p for p in [
        f"Selection process: {process}" if process else "",
        draft["pay_benefits"] or "",
        draft["hours_workload"] or "",
        draft["culture_env"] or "",
        ("Tips: " + draft["interview_tips"]) if draft["interview_tips"] else "",
    ] if p]
    draft["card_text"] = " • ".join(parts)[:500]
    return draft

def build_all(per_firm: int = 3) -> List[Dict]:
    by_firm = load_by_firm()
    seeds: List[Dict] = []
    for firm, posts in by_firm.items():
        if not posts: continue
        # create up to per_firm variations (slight shuffles)
        base = summarise_firm(firm, posts)
        seeds.append({**base, "id": f"seed:{firm}:1"})
        if per_firm >= 2 and len(posts) > 10:
            alt = summarise_firm(firm, posts[5:] + posts[:5])
            alt["id"] = f"seed:{firm}:2"; seeds.append(alt)
        if per_firm >= 3 and len(posts) > 20:
            alt2 = summarise_firm(firm, posts[10:] + posts[:10])
            alt2["id"] = f"seed:{firm}:3"; seeds.append(alt2)
    return seeds

def main():
    ap = argparse.ArgumentParser(description="Build seed submissions from CSVs")
    ap.add_argument("--per-firm", type=int, default=2, help="seed entries per firm (default 2)")
    ap.add_argument("--out", default="seed_submissions.json")
    args = ap.parse_args()

    seeds = build_all(args.per_firm)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(seeds, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(seeds)} seeds to {args.out}")

if __name__ == "__main__":
    main()
