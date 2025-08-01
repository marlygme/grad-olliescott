
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import json
import os

app = Flask(__name__)

data_file = 'submissions.json'

# Load existing data or create empty
if not os.path.exists(data_file):
    with open(data_file, 'w') as f:
        json.dump([], f)


@app.route('/')
def index():
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
    
    return render_template('index.html', companies=sorted_companies, total_submissions=len(submissions))


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        new_entry = {
            'company': request.form['company'],
            'role': request.form['role'],
            'experience_type': request.form['experience_type'],
            'salary': request.form.get('salary', ''),
            'bonus': request.form.get('bonus', ''),
            'university': request.form.get('university', ''),
            'wam': request.form.get('wam', ''),
            'application_stages': request.form.get('application_stages', ''),
            'interview_experience': request.form.get('interview_experience', ''),
            'outcome': request.form['outcome'],
            'advice': request.form.get('advice', ''),
            'timestamp': datetime.utcnow().isoformat()
        }
        with open(data_file, 'r') as f:
            data = json.load(f)
        data.append(new_entry)
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        return redirect(url_for('index'))
    return render_template('submit.html')


@app.route('/stories')
def stories():
    with open(data_file, 'r') as f:
        submissions = json.load(f)
    return render_template('stories.html', submissions=submissions[::-1])

@app.route('/company/<name>')
def company_page(name):
    with open(data_file, 'r') as f:
        data = json.load(f)
    company_entries = [entry for entry in data if entry['company'].lower() == name.lower()]
    
    # Calculate company stats
    if company_entries:
        success_count = len([e for e in company_entries if e['outcome'] == 'Success'])
        success_rate = round((success_count / len(company_entries)) * 100, 1)
        
        salaries = [int(e['salary']) for e in company_entries if e['salary'] and e['salary'].isdigit()]
        avg_salary = int(sum(salaries) / len(salaries)) if salaries else None
        
        roles = list(set([e['role'] for e in company_entries]))
        
        company_stats = {
            'success_rate': success_rate,
            'avg_salary': avg_salary,
            'roles': roles,
            'total_entries': len(company_entries)
        }
    else:
        company_stats = None
    
    return render_template('company.html', company=name, entries=company_entries, stats=company_stats)


@app.route('/law-match', methods=['GET', 'POST'])
def law_match():
    if request.method == 'POST':
        uni = request.form['uni']
        wam = float(request.form['wam'])
        interest = request.form['interest']
        preference = request.form['preference']

        # Basic rule-based match logic
        if wam >= 75 and preference == 'prestige':
            match = 'Try for top-tier firms like Allens, King & Wood Mallesons, or Herbert Smith Freehills.'
        elif interest == 'commercial':
            match = 'Consider mid-tier firms with strong commercial rotations, like Maddocks or Hall & Wilcox.'
        elif preference == 'worklife':
            match = 'Check out boutique firms or in-house clerkships at government or corporates.'
        else:
            match = 'Start with firms known for training like Lander & Rogers or Gadens.'

        return render_template('law_match_result.html', match=match)

    return render_template('law_match.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
