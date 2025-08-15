
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List

try:
    from dateutil import parser as du_parser
    HAVE_DATEUTIL = True
except Exception:
    HAVE_DATEUTIL = False

FIRM_ALIASES: Dict[str, List[str]] = {
    "Clayton Utz": ["clayton utz", "clutz", "claytons"],
    "Allens": ["allens"],
    "Herbert Smith Freehills": ["herbert smith freehills", "hsf", "herbies"],
    "Ashurst": ["ashurst"],
    "MinterEllison": ["minterellison", "minter ellison", "minters"],
    "Colin Biggers & Paisley": ["colin biggers", "cbp", "cb&p"],
    "Lander & Rogers": ["lander & rogers", "landers", "lander and rogers"],
    "Addisons": ["addisons"],
    "Clifford Chance": ["clifford chance", "cc"],
    "King & Wood Mallesons": ["king & wood mallesons", "kwm", "mallesons"],
    "Corrs Chambers Westgarth": ["corrs", "corrs chambers"],
    "Gilbert + Tobin": ["gilbert + tobin", "g+t", "gtobin", "g+tobin", "gilbert and tobin"],
    "HWL Ebsworth": ["hwl", "hwl ebsworth"],
    "Maddocks": ["maddocks"],
    "Sparke Helmore": ["sparke helmore", "sparke"],
    "Hall & Wilcox": ["hall & wilcox", "hall and wilcox", "h&w"],
    "Baker McKenzie": ["baker mckenzie", "bakers"],
    "Norton Rose Fulbright": ["norton rose fulbright", "nrf"],
    "DLA Piper": ["dla piper", "dla"],
    "K&L Gates": ["k&l gates", "klgates", "k l gates"],
    "Arnold Bloch Leibler": ["arnold bloch leibler", "abl"],
    "Johnson Winter Slattery": ["johnson winter slattery", "jws"],
    "White & Case": ["white & case", "white and case"],
}

CITY_ALIASES = {
    "Sydney": ["sydney", "syd"],
    "Melbourne": ["melbourne", "melb"],
    "Brisbane": ["brisbane", "bris"],
    "Perth": ["perth"],
    "Adelaide": ["adelaide", "adel"],
    "Canberra": ["canberra", "cbr"],
    "Hobart": ["hobart"],
}

PROGRAM_TYPES = [
    ("seasonal_clerkship", r"\b(seasonal clerkship|seasonal clerk)\b"),
    ("summer_clerkship", r"\b(summer clerkship|summer clerk)\b"),
    ("winter_clerkship", r"\b(winter clerkship|winter clerk)\b"),
    ("clerkship", r"\b(clerkship|clerkships|clerks?)\b"),
    ("vacation", r"\b(vacation(ers?| program)|vac program)\b"),
    ("graduate", r"\b(graduate program|grad program|grad role|graduate intake|grad intake|graduates?)\b"),
    ("internship", r"\b(intern(ship)?|intern program)\b"),
]

DATE_PATTERNS = [
    r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.? ,?\s+(\d{4})\b",
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b",
    r"\b(\d{4})[-/](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*[-/](\d{1,2})\b",
    r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b",
    r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b",
]

MONTH_MAP = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'sept':9,'oct':10,'nov':11,'dec':12}

def parse_date_to_iso(s: str) -> Optional[str]:
    s = s.strip()
    if not s:
        return None
    if HAVE_DATEUTIL:
        try:
            dt = du_parser.parse(s, dayfirst=True, fuzzy=True)
            return dt.date().isoformat()
        except Exception:
            pass
    import re
    from datetime import datetime
    for pat in DATE_PATTERNS:
        m = re.search(pat, s, flags=re.IGNORECASE)
        if not m:
            continue
        g = [x for x in m.groups()]
        try:
            if len(g)==3 and pat == DATE_PATTERNS[0]:
                d = int(g[0]); mon = MONTH_MAP[g[1][:3].lower()]; y = int(g[2])
            elif len(g)==3 and pat == DATE_PATTERNS[1]:
                mon = MONTH_MAP[g[0][:3].lower()]; d = int(g[1]); y = int(g[2])
            elif len(g)==3 and pat == DATE_PATTERNS[2]:
                y = int(g[0]); mon = MONTH_MAP[g[1][:3].lower()]; d = int(g[2])
            elif len(g)==3 and pat == DATE_PATTERNS[4]:
                y = int(g[0]); mon = int(g[1]); d = int(g[2])
            elif len(g)==3 and pat == DATE_PATTERNS[3]:
                d = int(g[0]); mon = int(g[1]); y = int(g[2]); 
                if y < 100: y += 2000
            else:
                continue
            return datetime(y, mon, d).date().isoformat()
        except Exception:
            continue
    return None

def parse_timestamp_to_utcish(raw: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return raw
    tz_offset = 0
    tz = None
    u = raw.upper()
    if "AEST" in u:
        tz_offset = -10
        tz = "AEST"
    elif "AEDT" in u:
        tz_offset = -11
        tz = "AEDT"
    clean = re.sub(r"\b(AEST|AEDT)\b", "", raw, flags=re.IGNORECASE)
    if HAVE_DATEUTIL:
        try:
            dt = du_parser.parse(clean, dayfirst=True, fuzzy=True)
            if tz:
                from datetime import timedelta
                dt = dt + timedelta(hours=tz_offset)
            return dt.isoformat()
        except Exception:
            return raw
    return raw

def detect_program_type(text: str) -> str:
    for label, pat in PROGRAM_TYPES:
        if re.search(pat, text, re.IGNORECASE):
            return label
    return "ambiguous"

def detect_city(text: str) -> str:
    t = text.lower()
    for city, aliases in CITY_ALIASES.items():
        for a in aliases:
            if re.search(rf"\b{re.escape(a)}\b", t):
                return city
    return "Other/Unknown"

def detect_intake_year(text: str, fallback_year: Optional[int]) -> Optional[int]:
    m = re.search(r"(clerkship|grad(uate)?|intake|program).{0,30}?(20\d{2})", text, re.IGNORECASE)
    if m:
        try:
            return int(re.search(r"(20\d{2})", m.group(0)).group(1))
        except Exception:
            pass
    m = re.search(r"\b(20\d{2})\b", text)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    return fallback_year

def money_to_number(aud_str: str) -> Optional[float]:
    s = aud_str.replace(",", "").lower()
    m = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*(k)?", s)
    if not m:
        return None
    n = float(m.group(1))
    if m.group(2):
        n *= 1000.0
    return n

def detect_salary(text: str) -> Optional[float]:
    m = re.search(r"\$\s*[\d,]+(?:\.\d+)?\s*k?\s*(?:\+\s*super)?", text, re.IGNORECASE)
    if not m:
        return None
    return money_to_number(m.group(0))

def detect_length_months(text: str) -> Optional[int]:
    m = re.search(r"\b(\d{1,2})\s*[- ]?\s*(month|months)\b", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d{1,2})\s*[- ]?\s*(year|years|yr|yrs)\b", text, re.IGNORECASE)
    if m:
        return int(m.group(1)) * 12
    return None

def detect_rotations(text: str) -> Optional[int]:
    m = re.search(r"\b(\d{1,2})\s+rotations?\b", text, re.IGNORECASE)
    return int(m.group(1)) if m else None

def find_dates_near_keywords(text: str, keyword: str) -> Optional[str]:
    for pat in DATE_PATTERNS:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            for kw in re.finditer(keyword, text, flags=re.IGNORECASE):
                if 0 <= (m.start() - kw.end()) <= 60 or 0 <= (kw.start() - m.end()) <= 30:
                    iso = parse_date_to_iso(m.group(0))
                    if iso:
                        return iso
    return None

def extract_evidence_span(text: str, firm_hit: str) -> str:
    t = text
    idx = t.lower().find(firm_hit.lower())
    if idx == -1:
        idx = 0
    start = max(0, idx - 120); end = min(len(t), idx + 120)
    import re as _re
    snippet = _re.sub(r"\s+", " ", t[start:end]).strip()
    return snippet[:240]

def score_confidence(is_exact_alias: bool, program_explicit: bool, city_found: bool, intake_found: bool, month_only_dates: bool, multi_firms: bool) -> float:
    score = 0.5
    score += 0.2 if is_exact_alias else 0.1
    if program_explicit: score += 0.1
    if city_found: score += 0.05
    if intake_found: score += 0.05
    if month_only_dates: score -= 0.1
    if multi_firms: score -= 0.1
    if score < 0: score = 0
    if score > 1: score = 1
    return score
