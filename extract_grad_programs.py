
import pandas as pd
import os
import sys
import argparse
from datetime import datetime
from extractors import FirmMatcher, DateParser, ProgramClassifier, ConfidenceCalculator, EvidenceExtractor

def main():
    parser = argparse.ArgumentParser(description='Extract graduate program signals from forum posts')
    parser.add_argument('--in', dest='input_files', nargs='*', 
                       default=['attached_assets/law_raw_1755229749802.csv',
                               'attached_assets/raw_all_1755229749804.csv', 
                               'attached_assets/law_whirlpool_2018_2025_1755229749803.csv'],
                       help='Input CSV files')
    parser.add_argument('--out', default='out/grad_program_signals.csv', help='Output CSV file')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs('out', exist_ok=True)
    
    # Initialize extractors
    firm_matcher = FirmMatcher()
    date_parser = DateParser()
    program_classifier = ProgramClassifier()
    confidence_calc = ConfidenceCalculator()
    evidence_extractor = EvidenceExtractor()
    
    all_signals = []
    
    for file_path in args.input_files:
        if not os.path.exists(file_path):
            print(f"Warning: File {file_path} not found, skipping...")
            continue
            
        print(f"Processing {file_path}...")
        
        try:
            df = pd.read_csv(file_path)
            source_file = os.path.basename(file_path)
            
            for _, row in df.iterrows():
                content = str(row.get('content', ''))
                if not content or content == 'nan':
                    continue
                
                # Normalize content for processing
                normalized_content = content.lower().strip()
                
                # Find firm matches
                firm_matches = firm_matcher.find_firms(normalized_content)
                
                for firm_name, firm_alias, match_start, match_end in firm_matches:
                    # Extract context around the firm mention
                    context_start = max(0, match_start - 100)
                    context_end = min(len(content), match_end + 100)
                    context = content[context_start:context_end]
                    
                    # Classify program type
                    program_type = program_classifier.classify(context)
                    
                    # Skip if no program signals found
                    if program_type == 'no_program':
                        continue
                    
                    # Extract other fields
                    city = extract_city(context, row.get('thread_title', ''))
                    intake_year = extract_intake_year(context, row.get('thread_title', ''), row.get('timestamp'))
                    
                    open_date, close_date = date_parser.extract_application_dates(context)
                    program_length = extract_program_length(context)
                    rotations = extract_rotations(context)
                    salary = extract_salary(context)
                    
                    # Generate evidence span
                    evidence_span = evidence_extractor.extract_evidence(context, firm_alias, program_type)
                    
                    # Parse timestamp
                    parsed_timestamp = date_parser.parse_timestamp(row.get('timestamp', ''))
                    
                    # Calculate confidence
                    confidence = confidence_calc.calculate(
                        firm_alias, firm_name, program_type, city, intake_year,
                        open_date, close_date, len(firm_matches)
                    )
                    
                    signal = {
                        'firm_name': firm_name,
                        'firm_alias': firm_alias,
                        'program_type': program_type,
                        'city': city,
                        'intake_year': intake_year,
                        'application_open_date': open_date,
                        'application_close_date': close_date,
                        'program_length_months': program_length,
                        'rotations_count': rotations,
                        'salary_annual_aud': salary,
                        'evidence_span': evidence_span,
                        'thread_title': row.get('thread_title', ''),
                        'thread_url': row.get('thread_url', ''),
                        'post_number': row.get('post_number', ''),
                        'post_timestamp': parsed_timestamp,
                        'source_file': source_file,
                        'confidence': confidence,
                        'created_at': datetime.utcnow().isoformat()
                    }
                    
                    all_signals.append(signal)
                    
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    # Create DataFrame and save
    if all_signals:
        signals_df = pd.DataFrame(all_signals)
        
        # Save as CSV
        signals_df.to_csv(args.out, index=False)
        
        # Save as Parquet
        parquet_path = args.out.replace('.csv', '.parquet')
        signals_df.to_parquet(parquet_path, index=False)
        
        print(f"\nExtracted {len(all_signals)} program signals")
        print(f"Saved to {args.out} and {parquet_path}")
        
        # Quality checks
        print_quality_checks(signals_df)
        
    else:
        print("No program signals found in any of the input files")

def extract_city(context, thread_title):
    """Extract city from context or thread title"""
    cities = {
        'sydney': ['sydney', 'syd'],
        'melbourne': ['melbourne', 'melb'],
        'brisbane': ['brisbane', 'bris'],
        'perth': ['perth'],
        'adelaide': ['adelaide'],
        'canberra': ['canberra'],
        'hobart': ['hobart']
    }
    
    combined_text = (context + ' ' + thread_title).lower()
    
    for city, aliases in cities.items():
        for alias in aliases:
            if alias in combined_text:
                return city.title()
    
    return 'Other/Unknown'

def extract_intake_year(context, thread_title, timestamp):
    """Extract intake year from context or thread title"""
    import re
    
    combined_text = context + ' ' + thread_title
    
    # Look for year patterns
    year_pattern = r'\b(20\d{2})\b'
    years = re.findall(year_pattern, combined_text)
    
    if years:
        return int(years[0])
    
    # Fallback to timestamp year with low confidence
    if timestamp:
        try:
            return int(timestamp[:4])
        except:
            pass
    
    return None

def extract_program_length(context):
    """Extract program length in months"""
    import re
    
    # Look for patterns like "18-month", "2 year", etc.
    month_pattern = r'(\d+)[-\s]?(month|months)'
    year_pattern = r'(\d+)[-\s]?(year|years|yr)'
    
    months = re.search(month_pattern, context.lower())
    if months:
        return int(months.group(1))
    
    years = re.search(year_pattern, context.lower())
    if years:
        return int(years.group(1)) * 12
    
    return None

def extract_rotations(context):
    """Extract number of rotations"""
    import re
    
    rotation_pattern = r'(\d+)\s+rotations?'
    match = re.search(rotation_pattern, context.lower())
    
    if match:
        return int(match.group(1))
    
    return None

def extract_salary(context):
    """Extract annual salary in AUD"""
    import re
    
    # Look for salary patterns like $65k, $70,000, etc.
    salary_patterns = [
        r'\$(\d+)k(?:\+super)?',
        r'\$(\d{1,3}),?(\d{3})(?:\+super)?',
        r'\$(\d+)(?:\+super)?'
    ]
    
    for pattern in salary_patterns:
        matches = re.findall(pattern, context.lower())
        for match in matches:
            if isinstance(match, tuple):
                if len(match) == 2 and match[1]:  # Format like $70,000
                    return int(match[0] + match[1])
                else:
                    return int(match[0])
            else:
                if 'k' in pattern:  # Format like $65k
                    return int(match) * 1000
                else:
                    salary = int(match)
                    if salary > 1000:  # Likely already in full amount
                        return salary
    
    return None

def print_quality_checks(df):
    """Print quality check statistics"""
    print("\n=== Quality Checks ===")
    
    # Top 20 firms by mention count
    print("\nTop 20 firms by mention count:")
    firm_counts = df.groupby(['firm_name', 'program_type']).size().reset_index(name='count')
    firm_totals = firm_counts.groupby('firm_name')['count'].sum().sort_values(ascending=False).head(20)
    
    for firm, count in firm_totals.items():
        breakdown = firm_counts[firm_counts['firm_name'] == firm]
        types = ', '.join([f"{row['program_type']}: {row['count']}" for _, row in breakdown.iterrows()])
        print(f"  {firm}: {count} ({types})")
    
    # Sample high-confidence rows
    print(f"\nSample 10 rows with confidence >= 0.75:")
    high_conf = df[df['confidence'] >= 0.75].head(10)
    for _, row in high_conf.iterrows():
        print(f"  {row['firm_name']} - {row['program_type']} - {row['city']} (conf: {row['confidence']:.2f})")
    
    # City breakdown
    print(f"\nProgram counts by city:")
    city_breakdown = df.groupby(['city', 'program_type']).size().reset_index(name='count')
    for city in df['city'].unique():
        city_data = city_breakdown[city_breakdown['city'] == city]
        if len(city_data) > 0:
            types = ', '.join([f"{row['program_type']}: {row['count']}" for _, row in city_data.iterrows()])
            total = city_data['count'].sum()
            print(f"  {city}: {total} ({types})")

if __name__ == "__main__":
    main()
