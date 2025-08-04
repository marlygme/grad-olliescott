
import csv
import json
from datetime import datetime
import os

def import_csv_to_json():
    csv_file_path = '/mnt/data/Auslaw_Comments_with_Themes_and_Firms_1754309543165.csv'
    json_file_path = 'submissions.json'
    
    # Check if CSV file exists
    if not os.path.exists(csv_file_path):
        print(f"Error: CSV file not found at {csv_file_path}")
        return
    
    # Load existing JSON data
    existing_data = []
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    
    print(f"Existing entries in JSON: {len(existing_data)}")
    
    # Read CSV and convert to JSON format
    new_entries = []
    skipped_count = 0
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            # Skip rows missing company or role
            company = row.get('Business', '').strip()
            role = "Graduate Lawyer"  # Default role since not in CSV
            
            if not company:
                skipped_count += 1
                continue
            
            # Extract relevant information from comment
            comment = row.get('Comment', '').strip()
            theme = row.get('Theme', '').strip()
            
            # Build entry matching our JSON schema
            entry = {
                "company": company,
                "role": role,
                "salary": "",  # Not available in CSV
                "bonus": "",   # Not available in CSV
                "university": "",  # Not available in CSV
                "wam": "",     # Not available in CSV
                "application_stages": "",  # Not available in CSV
                "interview_experience": comment if theme in ['Interviews', 'Applications'] else "",
                "outcome": "Unknown",  # Not clearly available in CSV
                "advice": comment if theme in ['Other', 'Practice Areas', 'Firm Culture'] else "",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            new_entries.append(entry)
    
    # Combine existing and new data
    all_data = existing_data + new_entries
    
    # Write back to JSON file
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"Imported {len(new_entries)} entries, now total {len(all_data)}.")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} rows due to missing company information.")

if __name__ == "__main__":
    import_csv_to_json()
