
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

def generate_realistic_stages(comment: str) -> str:
    """Generate application stages based on comment content."""
    stages = []
    comment_lower = comment.lower()
    
    if any(word in comment_lower for word in ["application", "apply", "cv", "resume", "cover letter"]):
        stages.append("Online application with CV and cover letter")
    
    if any(word in comment_lower for word in ["online", "test", "assessment", "oa"]):
        stages.append("Online assessment or testing")
        
    if any(word in comment_lower for word in ["video", "interview", "phone", "call"]):
        stages.append("Video or phone interview")
        
    if any(word in comment_lower for word in ["assessment centre", "ac", "group", "presentation"]):
        stages.append("Assessment centre with group exercises")
        
    if any(word in comment_lower for word in ["partner", "final", "panel"]):
        stages.append("Final partner interview")
    
    if not stages:
        stages = ["Application submitted", "Initial screening", "Interview process"]
    
    return " → ".join(stages)

def generate_interview_experience(comment: str, theme: str) -> str:
    """Generate interview experience based on comment and theme."""
    if "interview" in comment.lower():
        # Extract relevant parts about interviews
        sentences = [s.strip() for s in re.split(r'[.!?]', comment) if 'interview' in s.lower()]
        if sentences:
            return sentences[0][:200] + ("..." if len(sentences[0]) > 200 else "")
    
    # Theme-based fallbacks
    if theme == "Interviews":
        return "Standard competency-based interview focusing on motivation and commercial awareness. Behavioral questions about teamwork and problem-solving."
    elif theme == "Applications":
        return "Application reviewed, followed by structured interview process with HR and senior lawyers."
    else:
        return "Professional interview process with questions about interest in the firm and legal career goals."

def generate_advice(comment: str, theme: str) -> str:
    """Generate advice based on comment content and theme."""
    advice_parts = []
    comment_lower = comment.lower()
    
    if theme == "Applications":
        advice_parts.append("Start applications early and tailor each one to the specific firm.")
    elif theme == "Interviews":
        advice_parts.append("Practice common interview questions and research the firm's recent deals.")
    elif theme == "Firm Culture":
        advice_parts.append("Ask about the culture during interviews and speak to current employees if possible.")
    elif theme == "Salaries":
        advice_parts.append("Research market rates and don't be afraid to negotiate respectfully.")
    
    # Extract advice-like content from comment
    advice_indicators = ["advice", "tip", "recommend", "suggest", "should", "important", "make sure"]
    sentences = [s.strip() for s in re.split(r'[.!?]', comment)]
    
    for sentence in sentences:
        if any(indicator in sentence.lower() for indicator in advice_indicators):
            advice_parts.append(sentence[:150])
            break
    
    if not advice_parts:
        advice_parts.append("Do your research on the firm and be genuine about your interest in their work.")
    
    return " ".join(advice_parts)[:400]

def create_share_story_entry(company: str, theme: str, comment: str) -> Dict:
    """Create a realistic Share Story submission entry."""
    experience_type = THEME_TO_TYPE.get(theme, "Graduate Program")
    
    # Generate realistic content
    application_stages = generate_realistic_stages(comment)
    interview_experience = generate_interview_experience(comment, theme)
    advice = generate_advice(comment, theme)
    
    # Random but realistic timestamp (last 2 years)
    base_date = datetime.now() - timedelta(days=random.randint(30, 730))
    
    return {
        "company": company,
        "role": random.choice(["Graduate Lawyer", "Summer Clerk", "Paralegal", "Legal Intern"]),
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
