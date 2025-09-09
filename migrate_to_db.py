import json
import os
import psycopg2
from datetime import datetime

def migrate_applications_to_db():
    """Migrate applications from JSON file to database"""
    
    # Read existing applications
    if not os.path.exists('applications.json'):
        print("No applications.json found, skipping migration")
        return
    
    with open('applications.json', 'r') as f:
        applications = json.load(f)
    
    if not applications:
        print("No applications to migrate")
        return
    
    # Connect to database
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not found")
        return
    
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    # For each application, we need to create a user first (using Replit user ID)
    migrated_count = 0
    
    for app in applications:
        try:
            user_id = app.get('user_id')
            if not user_id:
                print(f"Skipping application {app.get('id')} - no user_id")
                continue
            
            # Insert/update user first
            user_name = app.get('user_name', 'Unknown User')
            cur.execute("""
                INSERT INTO users (id, email, first_name, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
            """, (user_id, f"{user_name}@replit.local", user_name))
            
            # Insert application
            cur.execute("""
                INSERT INTO applications (
                    user_id, company, role, application_date, university, wam, 
                    status, response_date, priority, notes, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                app.get('company'),
                app.get('role'),
                app.get('application_date') if app.get('application_date') else None,
                app.get('university'),
                app.get('wam'),
                app.get('status', 'Applied'),
                app.get('response_date') if app.get('response_date') else None,
                app.get('priority', 'Medium'),
                app.get('notes', ''),
                app.get('timestamp', datetime.utcnow().isoformat()),
                app.get('updated', datetime.utcnow().isoformat())
            ))
            
            migrated_count += 1
            
        except Exception as e:
            print(f"Error migrating application {app.get('id')}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"Successfully migrated {migrated_count} applications to database")
    
    # Backup original file
    if migrated_count > 0:
        os.rename('applications.json', 'applications.json.backup')
        print("Original applications.json backed up to applications.json.backup")

def migrate_submissions_to_db():
    """Migrate submissions from JSON file to database"""
    
    # Read existing submissions
    if not os.path.exists('submissions.json'):
        print("No submissions.json found, skipping migration")
        return
    
    with open('submissions.json', 'r') as f:
        submissions = json.load(f)
    
    if not submissions:
        print("No submissions to migrate")
        return
    
    # Connect to database
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not found")
        return
    
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    migrated_count = 0
    
    for sub in submissions:
        try:
            user_id = sub.get('user_id')
            if not user_id:
                # For submissions without user_id, assign to a default user
                user_id = 'anonymous'
            
            # Insert/update user first
            user_name = sub.get('user_name', 'Anonymous User')
            cur.execute("""
                INSERT INTO users (id, email, first_name, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
            """, (user_id, f"{user_name}@replit.local", user_name))
            
            # Insert submission
            cur.execute("""
                INSERT INTO submissions (
                    user_id, company, role, experience_type, theme, 
                    application_stages, interview_experience, assessment_centre,
                    program_structure, salary_benefits, culture_environment,
                    hours_workload, practice_areas, general_experience,
                    pro_tip, advice, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                sub.get('company'),
                sub.get('role'),
                sub.get('experience_type'),
                sub.get('theme'),
                sub.get('application_stages'),
                sub.get('interview_experience'),
                sub.get('assessment_centre'),
                sub.get('program_structure'),
                sub.get('salary_benefits'),
                sub.get('culture_environment'),
                sub.get('hours_workload'),
                sub.get('practice_areas'),
                sub.get('general_experience'),
                sub.get('pro_tip'),
                sub.get('advice'),
                sub.get('timestamp', datetime.utcnow().isoformat())
            ))
            
            migrated_count += 1
            
        except Exception as e:
            print(f"Error migrating submission: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"Successfully migrated {migrated_count} submissions to database")
    
    # Backup original file
    if migrated_count > 0:
        os.rename('submissions.json', 'submissions.json.backup')
        print("Original submissions.json backed up to submissions.json.backup")

if __name__ == "__main__":
    print("Starting migration to database...")
    migrate_applications_to_db()
    migrate_submissions_to_db()
    print("Migration completed!")