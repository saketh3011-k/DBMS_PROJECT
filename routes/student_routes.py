"""
Student routes for personal attendance dashboard, enrolled courses,
attendance history, low-attendance warnings, attendance simulator,
leave/OD regularization, and notification center.
"""
import math
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth.auth_service import login_required, role_required
from database.db import query_db, execute_db

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.before_request
@login_required
@role_required('student')
def check_student():
    pass

@student_bp.route('/dashboard')
def dashboard():
    student_id = session.get('reference_id')
    student_info = query_db("SELECT * FROM student WHERE student_id = %s", (student_id,), one=True)

    # Subject-wise attendance calculation
    courses_attendance = query_db("""
        SELECT 
            c.course_id,
            c.course_name,
            c.credits,
            f.faculty_name,
            COUNT(a.attendance_id) AS total_classes,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS attended_classes,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_classes,
            ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2) AS attendance_pct
        FROM enrollment e
        JOIN course c ON e.course_id = c.course_id
        LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
        LEFT JOIN attendance a ON e.student_id = a.student_id AND e.course_id = a.course_id
        WHERE e.student_id = %s
        GROUP BY c.course_id, c.course_name, c.credits, f.faculty_name
        ORDER BY c.course_id ASC
    """, (student_id,))

    # Compute overall statistics & check for low attendance (<75%)
    total_conducted = 0
    total_attended = 0
    warning_courses = []

    for item in courses_attendance:
        tot = int(item['total_classes'] or 0)
        att = int(item['attended_classes'] or 0)
        pct = float(item['attendance_pct']) if item['attendance_pct'] is not None else 0.0

        item['percentage_clean'] = pct
        total_conducted += tot
        total_attended += att

        # Calculate Bunk Margin vs Recovery Margin
        if tot > 0:
            if pct < 75.0:
                # Classes needed to attend consecutively to reach 75%:
                needed = max(0, math.ceil((0.75 * tot - att) / 0.25))
                item['classes_needed'] = needed
                item['bunk_safe'] = 0
                warning_courses.append(item)
            else:
                # Safe classes student can miss while maintaining >= 75%:
                # (att) / (tot + x) >= 0.75 => att >= 0.75*tot + 0.75*x => 0.75*x <= att - 0.75*tot
                safe = max(0, math.floor((att - 0.75 * tot) / 0.75))
                item['classes_needed'] = 0
                item['bunk_safe'] = safe
        else:
            item['classes_needed'] = 0
            item['bunk_safe'] = 0

    overall_pct = round((total_attended / total_conducted * 100), 2) if total_conducted > 0 else 0.0

    # Recent attendance records
    recent_records = query_db("""
        SELECT a.date, a.course_id, c.course_name, a.status, a.remarks
        FROM attendance a
        JOIN course c ON a.course_id = c.course_id
        WHERE a.student_id = %s
        ORDER BY a.date DESC
        LIMIT 6
    """, (student_id,))

    # Unread notifications
    notifications = query_db("""
        SELECT * FROM notification 
        WHERE student_id = %s 
        ORDER BY created_at DESC LIMIT 5
    """, (student_id,))

    unread_count = sum(1 for n in notifications if not n['is_read'])

    return render_template('student/dashboard.html',
                           student=student_info,
                           courses=courses_attendance,
                           total_conducted=total_conducted,
                           total_attended=total_attended,
                           overall_pct=overall_pct,
                           warning_courses=warning_courses,
                           recent_records=recent_records,
                           notifications=notifications,
                           unread_count=unread_count)

@student_bp.route('/courses')
def courses():
    student_id = session.get('reference_id')
    enrolled_courses = query_db("""
        SELECT e.semester, e.enrollment_date,
               c.course_id, c.course_name, c.credits, c.department,
               f.faculty_name, f.email AS faculty_email
        FROM enrollment e
        JOIN course c ON e.course_id = c.course_id
        LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
        WHERE e.student_id = %s
        ORDER BY c.course_id ASC
    """, (student_id,))
    return render_template('student/courses.html', courses=enrolled_courses)

@student_bp.route('/history')
def history():
    student_id = session.get('reference_id')
    course_filter = request.args.get('course_id', '').strip()
    status_filter = request.args.get('status', '').strip()

    sql = """
        SELECT a.attendance_id, a.date, a.course_id, c.course_name, f.faculty_name,
               a.status, a.remarks
        FROM attendance a
        JOIN course c ON a.course_id = c.course_id
        LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
        WHERE a.student_id = %s
    """
    params = [student_id]

    if course_filter:
        sql += " AND a.course_id = %s"
        params.append(course_filter)
    if status_filter:
        sql += " AND a.status = %s"
        params.append(status_filter)

    sql += " ORDER BY a.date DESC, a.course_id ASC"
    records = query_db(sql, tuple(params))

    student_courses = query_db("""
        SELECT c.course_id, c.course_name
        FROM enrollment e
        JOIN course c ON e.course_id = c.course_id
        WHERE e.student_id = %s
        ORDER BY c.course_id
    """, (student_id,))

    return render_template('student/history.html',
                           records=records,
                           courses=student_courses,
                           selected_course=course_filter,
                           selected_status=status_filter)

# -------------------------------------------------------------
# FEATURE: ATTENDANCE SIMULATOR & BUNK CALCULATOR
# -------------------------------------------------------------
@student_bp.route('/simulator')
def simulator():
    student_id = session.get('reference_id')
    courses = query_db("""
        SELECT 
            c.course_id, c.course_name,
            COUNT(a.attendance_id) AS total_classes,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS attended_classes,
            ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2) AS attendance_pct
        FROM enrollment e
        JOIN course c ON e.course_id = c.course_id
        LEFT JOIN attendance a ON e.student_id = a.student_id AND e.course_id = a.course_id
        WHERE e.student_id = %s
        GROUP BY c.course_id, c.course_name
        ORDER BY c.course_id ASC
    """, (student_id,))

    course_data = []
    for c in courses:
        tot = int(c['total_classes'] or 0)
        att = int(c['attended_classes'] or 0)
        pct = float(c['attendance_pct']) if c['attendance_pct'] is not None else 0.0

        if tot > 0:
            safe_bunk = max(0, math.floor((att - 0.75 * tot) / 0.75)) if pct >= 75.0 else 0
            needed_75 = max(0, math.ceil((0.75 * tot - att) / 0.25)) if pct < 75.0 else 0
            needed_85 = max(0, math.ceil((0.85 * tot - att) / 0.15)) if pct < 85.0 else 0
        else:
            safe_bunk = 0
            needed_75 = 0
            needed_85 = 0

        course_data.append({
            'course_id': c['course_id'],
            'course_name': c['course_name'],
            'total': tot,
            'attended': att,
            'pct': pct,
            'safe_bunk': safe_bunk,
            'needed_75': needed_75,
            'needed_85': needed_85
        })

    return render_template('student/simulator.html', courses=course_data)

# -------------------------------------------------------------
# FEATURE: LEAVE / OD / MEDICAL APPLICATION WORKFLOW
# -------------------------------------------------------------
@student_bp.route('/leave', methods=['GET'])
def leave():
    student_id = session.get('reference_id')

    # Get student's enrolled courses for the leave dropdown
    enrolled = query_db("""
        SELECT c.course_id, c.course_name, f.faculty_name
        FROM enrollment e
        JOIN course c ON e.course_id = c.course_id
        LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
        WHERE e.student_id = %s
        ORDER BY c.course_id
    """, (student_id,))

    # Past requests
    requests = query_db("""
        SELECT l.*, c.course_name, f.faculty_name
        FROM leave_request l
        JOIN course c ON l.course_id = c.course_id
        LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
        WHERE l.student_id = %s
        ORDER BY l.leave_date DESC, l.request_id DESC
    """, (student_id,))

    return render_template('student/leave.html', courses=enrolled, requests=requests)

@student_bp.route('/leave/apply', methods=['POST'])
def apply_leave():
    student_id = session.get('reference_id')
    course_id = request.form.get('course_id', '').strip()
    leave_date = request.form.get('leave_date', '').strip()
    leave_type = request.form.get('leave_type', 'Medical Leave').strip()
    reason = request.form.get('reason', '').strip()

    if not course_id or not leave_date or not reason:
        flash("All fields are required to apply for leave.", "danger")
        return redirect(url_for('student.leave'))

    try:
        execute_db("""
            INSERT INTO leave_request (student_id, course_id, leave_date, leave_type, reason, status)
            VALUES (%s, %s, %s, %s, %s, 'Pending')
        """, (student_id, course_id, leave_date, leave_type, reason))

        flash("Leave / OD application submitted successfully! Pending faculty review.", "success")
    except Exception as e:
        flash(f"Submission failed: {str(e)}", "danger")

    return redirect(url_for('student.leave'))

# -------------------------------------------------------------
# FEATURE: NOTIFICATION CENTER
# -------------------------------------------------------------
@student_bp.route('/notifications')
def notifications():
    student_id = session.get('reference_id')
    notifs = query_db("""
        SELECT * FROM notification 
        WHERE student_id = %s 
        ORDER BY created_at DESC
    """, (student_id,))
    return render_template('student/notifications.html', notifications=notifs)

@student_bp.route('/notifications/read/<int:nid>', methods=['POST'])
def mark_notification_read(nid):
    student_id = session.get('reference_id')
    execute_db("UPDATE notification SET is_read = 1 WHERE notification_id = %s AND student_id = %s", (nid, student_id))
    return redirect(url_for('student.notifications'))
