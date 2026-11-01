"""
Faculty routes for course oversight, daily attendance marking,
attendance updates, history filtering, and course-wise reports.
"""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth.auth_service import login_required, role_required
from database.db import query_db, execute_db

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')

@faculty_bp.before_request
@login_required
@role_required('faculty')
def check_faculty():
    pass

@faculty_bp.route('/dashboard')
def dashboard():
    faculty_id = session.get('reference_id')
    faculty_info = query_db("SELECT * FROM faculty WHERE faculty_id = %s", (faculty_id,), one=True)

    # Assigned courses
    assigned_courses = query_db("""
        SELECT c.*, COUNT(DISTINCT e.student_id) AS enrolled_count
        FROM course c
        LEFT JOIN enrollment e ON c.course_id = e.course_id
        WHERE c.faculty_id = %s
        GROUP BY c.course_id, c.course_name, c.credits, c.faculty_id, c.department, c.created_at
    """, (faculty_id,))

    # Today's attendance status
    today = date.today().isoformat()
    today_sessions = query_db("""
        SELECT c.course_id, c.course_name,
               COUNT(a.attendance_id) AS marked_count
        FROM course c
        LEFT JOIN attendance a ON c.course_id = a.course_id AND a.date = %s
        WHERE c.faculty_id = %s
        GROUP BY c.course_id, c.course_name
    """, (today, faculty_id))

    # Low attendance students in faculty's courses
    low_att_students = query_db("""
        SELECT s.student_id, s.student_name, c.course_id, c.course_name,
               COUNT(a.attendance_id) AS total,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present,
               ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 1) AS pct
        FROM course c
        JOIN enrollment e ON c.course_id = e.course_id
        JOIN student s ON e.student_id = s.student_id
        LEFT JOIN attendance a ON c.course_id = a.course_id AND s.student_id = a.student_id
        WHERE c.faculty_id = %s
        GROUP BY s.student_id, s.student_name, c.course_id, c.course_name
        HAVING pct < 75.0
        ORDER BY pct ASC
    """, (faculty_id,))

    # Pending leave requests count for this faculty's courses
    pending_leaves = query_db("""
        SELECT COUNT(l.request_id) AS count
        FROM leave_request l
        JOIN course c ON l.course_id = c.course_id
        WHERE c.faculty_id = %s AND l.status = 'Pending'
    """, (faculty_id,), one=True)['count']

    return render_template('faculty/dashboard.html',
                           faculty=faculty_info,
                           courses=assigned_courses,
                           today=today,
                           today_sessions=today_sessions,
                           low_att_students=low_att_students,
                           pending_leaves=pending_leaves)

@faculty_bp.route('/courses')
def courses():
    faculty_id = session.get('reference_id')
    assigned_courses = query_db("""
        SELECT c.*, COUNT(DISTINCT e.student_id) AS enrolled_count,
               COUNT(DISTINCT a.date) AS classes_conducted
        FROM course c
        LEFT JOIN enrollment e ON c.course_id = e.course_id
        LEFT JOIN attendance a ON c.course_id = a.course_id
        WHERE c.faculty_id = %s
        GROUP BY c.course_id, c.course_name, c.credits, c.faculty_id, c.department, c.created_at
    """, (faculty_id,))
    return render_template('faculty/courses.html', courses=assigned_courses)

@faculty_bp.route('/courses/<course_id>/students')
def course_students(course_id):
    faculty_id = session.get('reference_id')
    # Verify course ownership
    course = query_db("SELECT * FROM course WHERE course_id = %s AND faculty_id = %s",
                      (course_id, faculty_id), one=True)
    if not course:
        flash("You are not assigned to this course.", "danger")
        return redirect(url_for('faculty.dashboard'))

    students = query_db("""
        SELECT s.student_id, s.student_name, s.email, s.phone, s.department, e.semester,
               COUNT(a.attendance_id) AS total_classes,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS attended_classes,
               ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 1) AS attendance_pct
        FROM enrollment e
        JOIN student s ON e.student_id = s.student_id
        LEFT JOIN attendance a ON e.student_id = a.student_id AND e.course_id = a.course_id
        WHERE e.course_id = %s
        GROUP BY s.student_id, s.student_name, s.email, s.phone, s.department, e.semester
        ORDER BY s.student_id ASC
    """, (course_id,))

    return render_template('faculty/course_students.html', course=course, students=students)

@faculty_bp.route('/mark-attendance', methods=['GET', 'POST'])
def mark_attendance():
    faculty_id = session.get('reference_id')
    assigned_courses = query_db("SELECT course_id, course_name FROM course WHERE faculty_id = %s ORDER BY course_id", (faculty_id,))

    selected_course = request.args.get('course_id') or (assigned_courses[0]['course_id'] if assigned_courses else '')
    selected_date = request.args.get('date') or date.today().isoformat()

    if request.method == 'POST':
        selected_course = request.form.get('course_id')
        selected_date = request.form.get('date')

        # Check course ownership
        course = query_db("SELECT course_id FROM course WHERE course_id = %s AND faculty_id = %s",
                          (selected_course, faculty_id), one=True)
        if not course:
            flash("Unauthorized course selection.", "danger")
            return redirect(url_for('faculty.mark_attendance'))

        # Fetch enrolled students
        enrolled = query_db("SELECT student_id FROM enrollment WHERE course_id = %s", (selected_course,))
        
        saved_count = 0
        for item in enrolled:
            sid = item['student_id']
            status = request.form.get(f'status_{sid}', 'Absent')
            remarks = request.form.get(f'remarks_{sid}', '').strip()

            # Insert or Update (ensuring no duplicate entries for the same student, course, date)
            execute_db("""
                INSERT INTO attendance (student_id, course_id, date, status, remarks)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    status = VALUES(status),
                    remarks = VALUES(remarks)
            """, (sid, selected_course, selected_date, status, remarks))
            saved_count += 1

        flash(f"Attendance recorded successfully for {saved_count} students on {selected_date} ({selected_course})!", "success")
        return redirect(url_for('faculty.history', course_id=selected_course, date=selected_date))

    # GET: Load enrolled students and existing marks for this course and date
    students = []
    if selected_course:
        students = query_db("""
            SELECT s.student_id, s.student_name, s.department,
                   a.status AS current_status, a.remarks AS current_remarks
            FROM enrollment e
            JOIN student s ON e.student_id = s.student_id
            LEFT JOIN attendance a ON e.student_id = a.student_id AND e.course_id = a.course_id AND a.date = %s
            WHERE e.course_id = %s
            ORDER BY s.student_id ASC
        """, (selected_date, selected_course))

    return render_template('faculty/mark_attendance.html',
                           courses=assigned_courses,
                           selected_course=selected_course,
                           selected_date=selected_date,
                           students=students)

@faculty_bp.route('/history')
def history():
    faculty_id = session.get('reference_id')
    assigned_courses = query_db("SELECT course_id, course_name FROM course WHERE faculty_id = %s ORDER BY course_id", (faculty_id,))

    course_filter = request.args.get('course_id', '').strip()
    date_filter = request.args.get('date', '').strip()

    sql = """
        SELECT a.attendance_id, a.student_id, s.student_name, a.course_id, c.course_name,
               a.date, a.status, a.remarks
        FROM attendance a
        JOIN student s ON a.student_id = s.student_id
        JOIN course c ON a.course_id = c.course_id
        WHERE c.faculty_id = %s
    """
    params = [faculty_id]

    if course_filter:
        sql += " AND a.course_id = %s"
        params.append(course_filter)
    if date_filter:
        sql += " AND a.date = %s"
        params.append(date_filter)

    sql += " ORDER BY a.date DESC, a.course_id ASC, a.student_id ASC"
    records = query_db(sql, tuple(params))

    # Summary by session
    session_summary = query_db("""
        SELECT a.date, a.course_id, c.course_name,
               COUNT(a.attendance_id) AS total_marked,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
               SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_count
        FROM attendance a
        JOIN course c ON a.course_id = c.course_id
        WHERE c.faculty_id = %s
        GROUP BY a.date, a.course_id, c.course_name
        ORDER BY a.date DESC
    """, (faculty_id,))

    return render_template('faculty/attendance_history.html',
                           courses=assigned_courses,
                           selected_course=course_filter,
                           selected_date=date_filter,
                           records=records,
                           session_summary=session_summary)

@faculty_bp.route('/attendance/edit/<int:attendance_id>', methods=['POST'])
def edit_attendance_entry(attendance_id):
    faculty_id = session.get('reference_id')
    status = request.form.get('status')
    remarks = request.form.get('remarks', '').strip()

    # Verify that record belongs to this faculty's course
    entry = query_db("""
        SELECT a.attendance_id FROM attendance a
        JOIN course c ON a.course_id = c.course_id
        WHERE a.attendance_id = %s AND c.faculty_id = %s
    """, (attendance_id, faculty_id), one=True)

    if not entry:
        flash("Record not found or unauthorized.", "danger")
        return redirect(url_for('faculty.history'))

    try:
        execute_db("""
            UPDATE attendance SET status = %s, remarks = %s
            WHERE attendance_id = %s
        """, (status, remarks, attendance_id))
        flash("Attendance updated successfully.", "success")
    except Exception as e:
        flash(f"Update failed: {str(e)}", "danger")

    return redirect(request.referrer or url_for('faculty.history'))

@faculty_bp.route('/reports')
def reports():
    faculty_id = session.get('reference_id')
    assigned_courses = query_db("SELECT course_id, course_name FROM course WHERE faculty_id = %s ORDER BY course_id", (faculty_id,))
    selected_course = request.args.get('course_id') or (assigned_courses[0]['course_id'] if assigned_courses else '')

    course_summary = None
    student_stats = []

    if selected_course:
        course_summary = query_db("""
            SELECT c.course_id, c.course_name, c.credits,
                   COUNT(DISTINCT a.date) AS classes_held,
                   COUNT(a.attendance_id) AS total_records,
                   SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS total_present,
                   SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS total_absent,
                   ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2) AS overall_pct
            FROM course c
            LEFT JOIN attendance a ON c.course_id = a.course_id
            WHERE c.course_id = %s AND c.faculty_id = %s
            GROUP BY c.course_id, c.course_name, c.credits
        """, (selected_course, faculty_id), one=True)

        student_stats = query_db("""
            SELECT s.student_id, s.student_name, s.department, s.email,
                   COUNT(a.attendance_id) AS total_classes,
                   SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS attended_classes,
                   SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_classes,
                   ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2) AS attendance_pct
            FROM enrollment e
            JOIN student s ON e.student_id = s.student_id
            LEFT JOIN attendance a ON e.student_id = a.student_id AND e.course_id = a.course_id
            WHERE e.course_id = %s
            GROUP BY s.student_id, s.student_name, s.department, s.email
            ORDER BY attendance_pct ASC
        """, (selected_course,))

    return render_template('faculty/reports.html',
                           courses=assigned_courses,
                           selected_course=selected_course,
                           course_summary=course_summary,
                           student_stats=student_stats)

# -------------------------------------------------------------
# FEATURE: LEAVE & OD REQUEST APPROVAL WORKFLOW
# -------------------------------------------------------------
@faculty_bp.route('/leave-requests')
def leave_requests():
    faculty_id = session.get('reference_id')
    status_filter = request.args.get('status', 'Pending')

    sql = """
        SELECT l.*, s.student_name, s.department, c.course_name
        FROM leave_request l
        JOIN student s ON l.student_id = s.student_id
        JOIN course c ON l.course_id = c.course_id
        WHERE c.faculty_id = %s
    """
    params = [faculty_id]
    if status_filter and status_filter != 'all':
        sql += " AND l.status = %s"
        params.append(status_filter)

    sql += " ORDER BY l.leave_date DESC, l.request_id DESC"
    requests = query_db(sql, tuple(params))

    return render_template('faculty/leave_requests.html', requests=requests, selected_status=status_filter)

@faculty_bp.route('/leave-requests/<int:rid>/action', methods=['POST'])
def handle_leave_action(rid):
    faculty_id = session.get('reference_id')
    action = request.form.get('action') # 'Approved' or 'Rejected'
    remarks = request.form.get('remarks', '').strip()

    # Verify authorization
    req = query_db("""
        SELECT l.*, c.course_name, f.faculty_name
        FROM leave_request l
        JOIN course c ON l.course_id = c.course_id
        JOIN faculty f ON c.faculty_id = f.faculty_id
        WHERE l.request_id = %s AND c.faculty_id = %s
    """, (rid, faculty_id), one=True)

    if not req:
        flash("Unauthorized or leave request not found.", "danger")
        return redirect(url_for('faculty.leave_requests'))

    if action in ['Approved', 'Rejected']:
        execute_db("""
            UPDATE leave_request
            SET status = %s, faculty_remarks = %s
            WHERE request_id = %s
        """, (action, remarks or f"Decision by faculty on {action}", rid))

        # If approved, automatically regularize attendance as 'Present' with leave remark!
        if action == 'Approved':
            execute_db("""
                INSERT INTO attendance (student_id, course_id, date, status, remarks)
                VALUES (%s, %s, %s, 'Present', %s)
                ON DUPLICATE KEY UPDATE 
                    status = 'Present',
                    remarks = VALUES(remarks)
            """, (req['student_id'], req['course_id'], req['leave_date'], f"Approved {req['leave_type']}: {req['reason'][:50]}"))

        # Send notification to student
        notif_msg = f"Your {req['leave_type']} request for {req['course_id']} on {req['leave_date']} was {action.upper()} by {req['faculty_name']}."
        if remarks:
            notif_msg += f" Remarks: {remarks}"
        notif_type = 'success' if action == 'Approved' else 'warning'

        execute_db("""
            INSERT INTO notification (student_id, title, message, type)
            VALUES (%s, %s, %s, %s)
        """, (req['student_id'], f"Leave Request {action}", notif_msg, notif_type))

        flash(f"Leave request marked as {action}! Attendance and student record updated.", "success")

    return redirect(url_for('faculty.leave_requests'))

# -------------------------------------------------------------
# FEATURE: DIRECT ACADEMIC WARNING NOTICE TO STUDENT
# -------------------------------------------------------------
@faculty_bp.route('/send-warning', methods=['POST'])
def send_warning():
    faculty_id = session.get('reference_id')
    student_id = request.form.get('student_id')
    course_id = request.form.get('course_id')
    pct = request.form.get('pct', 'Below 75%')

    # Verify authorization
    course = query_db("SELECT course_name FROM course WHERE course_id = %s AND faculty_id = %s",
                      (course_id, faculty_id), one=True)
    if not course:
        flash("Unauthorized.", "danger")
        return redirect(request.referrer or url_for('faculty.dashboard'))

    faculty = query_db("SELECT faculty_name FROM faculty WHERE faculty_id = %s", (faculty_id,), one=True)

    title = f"Official Attendance Warning: {course_id}"
    message = (f"This is an official academic warning from {faculty['faculty_name']} for {course['course_name']} ({course_id}). "
               f"Your current attendance is {pct}%, which is below the mandatory 75% requirement. "
               "You are at risk of exam debarment unless immediate recovery classes are attended.")

    execute_db("""
        INSERT INTO notification (student_id, title, message, type)
        VALUES (%s, %s, %s, 'danger')
    """, (student_id, title, message))

    flash(f"Official warning notice delivered to student {student_id}!", "success")
    return redirect(request.referrer or url_for('faculty.dashboard'))

