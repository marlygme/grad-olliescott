
# experience_quality.py
# Accurate, transparent quality scoring + strong Whirlpool cleaner (stdlib only)

import csv, re, os, argparse
from typing import List, Dict, Optional, Tuple

# --- FIRM MATCHING -----------------------------------------------------------
try:
    # Prefer the project's alias list if present
    from extractors import FIRM_ALIASES  # type: ignore
except Exception:
    # Fallback (minimal)
    FIRM_ALIASES = {
        "Allens": ["allens"],
        "Herbert Smith Freehills": ["hsf","herbert smith freehills","herbies"],
        "Ashurst": ["ashurst"],
        "MinterEllison": ["minter ellison","minterellison","minters"],
        "King & Wood Mallesons": ["kwm","mallesons","king & wood mallesons"],
        "Corrs Chambers Westgarth": ["corrs"],
        "Gilbert + Tobin": ["gilbert + tobin","g+t","gtobin","g+tobin"],
    }

# --- CLEANING ---------------------------------------------------------------

NOISE_PATTERNS = [
    r"User\s?#\d+.*?(Forum Regular|Participant|Enthusiast|Addict).*?(?=posted|\Z)",  # user header
    r"\bO\.P\.\b",                                                       # OP tag
    r"\bref:\s*whrl\.pl/\S+",                                            # whirl refs
    r"\bwhrl\.pl/\S+",                                                   # short links
    r"https?://\S+",                                                     # any URLs
    r"posted\s+\d{4}-[A-Za-z]{3}-\d{1,2},\s+\d{1,2}:\d{2}\s*[ap]m\s*(AEST|AEDT)",
    r"\b(AEST|AEDT)\b",
    r"\b(edit(ed)?|last updated)\b[^\n]*",
]

QUESTION_STARTERS = [
    "anyone know","does anyone","has anyone","is it true","should i",
    "where can i","what are","when do","how long","how do","can i",
    "would it","is there","does it","do they","am i","are we"
]

META_PHRASES = [
    "bump","following","subscribing","any updates","thanks","lol","lmao",
    "haha","dm me","pm me","off-topic","+1","same here"
]

PROGRAM_SIGNALS = [
    "offer","offers","accepted","rejected","waitlist","on hold",
    "clerkship","graduate program","grad program","vacation program",
    "rotation","rotations","seat","assessment centre","assessment center",
    "ac","superday","panel","partner interview","paralegal","salary","pay",
    "remuneration","benefits","billable","hours","culture","mentor",
    "secondment","training","practice group","plt","admission"
]

PAST_TENSE_VERBS = [
    "received","accepted","completed","did","worked","went",
    "rotated","attended","participated","finished","started",
    "applied","interviewed","progressed","declined"
]

MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"

def clean_whirlpool_text(text: str) -> str:
    """Remove Whirlpool-specific metadata & junk; keep the human content."""
    if not isinstance(text, str):
        return ""
    t = text
    # unify whitespace & remove zero-width chars
    t = re.sub(r"[\u200B-\u200D\uFEFF]", "", t)
    for pat in NOISE_PATTERNS:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)
    # strip @mentions & leftover "ref:" tokens
    t = re.sub(r"@\w+", "", t)
    t = re.sub(r"\bref:\b", "", t, flags=re.IGNORECASE)
    # collapse quoting markers or bullets at the start of lines
    t = re.sub(r"(?m)^\s*[>\-\•\•]+\s*", "", t)
    # normalise whitespace
    t = re.sub(r"\s{2,}", " ", t).strip()
    # discard near-empty/placeholder
    if len(t) < 5 or t.lower() in {"deleted","edited"}:
        return ""
    return t

# --- FEATURE EXTRACTORS -----------------------------------------------------

def _words(text: str) -> List[str]:
    return re.findall(r"\b[^\W_]+\b", text.lower())

def _sentences(text: str) -> List[str]:
    # minimal sentence split
    return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

def is_question(text: str) -> bool:
    t = text.strip().lower()
    if not t: return False
    if t.endswith("?"): return True
    if any(t.startswith(s) for s in QUESTION_STARTERS): return True
    if t.count("?") >= 2: return True
    return False

def is_meta_low(text: str) -> bool:
    t = text.strip().lower()
    if not t: return True
    if any(p in t for p in META_PHRASES):
        # Avoid penalising long useful posts that include "thanks"
        if "thanks" in t and len(t) > 160:
            return False
        return True
    # super short acknowledgements
    if len(t) < 20 and any(w in t for w in ["yes","no","ok","thanks","same"]):
        return True
    return False

def info_signals(text: str) -> Dict[str, bool]:
    t = text.lower()
    return {
        "has_money": bool(re.search(r"\$\s*[\d,]+|\b\d+\s*k\b", t)),
        "has_date": bool(re.search(rf"\b({MONTHS})\b|\b\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}\b|\b20\d{{2}}\b", t)),
        "has_number": bool(re.search(r"\b\d+\b", t)),
    }

def count_program_signals(text: str) -> int:
    t = text.lower()
    return sum(1 for k in PROGRAM_SIGNALS if k in t)

def has_past_tense(text: str) -> bool:
    t = text.lower()
    return any(v in t for v in PAST_TENSE_VERBS)

def density(text: str) -> Tuple[int,int,int,float]:
    w = _words(text)
    uw = len(set(w))
    wc = len(w)
    sc = len(_sentences(text))
    dens = (uw / wc) if wc else 0.0
    return wc, uw, sc, dens

# --- QUALITY SCORING --------------------------------------------------------

def quality_score(text: str) -> Tuple[float, Dict[str, float]]:
    """
    Returns (score 0..1, breakdown dict).
    Transparent additive model:
      + length & uniqueness
      + program/domain signals, money/dates, past-tense
      - questions, meta/filler, extreme short
    """
    base = 0.40
    brk = {"base": base}

    wc, uw, sc, dens = density(text)

    # Length bonus (up to +0.20 around 80..260 words)
    length_bonus = 0.0
    if wc >= 60:
        length_bonus = min(0.20, (wc - 60) / 1000 * 200)  # gentle ramp to +0.2
    brk["length"] = length_bonus

    # Uniqueness/density bonus (up to +0.10)
    dens_bonus = min(0.10, max(0.0, (dens - 0.45) * 0.5))  # reward beyond ~0.45 type-token
    brk["density"] = dens_bonus

    # Program/domain signals (max +0.20)
    ps = count_program_signals(text)
    prog_bonus = min(0.20, ps * 0.05)
    brk["program_signals"] = prog_bonus

    # Money/Date/Number (+0.10 if any two, +0.05 if one)
    sigs = info_signals(text)
    sig_count = sum(1 for v in sigs.values() if v)
    sig_bonus = 0.10 if sig_count >= 2 else (0.05 if sig_count == 1 else 0.0)
    brk["info_signals"] = sig_bonus

    # Past-tense experiential (+0.10)
    past_bonus = 0.10 if has_past_tense(text) else 0.0
    brk["past_tense"] = past_bonus

    # Penalties
    penalty = 0.0
    # Short content penalty (-0.20 if <80w or <20 unique)
    if wc < 80 or uw < 20:
        penalty += 0.20
    # Question penalty (-0.25 if question and not long)
    if is_question(text) and wc < 120:
        penalty += 0.25
    # Meta/filler penalty (-0.15)
    if is_meta_low(text):
        penalty += 0.15
    brk["penalty"] = -penalty

    score = base + length_bonus + dens_bonus + prog_bonus + sig_bonus + past_bonus - penalty
    score = max(0.0, min(1.0, score))
    brk["final"] = score
    return score, brk

# --- FIRM MATCHING ----------------------------------------------------------

def match_firm(text: str, title: str = "") -> Optional[str]:
    hay = f"{text} {title}".lower()
    for canonical, aliases in FIRM_ALIASES.items():
        if re.search(rf"\b{re.escape(canonical.lower())}\b", hay):
            return canonical
        for a in aliases:
            if re.search(rf"\b{re.escape(a.lower())}\b", hay):
                return canonical
    return None

# --- CORE PIPELINE ----------------------------------------------------------

FIELDNAMES = [
    "firm_name","content","raw_content","timestamp","thread_url",
    "quality_score","is_question","is_meta_low","is_too_short","words","unique_words","sentences","reasons"
]

def process_csvs(inputs: List[str], firm: Optional[str]=None) -> List[Dict]:
    out: List[Dict] = []
    for path in inputs:
        if not os.path.exists(path):
            print(f"Warning: {path} not found")
            continue
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                raw = (row.get("content") or "").strip()
                if not raw: continue
                clean = clean_whirlpool_text(raw)
                if not clean: continue

                firm_hit = match_firm(clean, row.get("thread_title","") or "")
                if not firm_hit: continue
                if firm and firm_hit.lower() != firm.lower(): continue

                # score on CLEAN text
                s, _ = quality_score(clean)
                wc, uw, sc, _ = density(clean)

                is_q = is_question(clean)
                is_meta = is_meta_low(clean)
                is_short = (wc < 80 or uw < 20)

                reasons = []
                if s >= 0.70: reasons.append("high_quality")
                if is_q: reasons.append("question")
                if is_meta: reasons.append("meta")
                if is_short: reasons.append("short")

                out.append({
                    "firm_name": firm_hit,
                    "content": clean,             # <<< UI will render CLEAN text
                    "raw_content": raw,           # keep original for audit
                    "timestamp": row.get("timestamp",""),
                    "thread_url": row.get("thread_url",""),
                    "quality_score": f"{s:.3f}",
                    "is_question": str(is_q),
                    "is_meta_low": str(is_meta),
                    "is_too_short": str(is_short),
                    "words": str(wc),
                    "unique_words": str(uw),
                    "sentences": str(sc),
                    "reasons": ",".join(reasons) if reasons else "",
                })
    return out

def slugify_firm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+","-", name.lower().replace("&","and")).strip("-")

def save_cache(rows: List[Dict], firm_name: str) -> str:
    os.makedirs("out", exist_ok=True)
    p = os.path.join("out", f"experiences_{slugify_firm(firm_name)}.csv")
    with open(p, "w", newline="", encoding="utf-8") as g:
        w = csv.DictWriter(g, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    return p

def load_filtered_for_firm(firm_name: str, min_score: float=0.60, exclude_questions: bool=True) -> List[Dict]:
    """Drop-in helper for Flask routes."""
    cache = os.path.join("out", f"experiences_{slugify_firm(firm_name)}.csv")
    rows: List[Dict] = []
    # Prefer cache if present
    if os.path.exists(cache):
        with open(cache, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                try:
                    q = float(row.get("quality_score","0") or 0)
                except Exception:
                    q = 0.0
                is_q = (row.get("is_question","false").lower() == "true")
                if q >= min_score and (not exclude_questions or not is_q):
                    # Guarantee we render CLEAN text
                    if not row.get("content") and row.get("raw_content"):
                        row["content"] = clean_whirlpool_text(row["raw_content"])
                    rows.append(row)
        return rows
    # Build from raw if no cache
    inputs = ["law_raw.csv","law_whirlpool_2018_2025.csv","raw_all.csv"]
    all_rows = process_csvs(inputs, firm_name)
    # filter
    kept = []
    for r in all_rows:
        q = float(r["quality_score"])
        is_q = (r["is_question"].lower() == "true")
        if q >= min_score and (not exclude_questions or not is_q):
            kept.append(r)
    if kept:
        save_cache(kept, firm_name)
    return kept

# --- CLI --------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Quality-score and clean firm experiences")
    ap.add_argument("--in", dest="inputs", nargs="+", required=True, help="Input CSV(s)")
    ap.add_argument("--firm", dest="firm", default=None, help="Optional firm filter (canonical name)")
    ap.add_argument("--out", dest="out", default=None, help="Output CSV (optional)")
    ap.add_argument("--minscore", dest="minscore", type=float, default=0.60, help="Minimum score to keep (default 0.60)")
    ap.add_argument("--exclude-questions", dest="exclude_q", type=int, default=1, help="Exclude questions: 1=yes, 0=no")
    args = ap.parse_args()

    rows = process_csvs(args.inputs, args.firm)
    kept = []
    for r in rows:
        q = float(r["quality_score"])
        is_q = (r["is_question"].lower() == "true")
        if q >= args.minscore and (not args.exclude_q or not is_q):
            kept.append(r)

    print(f"Kept {len(kept)} / {len(rows)} rows", ("for "+args.firm) if args.firm else "")
    # top reasons
    reasons = {}
    for r in rows:
        for token in (r["reasons"] or "").split(","):
            if not token: continue
            reasons[token] = reasons.get(token, 0) + 1
    if reasons:
        print("Reasons:", ", ".join(f"{k}({v})" for k,v in sorted(reasons.items(), key=lambda x: -x[1])[:5]))

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", newline="", encoding="utf-8") as g:
            w = csv.DictWriter(g, fieldnames=FIELDNAMES)
            w.writeheader()
            w.writerows(kept)
        print("Wrote", args.out)

if __name__ == "__main__":
    main()
