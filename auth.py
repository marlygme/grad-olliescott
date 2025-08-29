
from flask import session, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from datetime import datetime

USERS_FILE = 'users.json'

def init_users_file():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)

def create_user(username, email, password):
    init_users_file()
    
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    
    # Check if user already exists
    if username in users or any(user.get('email') == email for user in users.values()):
        return False
    
    # Create new user
    users[username] = {
        'email': email,
        'password_hash': generate_password_hash(password),
        'created_at': datetime.utcnow().isoformat(),
        'user_id': f"user_{len(users) + 1}"
    }
    
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)
    
    return True

def authenticate_user(username, password):
    init_users_file()
    
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    
    if username in users:
        if check_password_hash(users[username]['password_hash'], password):
            return users[username]
    
    return None

def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def get_current_user():
    if 'user_id' in session:
        init_users_file()
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        
        for username, user_data in users.items():
            if user_data.get('user_id') == session['user_id']:
                return {
                    'user_id': user_data['user_id'],
                    'username': username,
                    'email': user_data.get('email')
                }
    return None
