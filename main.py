from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session, flash
from datetime import datetime, date
import json
import os
import re
import csv
from collections import defaultdict, Counter
from grad_data import load_cards, load_grad_signals
from grad_data_v2 import load_cards as load_cards_v2
from legal_config import LEGAL_CONFIG, NOT_ADVICE_DISCLAIMER
from auth import create_user, authenticate_user, login_required, get_current_user


# Load data from JSON file
data_file = 'submissions.json'

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this to a secure random key

data_file = 'submissions.json'
tracker_file = 'applications.json'

# University distribution data for law firms
FIRM_UNIVERSITY_DATA = {
    'Allens': {
        'University of Melbourne': 25, 'Monash University': 10, 'University of Sydney': 20,
        'UNSW': 15, 'University of Queensland': 10, 'Australian National University': 10,
        'Macquarie University': 5, 'University of Adelaide': 2, 'Other': 3
    },
    'Clayton Utz': {
        'University of Melbourne': 20, 'Monash University': 15, 'University of Sydney': 20,
        'UNSW': 15, 'University of Queensland': 10, 'Australian National University': 10,
        'Macquarie University': 5, 'University of Adelaide': 3, 'Other': 2
    },
    'Herbert Smith Freehills': {
        'University of Melbourne': 25, 'Monash University': 10, 'University of Sydney': 20,
        'UNSW': 15, 'University of Queensland': 10, 'Australian National University': 10,
        'Macquarie University': 5, 'University of Adelaide': 2, 'Other': 3
    },
    'Ashurst': {
        'University of Melbourne': 20, 'Monash University': 15, 'University of Sydney': 20,
        'UNSW': 15, 'University of Queensland': 10, 'Australian National University': 10,
        'Macquarie University': 5, 'University of Adelaide': 2, 'Other': 3
    },
    'MinterEllison': {
        'University of Melbourne': 15, 'Monash University': 20, 'University of Sydney': 15,
        'UNSW': 15, 'University of Queensland': 10, 'Australian National University': 10,
        'Macquarie University': 10, 'University of Adelaide': 2, 'Other': 3
    },
    'King & Wood Mallesons': {
        'University of Melbourne': 25, 'Monash University': 10, 'University of Sydney': 25,
        'UNSW': 15, 'University of Queensland': 10, 'Australian National University': 10,
        'Macquarie University': 2, 'University of Adelaide': 1, 'Other': 2
    },
    'Corrs Chambers Westgarth': {
        'University of Melbourne': 20, 'Monash University': 15, 'University of Sydney': 20,
        'UNSW': 15, 'University of Queensland': 10, 'Australian National University': 10,
        'Macquarie University': 5, 'University of Adelaide': 2, 'Other': 3
    },
    'Gilbert + Tobin': {
        'University of Melbourne': 10, 'Monash University': 5, 'University of Sydney': 30,
        'UNSW': 30, 'University of Queensland': 5, 'Australian National University': 10,
        'Macquarie University': 5, 'University of Adelaide': 1, 'Other': 4
    },
    'Lander & Rogers': {
        'University of Melbourne': 35, 'Monash University': 25, 'University of Sydney': 5,
        'UNSW': 5, 'University of Queensland': 5, 'Australian National University': 10,
        'Macquarie University': 5, 'University of Adelaide': 5, 'Other': 5
    },
    'Colin Biggers & Paisley': {
        'University of Melbourne': 20, 'Monash University': 20, 'University of Sydney': 10,
        'UNSW': 10, 'University of Queensland': 10, 'Australian National University': 10,
        'Macquarie University': 10, 'University of Adelaide': 5, 'Other': 5
    }
}

# Load existing data or create empty
if not os.path.exists(data_file):
    with open(data_file, 'w') as f:
        json.dump([], f)

if not os.path.exists(tracker_file):
    with open(tracker_file, 'w') as f:
        json.dump([], f)


@app.route('/')
def index():
    # Get user info from session
    current_user = get_current_user()
    user_id = current_user['user_id'] if current_user else None
    user_name = current_user['username'] if current_user else None

    with open(data_file, 'r') as f:
        submissions = json.load(f)

    # Group submissions by company for homepage
    companies = {}
    for submission in submissions:
        company = submission['company']
        if company not in companies:
            companies[company] = {
                'name': company,
                'total_submissions': 0,
                'success_count': 0,
                'avg_salary': 0,
                'salary_count': 0,
                'recent_roles': set()
            }

        companies[company]['total_submissions'] += 1
        if submission.get('outcome') == 'Success':
            companies[company]['success_count'] += 1

        salary = submission.get('salary', '')
        if salary and str(salary).isdigit():
            companies[company]['avg_salary'] += int(salary)
            companies[company]['salary_count'] += 1

        companies[company]['recent_roles'].add(submission['role'])

    # Calculate averages and format data
    for company_data in companies.values():
        if company_data['salary_count'] > 0:
            company_data['avg_salary'] = int(company_data['avg_salary'] / company_data['salary_count'])
        else:
            company_data['avg_salary'] = None

        company_data['success_rate'] = round((company_data['success_count'] / company_data['total_submissions']) * 100, 1)
        company_data['recent_roles'] = list(company_data['recent_roles'])[:3]  # Show top 3 roles

    # Sort by number of submissions
    sorted_companies = sorted(companies.values(), key=lambda x: x['total_submissions'], reverse=True)

    # Load firms from CSV for Explore Companies section
    firms = load_cards("out/grad_program_signals.csv")
    print(f"Loaded {len(firms)} firms from CSV")

    # Create a lookup dictionary for companies data
    companies_lookup = {company['name']: company for company in sorted_companies}

    return render_template('index.html', companies=companies_lookup, sorted_companies=sorted_companies, total_submissions=len(submissions), firms=firms, user_id=user_id, user_name=user_name)


@app.route('/auth_required')
def auth_required():
    return render_template('auth_required.html')

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    # Check if user is authenticated
    current_user = get_current_user()
    if not current_user:
        return render_template('auth_required.html')

    user_id = current_user['user_id']
    user_name = current_user['username']

    if request.method == 'POST':
        new_entry = {
            'company': request.form['company'],
            'role': request.form['role'],
            'experience_type': request.form['experience_type'],
            'theme': request.form['theme'],
            'application_stages': request.form.get('application_stages', ''),
            'interview_experience': request.form.get('interview_experience', ''),
            'assessment_centre': request.form.get('assessment_centre', ''),
            'program_structure': request.form.get('program_structure', ''),
            'salary_benefits': request.form.get('salary_benefits', ''),
            'culture_environment': request.form.get('culture_environment', ''),
            'hours_workload': request.form.get('hours_workload', ''),
            'practice_areas': request.form.get('practice_areas', ''),
            'general_experience': request.form.get('general_experience', ''),
            'pro_tip': request.form.get('pro_tip', ''),
            'advice': request.form.get('advice', ''),
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'user_name': user_name
        }
        with open(data_file, 'r') as f:
            data = json.load(f)
        data.append(new_entry)
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        return redirect(url_for('index'))

    return render_template("submit.html", user_id=user_id, user_name=user_name)



@app.route('/company/<name>')
def company_page(name):
    from categorizer import classify_text, label

    with open(data_file, 'r') as f:
        data = json.load(f)
    company_entries = [entry for entry in data if entry['company'].lower() == name.lower()]

    # Load firm data from CSV
    firms = load_cards_v2("out/grad_program_signals.csv")
    firm_data = None
    for firm in firms:
        if firm['name'].lower() == name.lower():
            firm_data = firm

            # Load experiences for this firm
            experiences = load_grad_signals("out/grad_program_signals.csv")
            firm_experiences = [exp for exp in experiences if exp['firm_name'].lower() == name.lower()]

            # Categorize experiences and add to firm data
            for exp in firm_experiences[:10]:  # Show top 10
                content = exp.get("evidence_span", "")
                if content:
                    p, cats, details = classify_text(content, threshold=1.0, top_k=3)
                    exp["primary_cat"] = p
                    exp["cat_labels"] = [label(c) for c in cats]

                # Clean any remaining usernames or identifiers
                for field in ['evidence_span', 'content']:
                    if exp.get(field):
                        # Remove any @mentions or user references
                        exp[field] = re.sub(r'@\w+', '', exp[field])
                        exp[field] = re.sub(r'User #\d+', '', exp[field])
                        exp[field] = re.sub(r'\busername:\s*\w+', '', exp[field], flags=re.IGNORECASE)
                        # Clean up multiple spaces
                        exp[field] = ' '.join(exp[field].split())

            firm_data['experiences'] = firm_experiences[:5]
            firm_data['total_experiences'] = len(firm_experiences)
            break

    # Calculate company stats
    if company_entries:
        success_count = len([e for e in company_entries if e.get('outcome') == 'Success'])
        success_rate = round((success_count / len(company_entries)) * 100, 1)

        salaries = [int(e.get('salary', 0)) for e in company_entries if e.get('salary') and str(e.get('salary')).isdigit()]
        avg_salary = int(sum(salaries) / len(salaries)) if salaries else None

        roles = list(set([e['role'] for e in company_entries]))

        # Add university breakdown if available
        university_breakdown = None
        if name in FIRM_UNIVERSITY_DATA:
            university_breakdown = FIRM_UNIVERSITY_DATA[name]

        # Calculate salary ranges
        salary_ranges = {
            'entry_level': len([s for s in salaries if s < 80000]),
            'mid_level': len([s for s in salaries if 80000 <= s < 120000]),
            'senior_level': len([s for s in salaries if s >= 120000])
        }

        # Most common advice themes
        advice_keywords = {}
        for entry in company_entries:
            if entry.get('advice'):
                words = entry['advice'].lower().split()
                for word in words:
                    if len(word) > 4:  # Only count meaningful words
                        advice_keywords[word] = advice_keywords.get(word, 0) + 1

        top_advice = sorted(advice_keywords.items(), key=lambda x: x[1], reverse=True)[:5]

        company_stats = {
            'success_rate': success_rate,
            'avg_salary': avg_salary,
            'salary_ranges': salary_ranges,
            'roles': roles,
            'total_entries': len(company_entries),
            'university_breakdown': university_breakdown,
            'top_advice_keywords': top_advice
        }
    else:
        company_stats = None

    return render_template('company.html', company=name, entries=company_entries, stats=company_stats, firm_data=firm_data)


@app.route('/companies')
def companies():
    with open(data_file, 'r') as f:
        submissions = json.load(f)

    # Group submissions by company
    companies = {}
    for submission in submissions:
        company = submission['company']
        if company not in companies:
            company_data = {
            'name': company,
            'total_submissions': 0,
            'success_count': 0,
            'experiences': [],
            'recent_roles': set(),
            'avg_salary': 0,
            'salary_count': 0
            }
            companies[company] = company_data

        companies[company]['total_submissions'] += 1
        if submission.get('outcome') == 'Success':
            companies[company]['success_count'] += 1

        salary = submission.get('salary', '')
        if salary and str(salary).isdigit():
            companies[company]['avg_salary'] += int(salary)
            companies[company]['salary_count'] += 1

        companies[company]['recent_roles'].add(submission['role'])
        companies[company]['experiences'].append(submission)

    # Calculate averages and format data
    for company_data in companies.values():
        if company_data['salary_count'] > 0:
            company_data['avg_salary'] = int(company_data['avg_salary'] / company_data['salary_count'])
        else:
            company_data['avg_salary'] = None

        company_data['success_rate'] = round((company_data['success_count'] / company_data['total_submissions']) * 100, 1)
        company_data['recent_roles'] = list(company_data['recent_roles'])[:3]  # Show top 3 roles

        # Keep only recent experiences for display
        company_data['experiences'] = company_data['experiences'][:5]

    # Convert to list and sort by number of submissions
    firms = sorted(companies.values(), key=lambda x: x['total_submissions'], reverse=True)

    return render_template("companies.html", firms=firms)


@app.route('/api/grad-data')
def api_grad_data():
    return jsonify({"firms": load_cards("out/grad_program_signals.csv")})


@app.route('/api/company-analytics/<company_name>')
def api_company_analytics(company_name):
    """Get analytics data for a specific company"""

    with open(tracker_file, 'r') as f:
        all_applications = json.load(f)

    # Filter applications for this company
    company_apps = [app for app in all_applications if app.get('company', '').lower() == company_name.lower()]

    if not company_apps:
        return jsonify({'error': 'No data available'})

    # Calculate company stats
    total_apps = len(company_apps)
    responses = [app for app in company_apps if app.get('response_date')]
    offers = [app for app in company_apps if app.get('status') == 'Offered']

    response_times = []
    for app in responses:
        if app.get('application_date') and app.get('response_date'):
            try:
                app_date = datetime.strptime(app['application_date'], '%Y-%m-%d').date()
                resp_date = datetime.strptime(app['response_date'], '%Y-%m-%d').date()
                response_times.append((resp_date - app_date).days)
            except:
                pass

    avg_response_time = round(sum(response_times) / len(response_times)) if response_times else 0

    company_stats = {
        'total_apps': total_apps,
        'response_rate': round((len(responses) / total_apps * 100), 1) if total_apps > 0 else 0,
        'offer_rate': round((len(offers) / total_apps * 100), 1) if total_apps > 0 else 0,
        'avg_response_time': avg_response_time
    }

    # Calculate university progression for this company
    uni_progression = defaultdict(lambda: {
        'Applied': 0, 'Online Assessment Received': 0, 'Phone Interview Scheduled': 0,
        'Assessment Centre Invited': 0, 'Offered': 0
    })

    for app in company_apps:
        if app.get('university'):
            uni = app['university']
            status = app.get('status', 'Applied')
            uni_progression[uni]['Applied'] += 1
            if status in uni_progression[uni]:
                uni_progression[uni][status] += 1

    # Convert to percentage and filter universities with meaningful data
    university_progression = {}
    for uni, stages in uni_progression.items():
        total_applied = stages.get('Applied', 0)
        if total_applied >= 2:  # Minimum threshold
            university_progression[uni] = {
                'total_apps': total_applied,
                'assessment_rate': round((stages.get('Online Assessment Received', 0) / total_applied * 100), 1) if total_applied > 0 else 0,
                'interview_rate': round(((stages.get('Phone Interview Scheduled', 0) + stages.get('Assessment Centre Invited', 0)) / total_applied * 100), 1) if total_applied > 0 else 0,
                'offer_rate': round((stages.get('Offered', 0) / total_applied * 100), 1) if total_applied > 0 else 0
            }

    return jsonify({
        'company_stats': company_stats if total_apps > 0 else None,
        'university_progression': university_progression
    })


@app.route('/api/company-insights/<company_name>')
def api_company_insights(company_name):
    """Get detailed insights and analytics for a specific company"""

    with open(tracker_file, 'r') as f:
        all_applications = json.load(f)

    # Filter applications for this company
    company_apps = [app for app in all_applications if app.get('company', '').lower() == company_name.lower()]

    if not company_apps:
        return jsonify({'error': 'No data available'})

    # Calculate timeline insights
    monthly_apps = defaultdict(int)
    for app in company_apps:
        if app.get('application_date'):
            try:
                app_date = datetime.strptime(app['application_date'], '%Y-%m-%d').date()
                month_key = app_date.strftime('%Y-%m')
                monthly_apps[month_key] += 1
            except:
                pass

    # Calculate stage progression insights
    stage_counts = defaultdict(int)
    for app in company_apps:
        status = app.get('status', 'Applied')
        stage_counts[status] += 1

    # Calculate WAM distribution if available
    wam_ranges = {'70-74': 0, '75-79': 0, '80-84': 0, '85+': 0, 'Unknown': 0}
    for app in company_apps:
        wam = app.get('wam', '')
        if wam and str(wam).replace('.', '').isdigit():
            wam_val = float(wam)
            if wam_val >= 85:
                wam_ranges['85+'] += 1
            elif wam_val >= 80:
                wam_ranges['80-84'] += 1
            elif wam_val >= 75:
                wam_ranges['75-79'] += 1
            elif wam_val >= 70:
                wam_ranges['70-74'] += 1
        else:
            wam_ranges['Unknown'] += 1

    # Calculate priority distribution
    priority_counts = defaultdict(int)
    for app in company_apps:
        priority = app.get('priority', 'Medium')
        priority_counts[priority] += 1

    # Generate insights
    insights = []

    # Response time insight
    response_times = []
    for app in company_apps:
        if app.get('application_date') and app.get('response_date'):
            try:
                app_date = datetime.strptime(app['application_date'], '%Y-%m-%d').date()
                resp_date = datetime.strptime(app['response_date'], '%Y-%m-%d').date()
                response_times.append((resp_date - app_date).days)
            except:
                pass

    if response_times:
        avg_response = sum(response_times) / len(response_times)
        if avg_response < 7:
            insights.append({
                'type': 'positive',
                'title': 'Fast Response Time',
                'description': f'Average response time of {round(avg_response)} days indicates efficient recruitment'
            })
        elif avg_response > 30:
            insights.append({
                'type': 'warning',
                'title': 'Slow Response Time',
                'description': f'Average response time of {round(avg_response)} days - consider following up'
            })

    # Success rate insight
    offers = len([app for app in company_apps if app.get('status') == 'Offered'])
    offer_rate = round((offers / len(company_apps) * 100), 1)

    if offer_rate > 20:
        insights.append({
            'type': 'positive',
            'title': 'High Success Rate',
            'description': f'{offer_rate}% offer rate suggests good candidate-company fit'
        })
    elif offer_rate < 5:
        insights.append({
            'type': 'info',
            'title': 'Competitive Process',
            'description': f'{offer_rate}% offer rate indicates highly selective recruitment'
        })

    return jsonify({
        'timeline_data': dict(monthly_apps),
        'stage_progression': dict(stage_counts),
        'wam_distribution': wam_ranges,
        'priority_distribution': dict(priority_counts),
        'insights': insights,
        'total_tracked': len(company_apps)
    })





@app.route('/experiences')
def experiences():
    # Load all submissions and display as experiences
    with open(data_file, 'r') as f:
        submissions = json.load(f)

    # Convert submissions to experience format
    experience_items = []
    for sub in submissions:
        content_parts = []
        if sub.get('application_stages'):
            content_parts.append(f"Application: {sub['application_stages']}")
        if sub.get('interview_experience'):
            content_parts.append(f"Interview: {sub['interview_experience']}")
        if sub.get('advice'):
            content_parts.append(f"Advice: {sub['advice']}")

        experience_items.append({
            "content": " • ".join(content_parts),
            "firm_name": sub['company'],
            "quality_score": 0.95,
            "primary_cat": sub.get('theme', 'other').lower().replace(' ', '_'),
            "cat_labels": [sub.get('theme', 'Other')],
            "is_submission": True,
            "experience_type": sub.get('experience_type', ''),
            "role": sub.get('role', ''),
            "timestamp": sub.get('timestamp', ''),
            "user_name": sub.get('user_name', 'Anonymous'),
            "source": sub.get('source', 'user'),
            "pro_tip": sub.get('pro_tip', ''),
            "advice": sub.get('advice', '')
        })

    # Sort by timestamp (most recent first)
    experience_items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    return render_template("experiences.html", experiences=experience_items, is_filtered=True)


@app.route('/experiences/<firm_name>')
def firm_experiences(firm_name):
    from collections import Counter
    from categorizer import classify_text, label

    # Get university data for this firm
    university_data = FIRM_UNIVERSITY_DATA.get(firm_name, None)

    # Create company slug and title for template
    company_slug = firm_name.lower().replace(' ', '-').replace('&', 'and')
    company_title = firm_name.replace('-', ' ').replace('%20', ' ').strip().title()

    # Load submissions data for this firm
    with open(data_file, 'r') as f:
        submissions = json.load(f)

    firm_submissions = [s for s in submissions if s.get('company', '').lower() == firm_name.lower()]

    # Convert submissions to experience format for display
    items = []
    for sub in firm_submissions:
        content_parts = []
        if sub.get('application_stages'):
            content_parts.append(f"Application process: {sub['application_stages']}")
        if sub.get('interview_experience'):
            content_parts.append(f"Interview experience: {sub['interview_experience']}")
        if sub.get('advice'):
            content_parts.append(f"Advice: {sub['advice']}")

        items.append({
            "content": " • ".join(content_parts),
            "firm_name": sub['company'],
            "quality_score": 0.95,
            "primary_cat": sub.get('theme', 'other').lower().replace(' ', '_'),
            "cat_labels": [sub.get('theme', 'Other')],
            "is_submission": True,
            "experience_type": sub.get('experience_type', ''),
            "role": sub.get('role', ''),
            "timestamp": sub.get('timestamp', ''),
            "user_name": sub.get('user_name', 'Anonymous'),
            "source": sub.get('source', 'user'),
            "application_process": sub.get('application_stages', ''),
            "application_stages": sub.get('application_stages', ''),
            "interview_experience": sub.get('interview_experience', ''),
            "pro_tip": sub.get('pro_tip', ''),
            "advice": sub.get('advice', '')
        })

    # Apply category filter
    active_cat = request.args.get("cat")
    if active_cat:
        items = [item for item in items if item.get("primary_cat") == active_cat]

    # Build category counts
    cat_counts = Counter(item["primary_cat"] for item in items if item.get("primary_cat"))

    return render_template("experiences.html", 
                         experiences=items, 
                         firm_name=firm_name,
                         company=firm_name,
                         company_slug=company_slug,
                         company_title=company_title,
                         is_filtered=True,
                         university_data=university_data,
                         cat_counts=cat_counts,
                         active_cat=active_cat)


@app.route('/law-match', methods=['GET', 'POST'])
def law_match():
    if request.method == 'POST':
        uni = request.form['uni']
        wam_str = request.form['wam'].strip().lower()
        if wam_str in ['nan', 'inf', '-inf', '+inf']:
            return "Invalid WAM value", 400
        try:
            wam = float(request.form['wam'])
            if not (0 <= wam <= 100):  # WAM should be between 0-100
                return "WAM must be between 0 and 100", 400
        except ValueError:
            return "Invalid WAM value", 400
        interest = request.form['interest']
        preference = request.form['preference']
        experience = request.form.get('experience', 'none')
        location = request.form.get('location', 'any')
        grad_year = request.form.get('grad_year', '2025')

        # Load real firm data from CSV
        firms = load_cards_v2("out/grad_program_signals.csv")
        firm_data_lookup = {firm['name']: firm for firm in firms}
        
        # Enhanced firm profiling with real data integration
        base_profiles = {
            'Allens': {
                'tier': 'top', 'prestige_score': 95, 'training_score': 90, 'worklife_score': 65,
                'competitive_level': 'very_high', 'wam_threshold': 82,
                'strengths': ['Corporate M&A', 'Banking & Finance', 'Competition Law'],
                'culture': 'Traditional, high-performing, competitive'
            },
            'King & Wood Mallesons': {
                'tier': 'top', 'prestige_score': 95, 'training_score': 85, 'worklife_score': 60,
                'competitive_level': 'very_high', 'wam_threshold': 83,
                'strengths': ['Asia-Pacific focus', 'Corporate M&A', 'Capital Markets'],
                'culture': 'International, demanding, prestigious'
            },
            'Herbert Smith Freehills': {
                'tier': 'top', 'prestige_score': 90, 'training_score': 88, 'worklife_score': 68,
                'competitive_level': 'very_high', 'wam_threshold': 81,
                'strengths': ['Dispute Resolution', 'Energy & Resources', 'Corporate'],
                'culture': 'Global outlook, collaborative, high standards'
            },
            'Gilbert + Tobin': {
                'tier': 'top', 'prestige_score': 88, 'training_score': 92, 'worklife_score': 75,
                'competitive_level': 'high', 'wam_threshold': 78,
                'strengths': ['Litigation', 'Corporate Advisory', 'Employment'],
                'culture': 'Innovative, collegial, quality-focused'
            },
            'Clayton Utz': {
                'tier': 'mid-top', 'prestige_score': 85, 'training_score': 85, 'worklife_score': 70,
                'competitive_level': 'high', 'wam_threshold': 76,
                'strengths': ['Insurance', 'Construction', 'Government Advisory'],
                'culture': 'Client-focused, collaborative, supportive'
            },
            'Ashurst': {
                'tier': 'mid-top', 'prestige_score': 82, 'training_score': 80, 'worklife_score': 72,
                'competitive_level': 'high', 'wam_threshold': 75,
                'strengths': ['Infrastructure', 'Corporate', 'Financial Services'],
                'culture': 'International, team-oriented, developmental'
            },
            'MinterEllison': {
                'tier': 'mid', 'prestige_score': 78, 'training_score': 85, 'worklife_score': 75,
                'competitive_level': 'moderate', 'wam_threshold': 73,
                'strengths': ['Government', 'Health', 'Workplace Relations'],
                'culture': 'Diverse, inclusive, development-focused'
            },
            'Corrs Chambers Westgarth': {
                'tier': 'mid', 'prestige_score': 75, 'training_score': 82, 'worklife_score': 78,
                'competitive_level': 'moderate', 'wam_threshold': 72,
                'strengths': ['Corporate', 'Competition', 'Intellectual Property'],
                'culture': 'Collegiate, supportive, quality work'
            },
            'Lander & Rogers': {
                'tier': 'mid', 'prestige_score': 70, 'training_score': 88, 'worklife_score': 85,
                'competitive_level': 'moderate', 'wam_threshold': 70,
                'strengths': ['Family Law', 'Commercial', 'Property'],
                'culture': 'Melbourne-focused, mentoring, work-life balance'
            }
        }

        # Merge real data with base profiles
        firm_profiles = {}
        for firm_name, base_profile in base_profiles.items():
            profile = base_profile.copy()
            
            # Add real salary data if available
            real_data = firm_data_lookup.get(firm_name)
            if real_data and real_data.get('avg_salary'):
                profile['avg_salary'] = real_data['avg_salary']
                profile['salary_range'] = real_data.get('salary_range', f"${real_data['avg_salary']:,.0f}")
            else:
                # Fallback salary estimates based on tier
                salary_estimates = {
                    'top': {'avg': 87000, 'range': '82-95k'},
                    'mid-top': {'avg': 82000, 'range': '76-88k'},
                    'mid': {'avg': 75000, 'range': '70-82k'}
                }
                est = salary_estimates.get(profile['tier'], salary_estimates['mid'])
                profile['avg_salary'] = est['avg']
                profile['salary_range'] = est['range']
            
            firm_profiles[firm_name] = profile

        # Enhanced scoring algorithm
        firm_scores = {}
        
        for firm, profile in firm_profiles.items():
            score = 50.0  # Base score
            reasons = []
            confidence_factors = []
            
            # University representation (weighted by firm tier)
            uni_percentage = FIRM_UNIVERSITY_DATA.get(firm, {}).get(uni, FIRM_UNIVERSITY_DATA.get(firm, {}).get('Other', 0))
            uni_weight = 1.5 if profile['tier'] == 'top' else 1.2 if profile['tier'] == 'mid-top' else 1.0
            
            if uni_percentage >= 20:
                uni_bonus = 25 * uni_weight
                score += uni_bonus
                reasons.append(f"Strong {uni} representation ({uni_percentage}%)")
                confidence_factors.append('high_uni_rep')
            elif uni_percentage >= 10:
                uni_bonus = 15 * uni_weight
                score += uni_bonus
                reasons.append(f"Good {uni} representation ({uni_percentage}%)")
                confidence_factors.append('medium_uni_rep')
            elif uni_percentage >= 5:
                uni_bonus = 8 * uni_weight
                score += uni_bonus
                reasons.append(f"Some {uni} representation ({uni_percentage}%)")

            # WAM scoring with firm-specific thresholds
            wam_threshold = profile.get('wam_threshold', 75)
            wam_diff = wam - wam_threshold
            
            if wam_diff >= 10:
                score += 35
                reasons.append(f"WAM well above typical threshold ({wam:.1f} vs {wam_threshold})")
                confidence_factors.append('excellent_wam')
            elif wam_diff >= 5:
                score += 25
                reasons.append(f"WAM above typical requirements ({wam:.1f})")
                confidence_factors.append('strong_wam')
            elif wam_diff >= 0:
                score += 15
                reasons.append(f"WAM meets requirements ({wam:.1f})")
                confidence_factors.append('adequate_wam')
            elif wam_diff >= -5:
                score += 5
                reasons.append(f"WAM slightly below typical ({wam:.1f})")
            else:
                score -= 10
                reasons.append(f"WAM below typical threshold")

            # Preference alignment with dynamic weighting
            pref_weight = 0.3
            if preference == 'prestige':
                pref_score = profile['prestige_score'] * pref_weight
                score += pref_score
                reasons.append(f"High prestige rating ({profile['prestige_score']}/100)")
            elif preference == 'training':
                pref_score = profile['training_score'] * pref_weight
                score += pref_score
                reasons.append(f"Strong training programs ({profile['training_score']}/100)")
            elif preference == 'worklife':
                pref_score = profile['worklife_score'] * pref_weight
                score += pref_score
                reasons.append(f"Good work-life balance ({profile['worklife_score']}/100)")
            elif preference == 'salary':
                salary_score = min(25, (profile['avg_salary'] - 70000) / 1000)
                score += salary_score
                reasons.append(f"Competitive salary (${profile['avg_salary']:,.0f})")

            # Experience level fit (only add specific bonuses, no generic reasons)
            exp_bonus = 0
            if experience == 'extensive' and profile['competitive_level'] == 'very_high':
                exp_bonus = 15
            elif experience == 'some' and profile['competitive_level'] in ['high', 'moderate']:
                exp_bonus = 12
            elif experience == 'none' and profile['competitive_level'] == 'moderate':
                exp_bonus = 15
                reasons.append("Welcomes graduates without prior legal experience")
            elif experience == 'none' and profile['competitive_level'] == 'high':
                exp_bonus = 5
            
            score += exp_bonus

            # Interest area alignment (improved matching)
            interest_bonus = 0
            interest_keywords = {
                'commercial': ['corporate', 'm&a', 'banking', 'finance', 'commercial'],
                'litigation': ['litigation', 'dispute', 'resolution', 'employment'],
                'family': ['family'],
                'criminal': ['criminal'],
                'employment': ['employment', 'workplace'],
                'property': ['property', 'real estate'],
                'tax': ['tax'],
                'other': []
            }
            
            user_keywords = interest_keywords.get(interest, [])
            for strength in profile['strengths']:
                for keyword in user_keywords:
                    if keyword.lower() in strength.lower():
                        interest_bonus += 18
                        reasons.append(f"Strong expertise in {strength}")
                        confidence_factors.append('practice_match')
                        break
            
            score += interest_bonus

            # Location bonus (if specific location preference)
            if location != 'any':
                real_data = firm_data_lookup.get(firm)
                if real_data and real_data.get('top_city'):
                    if location.lower() in real_data['top_city'].lower():
                        score += 8
                        reasons.append(f"Strong presence in {location}")

            # Calculate confidence level
            confidence = 'Low'
            if len(confidence_factors) >= 3 or 'excellent_wam' in confidence_factors:
                confidence = 'High'
            elif len(confidence_factors) >= 2 or any(f in confidence_factors for f in ['strong_wam', 'high_uni_rep']):
                confidence = 'Medium'

            firm_scores[firm] = {
                'score': max(0, min(100, score)),
                'profile': profile,
                'reasons': reasons[:4],  # Limit to top 4 reasons
                'uni_percentage': uni_percentage,
                'confidence': confidence
            }

        # Sort and select top recommendations
        sorted_firms = sorted(firm_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        top_firms = sorted_firms[:5]

        # Generate recommendations
        recommendations = []
        for i, (firm_name, firm_data) in enumerate(top_firms):
            rec_type = 'Primary' if i == 0 else 'Strong Alternative' if i == 1 else 'Consider'
            
            # Only include reasons that are specific and meaningful
            meaningful_reasons = []
            for reason in firm_data['reasons']:
                # Skip generic reasons
                if not any(generic in reason.lower() for generic in [
                    'be genuine', 'prepare thoroughly', 'show enthusiasm',
                    'good experience level', 'matches firm expectations'
                ]):
                    meaningful_reasons.append(reason)
            
            recommendations.append({
                'firm': firm_name,
                'confidence': firm_data['confidence'],
                'recommendation_type': rec_type,
                'score': round(firm_data['score'], 1),
                'reasons': meaningful_reasons[:3],  # Limit to top 3 specific reasons
                'profile': firm_data['profile']
            })

        # Generate sophisticated insights (only meaningful ones)
        insights = []
        primary_firm = top_firms[0][1]
        
        # Only add WAM insights if they're meaningful
        wam_threshold = primary_firm['profile'].get('wam_threshold', 75)
        if wam >= wam_threshold + 10:
            insights.append("Your WAM puts you in the top tier of applicants - you're highly competitive!")
        elif wam < wam_threshold - 5:
            insights.append("Consider emphasizing other strengths like work experience and leadership to offset WAM requirements.")

        # Only add university insights if there's strong representation
        if primary_firm['uni_percentage'] >= 20:
            insights.append(f"Your university has excellent placement rates at {top_firms[0][0]} - leverage alumni networks.")
        
        # Only add competition insights if there's a clear pattern
        score_spread = top_firms[0][1]['score'] - top_firms[-1][1]['score']
        if score_spread > 25:
            insights.append(f"You have a clear standout match in {top_firms[0][0]}.")
        
        # Only add experience insights if there's a meaningful gap
        if experience == 'none' and len([f for f in top_firms[:3] if f[1]['profile']['competitive_level'] == 'very_high']) >= 2:
            insights.append("Consider gaining legal work experience to strengthen applications to highly competitive firms.")
        
        return render_template('law_match_result.html', 
                             recommendations=recommendations,
                             insights=insights,
                             user_profile={
                                 'uni': uni, 'wam': wam, 'interest': interest, 
                                 'preference': preference, 'experience': experience
                             })

    return render_template('law_match.html')


@app.route('/tracker')
def tracker():
    current_user = get_current_user()
    user_id = current_user['user_id'] if current_user else None
    user_name = current_user['username'] if current_user else None

    applications = []
    if user_id:
        with open(tracker_file, 'r') as f:
            all_applications = json.load(f)

        # Filter applications for current user
        user_applications = [app for app in all_applications if app.get('user_id') == user_id]

        # Convert date strings to datetime objects for display
        for app in user_applications:
            if app.get('application_date'):
                app['application_date'] = datetime.strptime(app['application_date'], '%Y-%m-%d').date()
            if app.get('response_date'):
                app['response_date'] = datetime.strptime(app['response_date'], '%Y-%m-%d').date()

        applications = sorted(user_applications, key=lambda x: x.get('application_date', date.min), reverse=True)

    return render_template('tracker.html', applications=applications, user_id=user_id, user_name=user_name)


@app.route('/tracker/add', methods=['POST'])
@login_required
def add_application():
    current_user = get_current_user()
    user_id = current_user['user_id']
    user_name = current_user['username']

    with open(tracker_file, 'r') as f:
        applications = json.load(f)

    # Get next ID
    next_id = max([app.get('id', 0) for app in applications], default=0) + 1

    new_application = {
        'id': next_id,
        'company': request.form['company'],
        'role': request.form['role'],
        'application_date': request.form['application_date'],
        'university': request.form.get('university', ''),
        'wam': request.form.get('wam', ''),
        'status': request.form['status'],
        'response_date': request.form.get('response_date', ''),
        'priority': request.form.get('priority', ''),
        'notes': request.form.get('notes', ''),
        'user_id': user_id,
        'user_name': user_name,
        'timestamp': datetime.utcnow().isoformat()
    }

    applications.append(new_application)

    with open(tracker_file, 'w') as f:
        json.dump(applications, f, indent=2)

    return redirect(url_for('tracker'))


@app.route('/tracker/update/<int:app_id>', methods=['POST'])
@login_required
def update_application(app_id):
    current_user = get_current_user()
    user_id = current_user['user_id']

    with open(tracker_file, 'r') as f:
        applications = json.load(f)

    # Find and update application if it belongs to the user
    for app in applications:
        if app.get('id') == app_id and app.get('user_id') == user_id:
            # Update fields from request
            if 'status' in request.json:
                app['status'] = request.json['status']
            if 'response_date' in request.json:
                app['response_date'] = request.json['response_date']
            if 'notes' in request.json:
                app['notes'] = request.json['notes']
            if 'priority' in request.json:
                app['priority'] = request.json['priority']

            app['updated'] = datetime.utcnow().isoformat()
            break

    with open(tracker_file, 'w') as f:
        json.dump(applications, f, indent=2)

    return jsonify({'success': True})


@app.route('/tracker/delete/<int:app_id>', methods=['DELETE'])
@login_required
def delete_application(app_id):
    current_user = get_current_user()
    user_id = current_user['user_id']

    with open(tracker_file, 'r') as f:
        applications = json.load(f)

    # Remove application if it belongs to the user
    applications = [app for app in applications if not (app.get('id') == app_id and app.get('user_id') == user_id)]

    with open(tracker_file, 'w') as f:
        json.dump(applications, f, indent=2)

    return jsonify({'success': True})


@app.route('/tracker/analytics')
@login_required
def tracker_analytics():
    current_user = get_current_user()
    user_id = current_user['user_id']

    with open(tracker_file, 'r') as f:
        all_applications = json.load(f)

    # Personal stats
    user_apps = [app for app in all_applications if app.get('user_id') == user_id]

    total_applications = len(user_apps)
    responded_apps = [app for app in user_apps if app.get('response_date')]
    response_rate = round((len(responded_apps) / total_applications * 100), 1) if total_applications > 0 else 0

    # Calculate average response time
    response_times = []
    for app in responded_apps:
        if app.get('application_date') and app.get('response_date'):
            app_date = datetime.strptime(app['application_date'], '%Y-%m-%d').date()
            resp_date = datetime.strptime(app['response_date'], '%Y-%m-%d').date()
            response_times.append((resp_date - app_date).days)

    avg_response_time = round(sum(response_times) / len(response_times)) if response_times else 0

    # Success rate (offers/total)
    successful_apps = [app for app in user_apps if app.get('status') == 'Offered']
    success_rate = round((len(successful_apps) / total_applications * 100), 1) if total_applications > 0 else 0

    personal_stats = {
        'total_applications': total_applications,
        'response_rate': response_rate,
        'avg_response_time': avg_response_time,
        'success_rate': success_rate
    }

    # Enhanced community insights with interview stage progression
    company_stats = {}
    university_stats = {}
    stage_progression = {}

    # Define interview stages in progression order
    interview_stages = [
        'Applied',
        'Online Assessment Received',
        'Online Assessment Completed',
        'Phone Interview Scheduled',
        'Phone Interview Completed',
        'Assessment Centre Invited',
        'Assessment Centre Completed',
        'Final Interview Scheduled',
        'Final Interview Completed',
        'Offered'
    ]

    # Aggregate from tracker data with enhanced analytics
    company_counts = defaultdict(lambda: {
        'total_apps': 0, 'responses': 0, 'offers': 0,
        'avg_response_time': 0, 'response_times': []
    })

    uni_stage_progression = defaultdict(lambda: {
        stage: 0 for stage in interview_stages
    })

    uni_company_progression = defaultdict(lambda: defaultdict(lambda: {
        stage: 0 for stage in interview_stages
    }))

    # Add user info from submissions.json for university data
    with open(data_file, 'r') as f:
        submissions = json.load(f)

    for sub in submissions:
        if sub.get('university'):
            uni_stage_progression[sub['university']]['Applied'] += 1
            if sub.get('outcome') == 'Success':
                uni_stage_progression[sub['university']]['Offered'] += 1

    for app in all_applications:
        if app.get('company') and app.get('university'):
            company_counts[app['company']]['total_apps'] += 1

            # Track stage progression by university and company
            status = app.get('status', 'Applied')
            uni_stage_progression[app['university']][status] += 1
            uni_company_progression[app['university']][app['company']][status] += 1

            # Calculate response times
            if app.get('response_date') and app.get('application_date'):
                try:
                    app_date = datetime.strptime(app['application_date'], '%Y-%m-%d').date()
                    resp_date = datetime.strptime(app['response_date'], '%Y-%m-%d').date()
                    response_time = (resp_date - app_date).days
                    company_counts[app['company']]['response_times'].append(response_time)
                    company_counts[app['company']]['responses'] += 1
                except:
                    pass

            # Track offers
            if status == 'Offered':
                company_counts[app['company']]['offers'] += 1

    # Calculate enhanced company stats
    for company, counts in company_counts.items():
        if counts['total_apps'] >= 2:  # Lower threshold for more data
            avg_response_time = 0
            if counts['response_times']:
                avg_response_time = round(sum(counts['response_times']) / len(counts['response_times']), 1)

            company_stats[company] = {
                'total_apps': counts['total_apps'],
                'response_rate': round((counts['responses'] / counts['total_apps'] * 100), 1) if counts['total_apps'] > 0 else 0,
                'offer_rate': round((counts['offers'] / counts['total_apps'] * 100), 1) if counts['total_apps'] > 0 else 0,
                'avg_response_time': avg_response_time
            }

    # Calculate university progression statistics
    for uni, stages in uni_stage_progression.items():
        total_applied = stages.get('Applied', 0)
        if total_applied >= 2:  # Minimum threshold
            university_stats[uni] = {
                'total_apps': total_applied,
                'online_assessment_rate': round((stages.get('Online Assessment Received', 0) / total_applied * 100), 1) if total_applied > 0 else 0,
                'interview_rate': round(((stages.get('Phone Interview Scheduled', 0) + stages.get('Assessment Centre Invited', 0)) / total_applied * 100), 1) if total_applied > 0 else 0,
                'offer_rate': round((stages.get('Offered', 0) / total_applied * 100), 1) if total_applied > 0 else 0,
                'stage_breakdown': {
                    stage: stages.get(stage, 0) for stage in interview_stages
                }
            }

    # Create stage progression data for visualization
    for uni, companies in uni_company_progression.items():
        for company, stages in companies.items():
            total_apps = stages.get('Applied', 0)
            if total_apps >= 1:
                if uni not in stage_progression:
                    stage_progression[uni] = {}
                stage_progression[uni][company] = {
                    'total_apps': total_apps,
                    'progression': {
                        stage: round((count / total_apps * 100), 1) if total_apps > 0 else 0 
                        for stage, count in stages.items()
                    }
                }

    # Sort by success/response rate
    company_stats = dict(sorted(company_stats.items(), key=lambda x: x[1]['response_rate'], reverse=True)[:10])
    university_stats = dict(sorted(university_stats.items(), key=lambda x: x[1]['success_rate'], reverse=True)[:10])

    return render_template('tracker_analytics.html',
                         personal_stats=personal_stats,
                         company_stats=company_stats,
                         university_stats=university_stats,
                         stage_progression=stage_progression,
                         response_time_stats=None)


@app.route('/tracker/export')
@login_required
def export_tracker():
    current_user = get_current_user()
    user_id = current_user['user_id']

    with open(tracker_file, 'r') as f:
        all_applications = json.load(f)

    user_apps = [app for app in all_applications if app.get('user_id') == user_id]

    # Create CSV
    output_file = f'tracker_export_{user_id}.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['company', 'role', 'application_date', 'wam', 'status', 'response_date', 'priority', 'notes']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for app in user_apps:
            writer.writerow({field: app.get(field, '') for field in fieldnames})

    return send_file(output_file, as_attachment=True, download_name=f'applications_{datetime.now().strftime("%Y%m%d")}.csv')


# Legal & Compliance Routes
@app.route('/terms')
def terms():
    return render_template('terms.html', config=LEGAL_CONFIG)


@app.route('/privacy')
def privacy():
    return render_template('privacy.html', config=LEGAL_CONFIG)


@app.route('/moderation')
def moderation():
    return render_template('moderation.html', config=LEGAL_CONFIG)


@app.route('/report')
def report():
    return render_template('report.html', config=LEGAL_CONFIG)


# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = authenticate_user(username, password)
        if user:
            session['user_id'] = user['user_id']
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match')
        elif len(password) < 6:
            flash('Password must be at least 6 characters long')
        elif create_user(username, email, password):
            flash('Account created successfully! Please log in.')
            return redirect(url_for('login'))
        else:
            flash('Username or email already exists')

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)