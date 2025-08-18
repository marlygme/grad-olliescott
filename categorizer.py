
# categorizer.py — lightweight rule-based classifier (stdlib only)
import re
from collections import defaultdict

# Slug -> display label
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

# Keyword/regex signals per category (extend freely)
CATS = {
    "application_timeline": {
        "kw": ["open", "close", "deadline", "window", "applications", "intake", "by end", "cutoff"],
        "rx": [r"\b[A-Za-z]{3,9}\s+\d{4}\b", r"\b\d{1,2}\s*[/-]\s*\d{1,2}\s*[/-]\s*\d{2,4}\b"],
    },
    "selection_process": {
        "kw": ["online assessment", "oa", "vi", "video interview", "assessment centre", "assessment center",
               "ac", "case interview", "superday", "panel", "partner interview", "aptitude test"],
        "rx": [],
    },
    "offer_outcomes": {
        "kw": ["offer", "offers", "accepted", "rejected", "waitlist", "on hold", "conversion"],
        "rx": [],
    },
    "program_structure": {
        "kw": ["rotation", "rotations", "seat", "seats", "length", "18-month", "18 month", "12-month", "program"],
        "rx": [r"\b\d+\s+rotations?\b", r"\b\d+\s*(months?|yrs?|years?)\b"],
    },
    "pay_benefits": {
        "kw": ["salary", "pay", "super", "bonus", "overtime", "toil", "benefits", "allowance"],
        "rx": [r"\$[\d,]+", r"\b\d+\s*k\b"],
    },
    "hours_workload": {
        "kw": ["hours", "late", "weekend", "workload", "busy", "billable", "target", "utilisation", "utilization"],
        "rx": [r"\b\d{2}\+?\s*hours?\b", r"\b\d{3,4}\s*billable\b"],
    },
    "culture_environment": {
        "kw": ["culture", "supportive", "toxic", "nice", "collegial", "micromanage", "burnout", "team", "partners"],
        "rx": [],
    },
    "training_support": {
        "kw": ["mentor", "buddy", "training", "plt", "admission", "coaching", "feedback", "onboarding"],
        "rx": [],
    },
    "secondments_mobility": {
        "kw": ["secondment", "client secondment", "international", "rotation overseas", "relocation"],
        "rx": [],
    },
    "eligibility_requirements": {
        "kw": ["penultimate", "final year", "citizenship", "visa", "gpa", "credit average", "requirements"],
        "rx": [],
    },
    "interview_tips": {
        "kw": ["tip", "advice", "be ready", "expect", "my experience", "question was", "they asked"],
        "rx": [],
    },
}

def _score(text: str) -> dict:
    text_lc = text.lower()
    scores = defaultdict(float)
    for slug, spec in CATS.items():
        for k in spec["kw"]:
            if k in text_lc:
                scores[slug] += 1.0
        for pat in spec["rx"]:
            if re.search(pat, text_lc):
                scores[slug] += 1.5
    # cross-boosts
    if any(re.search(r"\$[\d,]+|\b\d+\s*k\b", text_lc) for _ in [0]):
        scores["pay_benefits"] += 0.5
    if "billable" in text_lc or "target" in text_lc:
        scores["hours_workload"] += 0.5
    if "rotation" in text_lc or "seat" in text_lc:
        scores["program_structure"] += 0.5
    return scores

def classify_text(text: str, threshold: float = 1.0, top_k: int = 3):
    """
    Returns (primary_slug, [slugs], details)
    - primary_slug: best category or None
    - slugs: all categories with score >= threshold (max top_k)
    - details: list of (slug, score) sorted desc
    """
    if not isinstance(text, str) or not text.strip():
        return None, [], []
    scores = _score(text)
    if not scores:
        return None, [], []
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    kept = [(s, sc) for s, sc in ranked if sc >= threshold][:top_k]
    primary = kept[0][0] if kept else ranked[0][0]
    return primary, [s for s, _ in kept], kept

def label(slug: str) -> str:
    return LABELS.get(slug, slug.replace("_", " ").title())
