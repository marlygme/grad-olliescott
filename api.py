from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import json
import os
from collections import defaultdict

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app, supports_credentials=True)

data_file = 'submissions.json'

if not os.path.exists(data_file):
    with open(data_file, 'w') as f:
        json.dump([], f)

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

def load_submissions():
    try:
        with open(data_file, 'r') as f:
            return json.load(f)
    except:
        return []

def save_submissions(submissions):
    with open(data_file, 'w') as f:
        json.dump(submissions, f, indent=2, default=str)

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join('public', path)):
        return send_from_directory('public', path)
    if not '.' in path:
        return send_from_directory('public', path + '.html')
    return send_from_directory('public', 'index.html')

@app.route('/api/companies')
def get_companies():
    submissions = load_submissions()
    companies = {}
    
    for submission in submissions:
        company = submission.get('company', '')
        if not company:
            continue
            
        if company not in companies:
            companies[company] = {
                'name': company,
                'total_submissions': 0,
                'avg_salary': 0,
                'salary_count': 0,
                'recent_roles': set()
            }
        
        companies[company]['total_submissions'] += 1
        
        salary = submission.get('salary', '')
        if salary and str(salary).isdigit():
            companies[company]['avg_salary'] += int(salary)
            companies[company]['salary_count'] += 1
        
        role = submission.get('role', '')
        if role:
            companies[company]['recent_roles'].add(role)
    
    result = []
    for company_data in companies.values():
        if company_data['salary_count'] > 0:
            company_data['avg_salary'] = int(company_data['avg_salary'] / company_data['salary_count'])
        else:
            company_data['avg_salary'] = None
        company_data['recent_roles'] = list(company_data['recent_roles'])[:5]
        del company_data['salary_count']
        result.append(company_data)
    
    result.sort(key=lambda x: x['total_submissions'], reverse=True)
    
    return jsonify({'companies': result})

@app.route('/api/companies/<company_name>')
def get_company(company_name):
    submissions = load_submissions()
    company_submissions = [s for s in submissions if s.get('company', '').lower() == company_name.lower()]
    
    company_data = None
    if company_submissions:
        total_salary = 0
        salary_count = 0
        roles = set()
        
        for s in company_submissions:
            if s.get('role'):
                roles.add(s['role'])
            salary = s.get('salary', '')
            if salary and str(salary).isdigit():
                total_salary += int(salary)
                salary_count += 1
        
        company_data = {
            'name': company_name,
            'total_submissions': len(company_submissions),
            'avg_salary': int(total_salary / salary_count) if salary_count > 0 else None,
            'recent_roles': list(roles)[:5]
        }
    
    return jsonify({
        'company': company_data,
        'experiences': company_submissions
    })

@app.route('/api/experiences')
def get_experiences():
    submissions = load_submissions()
    
    company = request.args.get('company', '')
    theme = request.args.get('theme', '')
    search = request.args.get('search', '')
    
    filtered = submissions
    
    if company:
        filtered = [s for s in filtered if s.get('company', '').lower() == company.lower()]
    
    if theme:
        filtered = [s for s in filtered if s.get('theme', '') == theme]
    
    if search:
        search_lower = search.lower()
        filtered = [s for s in filtered if 
            search_lower in s.get('company', '').lower() or
            search_lower in s.get('role', '').lower() or
            search_lower in s.get('general_experience', '').lower()
        ]
    
    return jsonify({'experiences': filtered})

@app.route('/api/experiences/<int:experience_id>')
def get_experience(experience_id):
    submissions = load_submissions()
    if 0 <= experience_id < len(submissions):
        return jsonify(submissions[experience_id])
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/experiences', methods=['POST'])
def create_experience():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    submissions = load_submissions()
    
    new_submission = {
        'id': len(submissions),
        'company': data.get('company', ''),
        'role': data.get('role', ''),
        'experience_type': data.get('experience_type', ''),
        'theme': data.get('theme', ''),
        'application_stages': data.get('application_stages', ''),
        'interview_experience': data.get('interview_experience', ''),
        'assessment_centre': data.get('assessment_centre', ''),
        'program_structure': data.get('program_structure', ''),
        'salary_benefits': data.get('salary_benefits', ''),
        'culture_environment': data.get('culture_environment', ''),
        'hours_workload': data.get('hours_workload', ''),
        'practice_areas': data.get('practice_areas', ''),
        'general_experience': data.get('general_experience', ''),
        'pro_tip': data.get('pro_tip', ''),
        'advice': data.get('advice', ''),
        'created_at': datetime.now().isoformat()
    }
    
    submissions.append(new_submission)
    save_submissions(submissions)
    
    return jsonify(new_submission), 201

@app.route('/api/user')
def get_current_user():
    user_id = request.headers.get('X-Replit-User-Id')
    username = request.headers.get('X-Replit-User-Name')
    
    if not user_id:
        return jsonify(None)
    
    return jsonify({
        'user_id': user_id,
        'username': username
    })

applications_store = {}

@app.route('/api/applications')
def get_applications():
    user_id = request.headers.get('X-Replit-User-Id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    user_apps = applications_store.get(user_id, [])
    return jsonify({'applications': user_apps})

@app.route('/api/applications', methods=['POST'])
def create_application():
    user_id = request.headers.get('X-Replit-User-Id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if user_id not in applications_store:
        applications_store[user_id] = []
    
    new_app = {
        'id': len(applications_store[user_id]) + 1,
        'company': data.get('company', ''),
        'role': data.get('role', ''),
        'status': data.get('status', 'Applied'),
        'priority': data.get('priority', 'Medium'),
        'application_date': data.get('application_date'),
        'notes': data.get('notes', ''),
        'created_at': datetime.now().isoformat()
    }
    
    applications_store[user_id].append(new_app)
    return jsonify(new_app), 201

@app.route('/api/applications/<int:app_id>', methods=['PUT'])
def update_application(app_id):
    user_id = request.headers.get('X-Replit-User-Id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    user_apps = applications_store.get(user_id, [])
    
    for app in user_apps:
        if app['id'] == app_id:
            app.update(data)
            return jsonify(app)
    
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/applications/<int:app_id>', methods=['DELETE'])
def delete_application(app_id):
    user_id = request.headers.get('X-Replit-User-Id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    user_apps = applications_store.get(user_id, [])
    
    for i, app in enumerate(user_apps):
        if app['id'] == app_id:
            del user_apps[i]
            return jsonify({'success': True})
    
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/firm-university-data')
def get_firm_university_data():
    return jsonify(FIRM_UNIVERSITY_DATA)

@app.route('/api/law-match', methods=['POST'])
def law_match():
    data = request.get_json()
    university = data.get('university', '')
    wam = float(data.get('wam', 70))
    
    results = []
    
    for firm, uni_data in FIRM_UNIVERSITY_DATA.items():
        uni_percentage = uni_data.get(university, uni_data.get('Other', 0))
        score = uni_percentage
        
        if wam >= 80:
            score *= 1.3
        elif wam >= 70:
            score *= 1.1
        elif wam < 60:
            score *= 0.8
        
        match_level = 'Strong' if score >= 20 else 'Good' if score >= 10 else 'Moderate'
        
        results.append({
            'firm': firm,
            'score': round(score),
            'uni_percentage': uni_percentage,
            'match_level': match_level
        })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({'results': results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
