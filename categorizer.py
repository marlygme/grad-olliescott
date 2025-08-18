
# categorizer.py — tiny rule-based tags (stdlib only)
import re
from collections import defaultdict

LABELS = {
    "application_timeline": "Application timeline",
    "selection_process": "Selection process",
    "offer_outcomes": "Offer outcomes",
    "program_structure": "Program structure",
    "pay_benefits": "Pay & benefits",
    "hours_workload": "Hours & workload",
    "culture_environment": "Culture & environment",
    "training_support": "Training & support",
    "secondments_mobility": "Secondments & mobility",
    "eligibility_requirements": "Eligibility & requirements",
    "interview_tips": "Interview tips",
}

CATS = {
    "application_timeline": {"kw": ["open", "close", "deadline", "window", "applications", "intake", "cutoff"], "rx": [r"\b[A-Za-z]{3,9}\s+\d{4}\b", r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"]},
    "selection_process": {"kw": ["online assessment","oa","video interview","vi","assessment centre","assessment center","ac","superday","panel","partner interview","aptitude test"], "rx": []},
    "offer_outcomes": {"kw": ["offer","offers","accepted","rejected","waitlist","on hold","conversion"], "rx": []},
    "program_structure": {"kw": ["rotation","rotations","seat","length","program"], "rx": [r"\b\d+\s+rotations?\b", r"\b\d+\s*(months?|yrs?|years?)\b"]},
    "pay_benefits": {"kw": ["salary","pay","super","bonus","overtime","toil","benefits","allowance"], "rx": [r"\$[\d,]+", r"\b\d+\s*k\b"]},
    "hours_workload": {"kw": ["hours","late","weekend","workload","busy","billable","target","utilisation","utilization"], "rx": [r"\b\d{2}\+?\s*hours?\b", r"\b\d{3,4}\s*billable\b"]},
    "culture_environment": {"kw": ["culture","supportive","toxic","collegial","micromanage","burnout","team","partners"], "rx": []},
    "training_support": {"kw": ["mentor","buddy","training","plt","admission","coaching","feedback","onboarding"], "rx": []},
    "secondments_mobility": {"kw": ["secondment","client secondment","international","relocation"], "rx": []},
    "eligibility_requirements": {"kw": ["penultimate","final year","citizenship","visa","gpa","credit average","requirements"], "rx": []},
    "interview_tips": {"kw": ["tip","advice","be ready","expect","they asked","question was","my experience"], "rx": []},
}

def _score(text: str):
    t = (text or "").lower()
    s = defaultdict(float)
    for slug, spec in CATS.items():
        for k in spec["kw"]:
            if k in t: s[slug] += 1.0
        for pat in spec["rx"]:
            if re.search(pat, t): s[slug] += 1.5
    if re.search(r"\$[\d,]+|\b\d+\s*k\b", t): s["pay_benefits"] += 0.5
    if "billable" in t or "target" in t: s["hours_workload"] += 0.5
    if "rotation" in t or "seat" in t: s["program_structure"] += 0.5
    return s

def classify_text(text: str, threshold: float = 1.0, top_k: int = 3):
    scores = _score(text)
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    kept = [(slug, sc) for slug, sc in ranked if sc >= threshold][:top_k]
    primary = kept[0][0] if kept else (ranked[0][0] if ranked else None)
    return primary, [s for s,_ in kept], kept

def label(slug: str) -> str:
    return LABELS.get(slug, slug.replace("_"," ").title())
