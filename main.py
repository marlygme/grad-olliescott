
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
    return render_template('index.html', submissions=submissions[::-1])


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        new_entry = {
            'company': request.form['company'],
            'role': request.form['role'],
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


@app.route('/company/<name>')
def company_page(name):
    with open(data_file, 'r') as f:
        data = json.load(f)
    company_entries = [entry for entry in data if entry['company'].lower() == name.lower()]
    return render_template('company.html', company=name, entries=company_entries)


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
