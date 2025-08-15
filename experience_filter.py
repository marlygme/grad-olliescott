
import csv
import re
import argparse
from typing import List, Dict, Optional
from extractors import FIRM_ALIASES

def clean_content(content: str) -> str:
    """Clean content for analysis"""
    if not content:
        return ""
    # Remove extra whitespace, newlines
    cleaned = re.sub(r'\s+', ' ', content.strip())
    return cleaned

def is_question(content: str) -> bool:
    """Check if content looks like a question"""
    if not content:
        return False
    
    content_lower = content.lower().strip()
    
    # Ends with ?
    if content_lower.endswith('?'):
        return True
    
    # Question starters
    question_starters = [
        'anyone know', 'does anyone', 'has anyone', 'is it true', 'should i',
        'where can i', 'what are', 'when do', 'how long', 'how do'
    ]
    
    for starter in question_starters:
        if content_lower.startswith(starter):
            return True
    
    # Multiple question marks
    if content.count('?') >= 2:
        return True
    
    return False

def is_meta_low(content: str) -> bool:
    """Check if content is meta/filler"""
    if not content:
        return True
    
    content_lower = content.lower().strip()
    
    meta_phrases = [
        'bump', 'following', 'subscribing', 'any updates', 'thanks', 'lol',
        'lmao', 'haha', 'dm me', 'pm me', 'off-topic'
    ]
    
    for phrase in meta_phrases:
        if phrase in content_lower:
            return True
    
    # Very short generic responses
    if len(content_lower) < 20 and any(word in content_lower for word in ['yes', 'no', 'ok', 'thanks', 'same']):
        return True
    
    return False

def is_too_short(content: str) -> bool:
    """Check if content is too short"""
    if not content:
        return True
    
    cleaned = clean_content(content)
    
    # Length check
    if len(cleaned) < 180:
        return True
    
    # Unique words check
    words = set(word.lower() for word in re.findall(r'\b\w+\b', cleaned))
    if len(words) < 25:
        return True
    
    return False

def has_program_signals(content: str) -> bool:
    """Check if content contains useful program signals"""
    if not content:
        return False
    
    content_lower = content.lower()
    
    signals = [
        'offer', 'rejected', 'accepted', 'clerkship', 'graduate program',
        'rotation', 'ac', 'assessment centre', 'superday', 'paralegal',
        'salary', 'pay', 'remuneration', 'benefits', 'billable', 'hours',
        'culture', 'mentor', 'secondment', 'seat', 'practice group', 'training'
    ]
    
    return any(signal in content_lower for signal in signals)

def has_numbers(content: str) -> bool:
    """Check if content contains dates, money, or other numbers"""
    if not content:
        return False
    
    # Check for $ symbol
    if '$' in content:
        return True
    
    # Check for dates (basic patterns)
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # dd/mm/yyyy
        r'\b\d{4}\b',  # year
        r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b'  # months
    ]
    
    for pattern in date_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    
    # Check for other significant numbers
    if re.search(r'\b\d+\b', content):
        return True
    
    return False

def past_tense_hint(content: str) -> bool:
    """Check for past tense verbs indicating experience"""
    if not content:
        return False
    
    content_lower = content.lower()
    
    past_verbs = [
        'received', 'accepted', 'completed', 'did', 'worked', 'went',
        'rotated', 'attended', 'participated', 'finished', 'started'
    ]
    
    return any(verb in content_lower for verb in past_verbs)

def compute_quality_score(content: str) -> float:
    """Compute quality score from 0 to 1"""
    score = 0.5
    
    # Positive signals
    if has_program_signals(content):
        score += 0.25
    if has_numbers(content):
        score += 0.1
    if past_tense_hint(content):
        score += 0.1
    if not is_too_short(content):
        score += 0.1
    
    # Negative signals
    if is_question(content):
        score -= 0.5
    if is_meta_low(content):
        score -= 0.2
    if is_too_short(content):
        score -= 0.2
    
    # Clamp to 0-1
    return max(0.0, min(1.0, score))

def match_firm(content: str, thread_title: str = "") -> Optional[str]:
    """Match content to a firm using FIRM_ALIASES"""
    text_to_search = f"{content} {thread_title}".lower()
    
    for canonical, aliases in FIRM_ALIASES.items():
        # Check canonical name
        if re.search(rf'\b{re.escape(canonical.lower())}\b', text_to_search):
            return canonical
        
        # Check aliases
        for alias in aliases:
            if re.search(rf'\b{re.escape(alias.lower())}\b', text_to_search):
                return canonical
    
    return None

def process_csv_files(input_files: List[str], target_firm: Optional[str] = None) -> List[Dict]:
    """Process CSV files and extract firm-related posts"""
    results = []
    
    for file_path in input_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    content = row.get('content', '')
                    thread_title = row.get('thread_title', '')
                    
                    if not content:
                        continue
                    
                    # Match to firm
                    firm = match_firm(content, thread_title)
                    if not firm:
                        continue
                    
                    # If target firm specified, filter to only that firm
                    if target_firm and firm.lower() != target_firm.lower():
                        continue
                    
                    # Compute quality metrics
                    is_q = is_question(content)
                    is_meta = is_meta_low(content)
                    is_short = is_too_short(content)
                    quality = compute_quality_score(content)
                    
                    # Remove any username/author fields for privacy
                    for field in ['author', 'username', 'user', 'Author', 'User', 'USERNAME']:
                        if field in row:
                            del row[field]
                    
                    # Determine reason for inclusion/exclusion
                    reasons = []
                    if quality >= 0.6:
                        reasons.append("high_quality")
                    if is_q:
                        reasons.append("question")
                    if is_meta:
                        reasons.append("meta")
                    if is_short:
                        reasons.append("too_short")
                    
                    results.append({
                        'firm_name': firm,
                        'content': content,
                        'timestamp': row.get('timestamp', ''),
                        'thread_url': row.get('thread_url', ''),
                        'quality_score': round(quality, 3),
                        'is_question': is_q,
                        'is_meta_low': is_meta,
                        'is_too_short': is_short,
                        'reason': ','.join(reasons) if reasons else 'included'
                    })
        
        except FileNotFoundError:
            print(f"Warning: File {file_path} not found, skipping...")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    return results

def load_filtered_for_firm(firm_name: str, min_score: float = 0.6, exclude_questions: bool = True) -> List[Dict]:
    """Load filtered experiences for a specific firm"""
    # Try to load from cached file first
    slug = firm_name.lower().replace('&', '').replace('+', '').replace(' ', '-').strip('-')
    cache_file = f"out/experiences_{slug}.csv"
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            results = []
            for row in reader:
                quality = float(row.get('quality_score', 0))
                is_q = row.get('is_question', 'False').lower() == 'true'
                
                if quality >= min_score and (not exclude_questions or not is_q):
                    results.append(row)
            return results
    except FileNotFoundError:
        pass
    
    # Fall back to processing raw files
    input_files = ['law_raw.csv', 'law_whirlpool_2018_2025.csv', 'raw_all.csv']
    all_results = process_csv_files(input_files, firm_name)
    
    # Filter results
    filtered = []
    for result in all_results:
        if result['quality_score'] >= min_score:
            if not exclude_questions or not result['is_question']:
                filtered.append(result)
    
    return filtered

def main():
    parser = argparse.ArgumentParser(description='Filter high-quality firm experiences')
    parser.add_argument('--in', dest='input_files', nargs='+', required=True,
                       help='Input CSV files')
    parser.add_argument('--firm', help='Target firm name')
    parser.add_argument('--out', help='Output CSV file')
    parser.add_argument('--minscore', type=float, default=0.6,
                       help='Minimum quality score (default: 0.6)')
    parser.add_argument('--exclude-questions', type=int, default=1,
                       help='Exclude questions (1=yes, 0=no)')
    
    args = parser.parse_args()
    
    # Process files
    results = process_csv_files(args.input_files, args.firm)
    
    # Filter results
    exclude_q = bool(args.exclude_questions)
    filtered = []
    for result in results:
        if result['quality_score'] >= args.minscore:
            if not exclude_q or not result['is_question']:
                filtered.append(result)
    
    # Print summary
    total = len(results)
    kept = len(filtered)
    print(f"Kept {kept} / {total} for {args.firm or 'all firms'}")
    
    # Count reasons
    reason_counts = {}
    for result in results:
        for reason in result['reason'].split(','):
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    
    top_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"Top reasons: {', '.join([f'{r}({c})' for r, c in top_reasons])}")
    
    # Write output
    if args.out and filtered:
        with open(args.out, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['firm_name', 'content', 'timestamp', 'thread_url',
                         'quality_score', 'is_question', 'is_meta_low', 'is_too_short', 'reason']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(filtered)
        print(f"Written to {args.out}")

if __name__ == '__main__':
    main()
