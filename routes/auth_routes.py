"""
Authentication routes for login, logout, and redirection.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from auth.auth_service import authenticate_user, login_user, logout_user, login_required
from database.db import query_db, execute_db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if session.get('logged_in'):
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'faculty':
            return redirect(url_for('faculty.dashboard'))
        elif role == 'student':
            return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '').strip()
        role_hint = request.form.get('role', '').strip()

        if not identifier or not password:
            flash("Please enter both username/ID and password.", "danger")
            return render_template('auth/login.html', identifier=identifier, role=role_hint)

        user, err = authenticate_user(identifier, password, role_hint if role_hint else None)
        if err:
            flash(err, "danger")
            return render_template('auth/login.html', identifier=identifier, role=role_hint)

        login_user(user)
        flash(f"Welcome back, {user['full_name']}! Logged in as {user['role'].title()}.", "success")

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)

        if user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user['role'] == 'faculty':
            return redirect(url_for('faculty.dashboard'))
        elif user['role'] == 'student':
            return redirect(url_for('student.dashboard'))

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session.get('user_id')
    user = query_db("SELECT * FROM users WHERE user_id = %s", (user_id,), one=True)

    if request.method == 'POST':
        current_pwd = request.form.get('current_password', '').strip()
        new_pwd = request.form.get('new_password', '').strip()
        confirm_pwd = request.form.get('confirm_password', '').strip()

        if not current_pwd or not new_pwd:
            flash("Please enter both current and new password.", "danger")
            return render_template('auth/profile.html', user=user)

        if not check_password_hash(user['password_hash'], current_pwd):
            flash("Incorrect current password.", "danger")
            return render_template('auth/profile.html', user=user)

        if new_pwd != confirm_pwd:
            flash("New passwords do not match.", "danger")
            return render_template('auth/profile.html', user=user)

        if len(new_pwd) < 4:
            flash("Password must be at least 4 characters long.", "danger")
            return render_template('auth/profile.html', user=user)

        new_hash = generate_password_hash(new_pwd)
        execute_db("UPDATE users SET password_hash = %s WHERE user_id = %s", (new_hash, user_id))
        flash("Password updated successfully!", "success")
        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', user=user)

