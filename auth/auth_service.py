"""
Authentication service handling secure login, password verification,
session management, and role-based access decorators.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import query_db, execute_db

def authenticate_user(identifier, password, role_hint=None):
    """
    Authenticate user by username, email, or registration number.
    Optionally check role.
    Returns (user_dict, error_message)
    """
    identifier = identifier.strip()
    
    # Check if identifier matches username or email or reference_id
    query = """
        SELECT user_id, username, password_hash, role, reference_id, full_name, email, is_active
        FROM users
        WHERE (username = %s OR email = %s OR reference_id = %s)
    """
    args = [identifier, identifier, identifier]
    
    if role_hint and role_hint in ('admin', 'faculty', 'student'):
        query += " AND role = %s"
        args.append(role_hint)
        
    user = query_db(query, tuple(args), one=True)
    
    if not user:
        return None, "Invalid credentials or account not found."
    
    if not user['is_active']:
        return None, "This account is inactive. Please contact the administrator."
    
    if not check_password_hash(user['password_hash'], password):
        return None, "Invalid password. Please try again."
    
    return user, None

def login_user(user):
    """
    Store user information in Flask session.
    """
    session.clear()
    session['logged_in'] = True
    session['user_id'] = user['user_id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['reference_id'] = user['reference_id']
    session['full_name'] = user['full_name']
    session['email'] = user['email']

def logout_user():
    """
    Clear active user session.
    """
    session.clear()

def get_current_user():
    """
    Get current logged in user details from session.
    """
    if not session.get('logged_in'):
        return None
    return {
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'role': session.get('role'),
        'reference_id': session.get('reference_id'),
        'full_name': session.get('full_name'),
        'email': session.get('email')
    }

def login_required(f):
    """
    Decorator to ensure user is logged in.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """
    Decorator to enforce specific user role(s).
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                flash("Please log in to continue.", "warning")
                return redirect(url_for('auth.login'))
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash("Access denied: You do not have permission to view this page.", "danger")
                if user_role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user_role == 'faculty':
                    return redirect(url_for('faculty.dashboard'))
                elif user_role == 'student':
                    return redirect(url_for('student.dashboard'))
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def create_user_account(username, password, role, reference_id, full_name, email):
    """
    Helper to create a user account when admin adds student or faculty.
    """
    pwd_hash = generate_password_hash(password)
    query = """
        INSERT INTO users (username, password_hash, role, reference_id, full_name, email)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            password_hash = VALUES(password_hash),
            role = VALUES(role),
            reference_id = VALUES(reference_id),
            full_name = VALUES(full_name),
            email = VALUES(email),
            is_active = 1
    """
    execute_db(query, (username, pwd_hash, role, reference_id, full_name, email))
