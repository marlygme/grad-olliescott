from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from datetime import datetime, date
import json
import os
import re
import csv
from collections import defaultdict, Counter
from grad_data import load_cards, load_grad_signals
from grad_data_v2 import load_cards as load_cards_v2

app = Flask(__name__)

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
    # Get user info from Replit headers
    user_id = request.headers.get('X-Replit-User-Id')
    user_name = request.headers.get('X-Replit-User-Name')

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
        if submission['outcome'] == 'Success':
            companies[company]['success_count'] += 1

        if submission['salary'] and submission['salary'].isdigit():
            companies[company]['avg_salary'] += int(submission['salary'])
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

    return render_template('index.html', companies=sorted_companies, total_submissions=len(submissions), firms=firms, user_id=user_id, user_name=user_name)


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    # Get user info from Replit headers
    user_id = request.headers.get('X-Replit-User-Id')
    user_name = request.headers.get('X-Replit-User-Name')

    if request.method == 'POST':
        # Ensure user is authenticated before allowing submission
        if not user_id:
            return redirect(url_for('submit'))

        new_entry = {
            'company': request.form['company'],
            'role': request.form['role'],
            'experience_type': request.form['experience_type'],
            'theme': request.form['theme'],
            'application_stages': request.form.get('application_stages', ''),
            'interview_experience': request.form.get('interview_experience', ''),
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
    
    firm_name = request.args.get("firm")
    generated_draft = None

    if firm_name:
        try:
            from csv_to_submission_draft import generate_submission_for_firm, format_submission_html
            draft_data = generate_submission_for_firm(firm_name)
            generated_draft = format_submission_html(draft_data)
        except Exception as e:
            print(f"Error generating draft: {e}")
            generated_draft = None

    return render_template("submit.html", generated_draft=generated_draft, firm_name=firm_name, user_id=user_id, user_name=user_name)



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
        success_count = len([e for e in company_entries if e['outcome'] == 'Success'])
        success_rate = round((success_count / len(company_entries)) * 100, 1)

        salaries = [int(e['salary']) for e in company_entries if e['salary'] and e['salary'].isdigit()]
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
    from categorizer import classify_text, label

    firms = load_cards_v2("out/grad_program_signals.csv")

    # Load experiences for each firm
    experiences = load_grad_signals("out/grad_program_signals.csv")

    # Group experiences by firm
    firm_experiences = {}
    for exp in experiences:
        firm_name = exp['firm_name']
        if firm_name not in firm_experiences:
            firm_experiences[firm_name] = []

        # Categorize the experience
        content = exp.get("evidence_span", "")
        if content:
            p, cats, details = classify_text(content, threshold=1.0, top_k=3)
            exp["primary_cat"] = p
            exp["cat_labels"] = [label(c) for c in cats]

        firm_experiences[firm_name].append(exp)

    # Add experiences to each firm
    for firm in firms:
        firm['experiences'] = firm_experiences.get(firm['name'], [])[:8]  # Show top 8 experiences
        firm['total_experiences'] = len(firm_experiences.get(firm['name'], []))

    return render_template("companies_v2.html", firms=firms)


@app.route('/api/grad-data')
def api_grad_data():
    return jsonify({"firms": load_cards("out/grad_program_signals.csv")})


@app.route('/experiences')
def experiences():
    experiences = load_grad_signals("out/grad_program_signals.csv")
    return render_template("experiences.html", experiences=experiences)


@app.route('/experiences/<firm_name>')
def firm_experiences(firm_name):
    from collections import Counter
    from categorizer import classify_text, label

    # Get university data for this firm
    university_data = FIRM_UNIVERSITY_DATA.get(firm_name, None)

    # Try to load filtered experiences first
    try:
        from experience_value_filter import load_filtered_for_firm
        items = load_filtered_for_firm(firm_name, min_value=0.58, min_items=8)
        print(f"Loaded {len(items)} filtered experiences for {firm_name}")
        is_filtered = True
    except Exception as e:
        print(f"Error loading filtered experiences: {e}")
        # Fall back to grad signals
        experiences = load_grad_signals("out/grad_program_signals.csv")
        items = [exp for exp in experiences if exp['firm_name'].lower() == firm_name.lower()]
        is_filtered = False

    # Guard: ensure 'content' exists
    items = [it for it in items if isinstance(it.get("content"), str) and it["content"].strip()]

    # Categorize each item
    for item in items:
        content = item.get("content", "") or item.get("evidence_span", "")
        p, cats, details = classify_text(content, threshold=1.0, top_k=3)
        item["primary_cat"] = p
        item["cat_labels"] = [label(c) for c in cats]

    # Apply category filter
    active_cat = request.args.get("cat")
    if active_cat:
        items = [item for item in items if item.get("primary_cat") == active_cat]

    # Build category counts
    cat_counts = Counter(item["primary_cat"] for item in items if item.get("primary_cat"))

    return render_template("experiences.html", 
                         experiences=items, 
                         firm_name=firm_name, 
                         is_filtered=is_filtered,
                         university_data=university_data,
                         cat_counts=cat_counts,
                         active_cat=active_cat)


@app.route('/law-match', methods=['GET', 'POST'])
def law_match():
    if request.method == 'POST':
        uni = request.form['uni']
        wam = float(request.form['wam'])
        interest = request.form['interest']
        preference = request.form['preference']

        # Find firms with good representation from user's university
        uni_matches = []
        for firm, uni_data in FIRM_UNIVERSITY_DATA.items():
            # Check if user's uni has good representation (>= 15%)
            uni_percentage = uni_data.get(uni, uni_data.get('Other', 0))
            if uni_percentage >= 15:
                uni_matches.append((firm, uni_percentage))

        # Sort by university representation
        uni_matches.sort(key=lambda x: x[1], reverse=True)

        # Enhanced rule-based match logic
        if wam >= 75 and preference == 'prestige':
            top_tier = ['Allens', 'King & Wood Mallesons', 'Herbert Smith Freehills', 'Gilbert + Tobin']
            relevant_firms = [firm for firm, _ in uni_matches if firm in top_tier]
            if relevant_firms:
                match = f'Based on your {uni} background and high WAM, consider top-tier firms: {", ".join(relevant_firms[:3])}. '
                match += f'Your university has {uni_matches[0][1]}% representation at {uni_matches[0][0]}.'
            else:
                match = 'Try for top-tier firms like Allens, King & Wood Mallesons, or Herbert Smith Freehills.'
        elif interest == 'commercial':
            if uni_matches:
                match = f'For commercial law, consider firms where {uni} graduates are well-represented: '
                match += f'{", ".join([firm for firm, _ in uni_matches[:3]])}. '
                match += f'Your university has particularly strong representation at {uni_matches[0][0]} ({uni_matches[0][1]}%).'
            else:
                match = 'Consider mid-tier firms with strong commercial rotations, like MinterEllison or Ashurst.'
        elif preference == 'worklife':
            melbourne_focused = [firm for firm, _ in uni_matches if 'Melbourne' in FIRM_UNIVERSITY_DATA[firm] and FIRM_UNIVERSITY_DATA[firm]['University of Melbourne'] > 20]
            if melbourne_focused:
                match = f'For better work-life balance, consider Melbourne-focused firms: {", ".join(melbourne_focused[:2])}. '
                match += 'Also explore boutique firms or in-house clerkships.'
            else:
                match = 'Check out boutique firms, Lander & Rogers, or in-house clerkships at government or corporates.'
        else:
            if uni_matches:
                match = f'Great starting firms for {uni} graduates: {", ".join([firm for firm, _ in uni_matches[:3]])}. '
                match += f'Your university has {uni_matches[0][1]}% representation at {uni_matches[0][0]}.'
            else:
                match = 'Start with firms known for training like Lander & Rogers, MinterEllison, or mid-tier firms.'

        return render_template('law_match_result.html', match=match, uni_matches=uni_matches[:5])

    return render_template('law_match.html')


@app.route('/tracker')
def tracker():
    user_id = request.headers.get('X-Replit-User-Id')
    user_name = request.headers.get('X-Replit-User-Name')

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
def add_application():
    user_id = request.headers.get('X-Replit-User-Id')
    user_name = request.headers.get('X-Replit-User-Name')

    if not user_id:
        return redirect(url_for('tracker'))

    with open(tracker_file, 'r') as f:
        applications = json.load(f)

    # Get next ID
    next_id = max([app.get('id', 0) for app in applications], default=0) + 1

    new_application = {
        'id': next_id,
        'company': request.form['company'],
        'role': request.form['role'],
        'application_date': request.form['application_date'],
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


@app.route('/tracker/delete/<int:app_id>', methods=['DELETE'])
def delete_application(app_id):
    user_id = request.headers.get('X-Replit-User-Id')

    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    with open(tracker_file, 'r') as f:
        applications = json.load(f)

    # Remove application if it belongs to the user
    applications = [app for app in applications if not (app.get('id') == app_id and app.get('user_id') == user_id)]

    with open(tracker_file, 'w') as f:
        json.dump(applications, f, indent=2)

    return jsonify({'success': True})


@app.route('/tracker/analytics')
def tracker_analytics():
    user_id = request.headers.get('X-Replit-User-Id')

    if not user_id:
        return redirect(url_for('tracker'))

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

    # Community insights (aggregate data from submissions and tracker)
    company_stats = {}
    university_stats = {}

    # Aggregate from tracker data
    company_counts = defaultdict(lambda: {'total_apps': 0, 'responses': 0})
    uni_counts = defaultdict(lambda: {'total_apps': 0, 'total_offers': 0})

    # Add user info from submissions.json for university data
    with open(data_file, 'r') as f:
        submissions = json.load(f)

    for sub in submissions:
        if sub.get('university'):
            uni_counts[sub['university']]['total_apps'] += 1
            if sub.get('outcome') == 'Success':
                uni_counts[sub['university']]['total_offers'] += 1

    for app in all_applications:
        if app.get('company'):
            company_counts[app['company']]['total_apps'] += 1
            if app.get('response_date'):
                company_counts[app['company']]['responses'] += 1

    # Calculate rates
    for company, counts in company_counts.items():
        if counts['total_apps'] >= 3:  # Only show companies with 3+ applications
            company_stats[company] = {
                'total_apps': counts['total_apps'],
                'response_rate': round((counts['responses'] / counts['total_apps'] * 100), 1)
            }

    for uni, counts in uni_counts.items():
        if counts['total_apps'] >= 3:  # Only show universities with 3+ applications
            university_stats[uni] = {
                'total_apps': counts['total_apps'],
                'total_offers': counts['total_offers'],
                'success_rate': round((counts['total_offers'] / counts['total_apps'] * 100), 1)
            }

    # Sort by success/response rate
    company_stats = dict(sorted(company_stats.items(), key=lambda x: x[1]['response_rate'], reverse=True)[:10])
    university_stats = dict(sorted(university_stats.items(), key=lambda x: x[1]['success_rate'], reverse=True)[:10])

    return render_template('tracker_analytics.html',
                         personal_stats=personal_stats,
                         company_stats=company_stats,
                         university_stats=university_stats,
                         response_time_stats=None)


@app.route('/tracker/export')
def export_tracker():
    user_id = request.headers.get('X-Replit-User-Id')

    if not user_id:
        return redirect(url_for('tracker'))

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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)