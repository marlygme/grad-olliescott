
# seed_from_csv.py
# Build "seed submissions" per firm from existing CSVs in Share Story format.
import csv, re, os, json, argparse, statistics, random
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

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

# Experience type mapping based on themes
THEME_TO_TYPE = {
    "Programs": "Clerkship",
    "Applications": "Graduate Program", 
    "Interviews": "Graduate Program",
    "Salaries": "Graduate Program",
    "Start Dates": "Graduate Program",
    "Offers & Rejections": "Graduate Program",
    "Firm Culture": "Clerkship",
    "Practice Areas": "Clerkship",
    "Locations": "Clerkship",
    "Other": "Graduate Program"
}

THEME_TO_STORY_FOCUS = {
    "Programs": "program_structure",
    "Applications": "application_stages", 
    "Interviews": "interview_experience",
    "Salaries": "advice",
    "Start Dates": "advice",
    "Offers & Rejections": "interview_experience",
    "Firm Culture": "advice",
    "Practice Areas": "advice",
    "Locations": "advice",
    "Other": "advice"
}

def load_csv_data() -> List[Dict]:
    """Load and clean CSV data with themes and firms."""
    csv_file = "attached_assets/Auslaw_Comments_with_Themes_and_Firms_1754309543165.csv"
    if not os.path.exists(csv_file):
        return []
    
    data = []
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = row.get("Business", "").strip()
            theme = row.get("Theme", "Other").strip()
            comment = row.get("Comment", "").strip()
            
            if company and comment:
                data.append({
                    "company": company,
                    "theme": theme,
                    "comment": clean_text(comment),
                    "original_comment": comment
                })
    return data

def generate_realistic_stages(comment: str, theme: str) -> str:
    """Generate application stages based on comment content and theme."""
    stages = []
    comment_lower = comment.lower()
    
    # Always start with application
    stages.append("Online application with CV and cover letter")
    
    if any(word in comment_lower for word in ["online", "test", "assessment", "oa", "aptitude", "cognitive"]):
        stages.append("Online assessment (aptitude/situational judgment)")
        
    if any(word in comment_lower for word in ["video", "interview", "phone", "call", "screening"]):
        stages.append("Phone/video interview with HR")
        
    if any(word in comment_lower for word in ["assessment centre", "ac", "group", "presentation", "exercise"]):
        stages.append("Assessment centre with group exercises and presentations")
    elif theme == "Interviews" and "partner" not in comment_lower:
        stages.append("In-person interview with team members")
        
    if any(word in comment_lower for word in ["partner", "final", "panel", "senior"]):
        stages.append("Final interview with partners/senior staff")
    
    # Ensure at least 3 stages for realism
    if len(stages) < 3:
        stages.insert(-1, "Competency-based interview")
    
    return " → ".join(stages)

def generate_interview_experience(comment: str, theme: str) -> str:
    """Generate interview experience based on comment and theme."""
    comment_lower = comment.lower()
    
    # Extract interview-specific content
    if any(word in comment_lower for word in ["interview", "panel", "video", "phone", "assessment centre", "ac"]):
        sentences = [s.strip() for s in re.split(r'[.!?]', comment) if any(word in s.lower() for word in ["interview", "panel", "video", "phone", "assessment", "asked", "question"])]
        if sentences:
            best_sentence = max(sentences, key=len)
            return clean_text(best_sentence)[:300] + ("..." if len(best_sentence) > 300 else "")
    
    # Theme-based realistic content
    if theme == "Interviews":
        return "Competency-based interview with questions about motivation, commercial awareness, and why this firm. Asked about recent deals and current events affecting the legal industry."
    elif theme == "Applications":
        return "Initial application screening followed by phone interview with HR, then video interview with senior associate covering technical and behavioral questions."
    elif theme == "Programs":
        return "Interview focused on understanding of the clerkship program structure and rotation preferences. Questions about teamwork and adaptability."
    else:
        return "Standard interview process covering motivation for law, interest in the firm, and scenario-based questions about client service."

def generate_advice(comment: str, theme: str) -> str:
    """Generate advice based on comment content and theme."""
    advice_parts = []
    comment_lower = comment.lower()
    
    # Enhanced advice indicators (actionable words)
    advice_indicators = [
        "recommend", "suggest", "should", "must", "need to", "make sure", "prepare", 
        "practice", "research", "apply early", "tailor", "focus on", "emphasize", 
        "avoid", "don't", "be sure to", "remember to", "consider", "try to"
    ]
    
    # Question indicators to exclude
    question_indicators = [
        "does that mean", "what does", "how does", "why does", "is it", "are they", 
        "do you", "did you", "have you", "will they", "would you", "can you", 
        "could you", "might", "maybe", "perhaps", "i wonder", "wondering if"
    ]
    
    # Non-advice indicators to exclude
    non_advice_indicators = [
        "i think", "i believe", "in my opinion", "it seems", "appears to be",
        "i heard", "rumor", "supposedly", "allegedly", "not sure if", "unclear",
        "partnership doesn't have", "doesn't mean", "probably", "likely"
    ]
    
    sentences = [s.strip() for s in re.split(r'[.!?]', comment) if s.strip()]
    
    # Find sentences with advice indicators
    advice_sentences = []
    for sentence in sentences:
        sentence_lower = sentence.lower()
        
        # Skip if it's a question
        if (sentence.strip().endswith('?') or 
            any(q_ind in sentence_lower for q_ind in question_indicators)):
            continue
            
        # Skip if it contains non-advice indicators
        if any(na_ind in sentence_lower for na_ind in non_advice_indicators):
            continue
            
        # Check for advice indicators
        if any(indicator in sentence_lower for indicator in advice_indicators):
            cleaned = clean_text(sentence)
            # More stringent requirements for advice
            if (len(cleaned) > 30 and  # Longer minimum length
                not cleaned.lower().startswith(('i think', 'i believe', 'maybe', 'perhaps')) and
                any(word in cleaned.lower() for word in ['should', 'recommend', 'prepare', 'make sure', 'focus', 'avoid', 'remember'])):
                advice_sentences.append(cleaned)
    
    if advice_sentences:
        advice_parts.extend(advice_sentences[:2])  # Top 2 pieces of advice
    
    # Theme-specific advice if no good advice found
    if not advice_parts:
        import random
        if theme == "Applications":
            fallback_options = [
                "Start applications early and thoroughly research each firm's practice areas and recent work.",
                "Tailor your application to show specific interest in the firm's key practice areas.",
                "Apply early in the application window and ensure your cover letter is firm-specific."
            ]
        elif theme == "Interviews":
            fallback_options = [
                "Prepare for competency-based questions and be ready to discuss your motivation for commercial law.",
                "Practice discussing recent commercial news and how it affects the legal industry.", 
                "Research the firm's recent deals and be ready to discuss why you're interested in their work."
            ]
        elif theme == "Firm Culture":
            fallback_options = [
                "Ask current employees about day-to-day work culture and opportunities for mentorship.",
                "Research the firm's values and recent initiatives to understand their culture.",
                "Connect with current employees on LinkedIn to learn about their experiences."
            ]
        elif theme == "Salaries":
            fallback_options = [
                "Research market rates through graduate surveys and be prepared to discuss total package including benefits.",
                "Consider the full package including professional development opportunities, not just base salary.",
                "Ask about salary progression and performance review processes during interviews."
            ]
        elif theme == "Programs":
            fallback_options = [
                "Understand the rotation structure and express genuine interest in multiple practice areas.",
                "Research each practice area offered and be ready to discuss your interests in rotations.",
                "Ask about mentorship programs and training opportunities available to graduates."
            ]
        else:
            fallback_options = [
                "Be genuine in your interest, prepare thoroughly, and show enthusiasm for learning.",
                "Research the firm's recent work and be ready to discuss why you're interested in their practice.",
                "Demonstrate your commitment to commercial law through relevant experiences and knowledge."
            ]
        
        advice_parts.append(random.choice(fallback_options))
    
    return " ".join(advice_parts)[:500]

def create_share_story_entry(company: str, theme: str, comment: str) -> Dict:
    """Create a realistic Share Story submission entry."""
    experience_type = THEME_TO_TYPE.get(theme, "Graduate Program")
    
    # Weight roles based on experience type
    if experience_type == "Clerkship":
        roles = ["Summer Clerk", "Vacation Clerk", "Seasonal Clerk"]
    elif experience_type == "Graduate Program":
        roles = ["Graduate Lawyer", "Graduate", "Junior Lawyer"]
    else:
        roles = ["Graduate Lawyer", "Summer Clerk", "Paralegal", "Legal Intern"]
    
    # Generate realistic content
    application_stages = generate_realistic_stages(comment, theme)
    interview_experience = generate_interview_experience(comment, theme)
    advice = generate_advice(comment, theme)
    
    # Random but realistic timestamp (last 2 years, weighted toward recent)
    days_back = random.choices([30, 90, 180, 365, 730], weights=[30, 25, 20, 15, 10])[0]
    base_date = datetime.now() - timedelta(days=random.randint(1, days_back))
    
    return {
        "company": company,
        "role": random.choice(roles),
        "experience_type": experience_type,
        "theme": theme,
        "application_stages": application_stages,
        "interview_experience": interview_experience,
        "advice": advice,
        "timestamp": base_date.isoformat(),
        "user_id": f"seed_user_{random.randint(1000, 9999)}",
        "user_name": f"Graduate{random.randint(100, 999)}",
        "source": "csv_seed"
    }

def build_share_story_submissions(min_per_firm: int = 2, max_per_firm: int = 4) -> List[Dict]:
    """Build Share Story format submissions from CSV data."""
    csv_data = load_csv_data()
    if not csv_data:
        print("No CSV data found")
        return []
    
    # Group by company
    by_company = {}
    for entry in csv_data:
        company = entry["company"]
        if company not in by_company:
            by_company[company] = []
        by_company[company].append(entry)
    
    submissions = []
    
    for company, entries in by_company.items():
        # Generate 2-4 submissions per company
        num_submissions = min(max_per_firm, max(min_per_firm, len(entries)))
        
        # Sample entries to avoid duplicates
        sampled_entries = random.sample(entries, min(num_submissions, len(entries)))
        
        for entry in sampled_entries:
            submission = create_share_story_entry(
                company=entry["company"],
                theme=entry["theme"], 
                comment=entry["comment"]
            )
            submissions.append(submission)
    
    return submissions

def main():
    ap = argparse.ArgumentParser(description="Build Share Story submissions from CSV")
    ap.add_argument("--min-per-firm", type=int, default=2, help="Minimum submissions per firm")
    ap.add_argument("--max-per-firm", type=int, default=4, help="Maximum submissions per firm")
    ap.add_argument("--out", default="submissions.json", help="Output file")
    args = ap.parse_args()

    # Generate submissions
    submissions = build_share_story_submissions(args.min_per_firm, args.max_per_firm)
    
    # Write to file
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(submissions, f, ensure_ascii=False, indent=2)
    
    print(f"Generated {len(submissions)} Share Story submissions")
    
    # Print summary by company
    by_company = {}
    for sub in submissions:
        company = sub["company"]
        by_company[company] = by_company.get(company, 0) + 1
    
    print(f"Distribution across {len(by_company)} companies:")
    for company, count in sorted(by_company.items()):
        print(f"  {company}: {count} submissions")

if __name__ == "__main__":
    main()
