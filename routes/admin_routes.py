"""
Admin routes for managing students, faculty, courses, enrollments,
attendance oversight, and high-level reports.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from auth.auth_service import login_required, role_required, create_user_account
from database.db import query_db, execute_db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
@role_required('admin')
def check_admin():
    pass

@admin_bp.route('/dashboard')
def dashboard():
    # Key Metrics
    student_count = query_db("SELECT COUNT(*) AS count FROM student", one=True)['count']
    faculty_count = query_db("SELECT COUNT(*) AS count FROM faculty", one=True)['count']
    course_count = query_db("SELECT COUNT(*) AS count FROM course", one=True)['count']
    attendance_count = query_db("SELECT COUNT(*) AS count FROM attendance", one=True)['count']

    # Overall Attendance %
    overall_stat = query_db("""
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present,
            SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent
        FROM attendance
    """, one=True)
    
    total_entries = int(overall_stat['total'] or 0)
    total_present = int(overall_stat['present'] or 0)
    total_absent = int(overall_stat['absent'] or 0)
    overall_pct = round((total_present / total_entries * 100), 2) if total_entries > 0 else 0.0

    # Low attendance count (<75%)
    low_att_records = query_db("""
        SELECT s.student_id, c.course_id,
               COUNT(a.attendance_id) AS total,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present
        FROM enrollment e
        JOIN student s ON e.student_id = s.student_id
        JOIN course c ON e.course_id = c.course_id
        LEFT JOIN attendance a ON e.student_id = a.student_id AND e.course_id = a.course_id
        GROUP BY s.student_id, c.course_id
        HAVING (present / NULLIF(total, 0) * 100) < 75.0
    """)
    low_attendance_count = len(low_att_records)

    # Course-wise statistics for chart
    course_stats = query_db("""
        SELECT c.course_id, c.course_name,
               COUNT(a.attendance_id) AS total_marked,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
               ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 1) AS pct
        FROM course c
        LEFT JOIN attendance a ON c.course_id = a.course_id
        GROUP BY c.course_id, c.course_name
        ORDER BY c.course_id
    """)

    # Recent attendance activities
    recent_attendance = query_db("""
        SELECT a.attendance_id, a.student_id, s.student_name, a.course_id, c.course_name, a.date, a.status, a.remarks
        FROM attendance a
        JOIN student s ON a.student_id = s.student_id
        JOIN course c ON a.course_id = c.course_id
        ORDER BY a.date DESC, a.attendance_id DESC
        LIMIT 10
    """)

    return render_template('admin/dashboard.html',
                           student_count=student_count,
                           faculty_count=faculty_count,
                           course_count=course_count,
                           attendance_count=attendance_count,
                           overall_pct=overall_pct,
                           total_present=total_present,
                           total_absent=total_absent,
                           low_attendance_count=low_attendance_count,
                           course_stats=course_stats,
                           recent_attendance=recent_attendance)

# -------------------------------------------------------------
# STUDENT CRUD & SEARCH BY REGISTRATION NUMBER
# -------------------------------------------------------------
@admin_bp.route('/students', methods=['GET'])
def students():
    search_query = request.args.get('search', '').strip()
    dept_filter = request.args.get('dept', '').strip()

    sql = "SELECT * FROM student WHERE 1=1"
    params = []

    if search_query:
        sql += " AND (student_id LIKE %s OR student_name LIKE %s OR email LIKE %s)"
        like_term = f"%{search_query}%"
        params.extend([like_term, like_term, like_term])

    if dept_filter:
        sql += " AND department = %s"
        params.append(dept_filter)

    sql += " ORDER BY student_id ASC"
    student_list = query_db(sql, tuple(params))
    departments = query_db("SELECT DISTINCT department FROM student ORDER BY department")

    return render_template('admin/students.html',
                           students=student_list,
                           departments=departments,
                           search=search_query,
                           selected_dept=dept_filter)

@admin_bp.route('/students/add', methods=['POST'])
def add_student():
    student_id = request.form.get('student_id', '').strip().upper()
    student_name = request.form.get('student_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    department = request.form.get('department', '').strip()
    password = request.form.get('password', '').strip() or 'student123'

    if not student_id or not student_name or not email or not department:
        flash("Please fill in all required fields.", "danger")
        return redirect(url_for('admin.students'))

    # Check for existing student_id or email
    existing = query_db("SELECT student_id, email FROM student WHERE student_id = %s OR email = %s",
                        (student_id, email), one=True)
    if existing:
        flash(f"Student ID '{student_id}' or Email '{email}' is already registered.", "danger")
        return redirect(url_for('admin.students'))

    try:
        execute_db("""
            INSERT INTO student (student_id, student_name, email, phone, department)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, student_name, email, phone, department))

        # Create user account for login
        create_user_account(username=student_id, password=password, role='student',
                            reference_id=student_id, full_name=student_name, email=email)

        flash(f"Student '{student_name}' ({student_id}) added successfully!", "success")
    except Exception as e:
        flash(f"Failed to add student: {str(e)}", "danger")

    return redirect(url_for('admin.students'))

@admin_bp.route('/students/edit/<student_id>', methods=['POST'])
def edit_student(student_id):
    student_name = request.form.get('student_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    department = request.form.get('department', '').strip()

    try:
        execute_db("""
            UPDATE student 
            SET student_name = %s, email = %s, phone = %s, department = %s
            WHERE student_id = %s
        """, (student_name, email, phone, department, student_id))

        execute_db("""
            UPDATE users
            SET full_name = %s, email = %s
            WHERE reference_id = %s AND role = 'student'
        """, (student_name, email, student_id))

        flash(f"Student '{student_id}' updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update student: {str(e)}", "danger")

    return redirect(url_for('admin.students'))

@admin_bp.route('/students/delete/<student_id>', methods=['POST'])
def delete_student(student_id):
    try:
        execute_db("DELETE FROM student WHERE student_id = %s", (student_id,))
        execute_db("DELETE FROM users WHERE reference_id = %s AND role = 'student'", (student_id,))
        flash(f"Student '{student_id}' and related records deleted successfully.", "success")
    except Exception as e:
        flash(f"Failed to delete student: {str(e)}", "danger")
    return redirect(url_for('admin.students'))

# -------------------------------------------------------------
# FACULTY CRUD
# -------------------------------------------------------------
@admin_bp.route('/faculty', methods=['GET'])
def faculty():
    search_query = request.args.get('search', '').strip()
    sql = """
        SELECT f.*, COUNT(c.course_id) AS course_count
        FROM faculty f
        LEFT JOIN course c ON f.faculty_id = c.faculty_id
    """
    params = []
    if search_query:
        sql += " WHERE (f.faculty_id LIKE %s OR f.faculty_name LIKE %s OR f.email LIKE %s)"
        like_term = f"%{search_query}%"
        params.extend([like_term, like_term, like_term])
    sql += " GROUP BY f.faculty_id ORDER BY f.faculty_id ASC"

    faculty_list = query_db(sql, tuple(params))
    return render_template('admin/faculty.html', faculty=faculty_list, search=search_query)

@admin_bp.route('/faculty/add', methods=['POST'])
def add_faculty():
    faculty_id = request.form.get('faculty_id', '').strip().upper()
    faculty_name = request.form.get('faculty_name', '').strip()
    email = request.form.get('email', '').strip()
    department = request.form.get('department', '').strip()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '').strip() or 'faculty123'

    if not faculty_id or not faculty_name or not email or not department:
        flash("Please fill in all required fields.", "danger")
        return redirect(url_for('admin.faculty'))

    existing = query_db("SELECT faculty_id FROM faculty WHERE faculty_id = %s OR email = %s",
                        (faculty_id, email), one=True)
    if existing:
        flash("Faculty ID or Email already exists.", "danger")
        return redirect(url_for('admin.faculty'))

    try:
        execute_db("""
            INSERT INTO faculty (faculty_id, faculty_name, email, department, phone)
            VALUES (%s, %s, %s, %s, %s)
        """, (faculty_id, faculty_name, email, department, phone))

        create_user_account(username=faculty_id, password=password, role='faculty',
                            reference_id=faculty_id, full_name=faculty_name, email=email)

        flash(f"Faculty '{faculty_name}' ({faculty_id}) added successfully!", "success")
    except Exception as e:
        flash(f"Failed to add faculty: {str(e)}", "danger")

    return redirect(url_for('admin.faculty'))

@admin_bp.route('/faculty/edit/<faculty_id>', methods=['POST'])
def edit_faculty(faculty_id):
    faculty_name = request.form.get('faculty_name', '').strip()
    email = request.form.get('email', '').strip()
    department = request.form.get('department', '').strip()
    phone = request.form.get('phone', '').strip()

    try:
        execute_db("""
            UPDATE faculty
            SET faculty_name = %s, email = %s, department = %s, phone = %s
            WHERE faculty_id = %s
        """, (faculty_name, email, department, phone, faculty_id))

        execute_db("""
            UPDATE users
            SET full_name = %s, email = %s
            WHERE reference_id = %s AND role = 'faculty'
        """, (faculty_name, email, faculty_id))

        flash(f"Faculty '{faculty_id}' updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update faculty: {str(e)}", "danger")

    return redirect(url_for('admin.faculty'))

@admin_bp.route('/faculty/delete/<faculty_id>', methods=['POST'])
def delete_faculty(faculty_id):
    try:
        execute_db("DELETE FROM faculty WHERE faculty_id = %s", (faculty_id,))
        execute_db("DELETE FROM users WHERE reference_id = %s AND role = 'faculty'", (faculty_id,))
        flash(f"Faculty '{faculty_id}' deleted successfully.", "success")
    except Exception as e:
        flash(f"Failed to delete faculty: {str(e)}", "danger")
    return redirect(url_for('admin.faculty'))

# -------------------------------------------------------------
# COURSE MANAGEMENT & ASSIGN FACULTY
# -------------------------------------------------------------
@admin_bp.route('/courses', methods=['GET'])
def courses():
    course_list = query_db("""
        SELECT c.*, f.faculty_name, COUNT(e.student_id) AS enrolled_students
        FROM course c
        LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
        LEFT JOIN enrollment e ON c.course_id = e.course_id
        GROUP BY c.course_id, c.course_name, c.credits, c.faculty_id, c.department, c.created_at, f.faculty_name
        ORDER BY c.course_id ASC
    """)
    faculty_list = query_db("SELECT faculty_id, faculty_name, department FROM faculty ORDER BY faculty_name")
    return render_template('admin/courses.html', courses=course_list, faculty=faculty_list)

@admin_bp.route('/courses/add', methods=['POST'])
def add_course():
    course_id = request.form.get('course_id', '').strip().upper()
    course_name = request.form.get('course_name', '').strip()
    credits = int(request.form.get('credits', 3))
    faculty_id = request.form.get('faculty_id', '').strip() or None
    department = request.form.get('department', '').strip()

    if not course_id or not course_name or not department:
        flash("Please provide Course ID, Name, and Department.", "danger")
        return redirect(url_for('admin.courses'))

    existing = query_db("SELECT course_id FROM course WHERE course_id = %s", (course_id,), one=True)
    if existing:
        flash(f"Course ID '{course_id}' already exists.", "danger")
        return redirect(url_for('admin.courses'))

    try:
        execute_db("""
            INSERT INTO course (course_id, course_name, credits, faculty_id, department)
            VALUES (%s, %s, %s, %s, %s)
        """, (course_id, course_name, credits, faculty_id, department))
        flash(f"Course '{course_name}' ({course_id}) created successfully!", "success")
    except Exception as e:
        flash(f"Failed to add course: {str(e)}", "danger")

    return redirect(url_for('admin.courses'))

@admin_bp.route('/courses/edit/<course_id>', methods=['POST'])
def edit_course(course_id):
    course_name = request.form.get('course_name', '').strip()
    credits = int(request.form.get('credits', 3))
    faculty_id = request.form.get('faculty_id', '').strip() or None
    department = request.form.get('department', '').strip()

    try:
        execute_db("""
            UPDATE course
            SET course_name = %s, credits = %s, faculty_id = %s, department = %s
            WHERE course_id = %s
        """, (course_name, credits, faculty_id, department, course_id))
        flash(f"Course '{course_id}' updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update course: {str(e)}", "danger")

    return redirect(url_for('admin.courses'))

@admin_bp.route('/courses/delete/<course_id>', methods=['POST'])
def delete_course(course_id):
    try:
        execute_db("DELETE FROM course WHERE course_id = %s", (course_id,))
        flash(f"Course '{course_id}' deleted successfully.", "success")
    except Exception as e:
        flash(f"Failed to delete course: {str(e)}", "danger")
    return redirect(url_for('admin.courses'))

# -------------------------------------------------------------
# ENROLLMENTS MANAGEMENT
# -------------------------------------------------------------
@admin_bp.route('/enrollments', methods=['GET'])
def enrollments():
    course_filter = request.args.get('course_id', '').strip()
    student_filter = request.args.get('student_id', '').strip()

    sql = """
        SELECT e.enrollment_id, e.student_id, s.student_name, s.department AS student_dept,
               e.course_id, c.course_name, f.faculty_name, e.semester, e.enrollment_date
        FROM enrollment e
        JOIN student s ON e.student_id = s.student_id
        JOIN course c ON e.course_id = c.course_id
        LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
        WHERE 1=1
    """
    params = []
    if course_filter:
        sql += " AND e.course_id = %s"
        params.append(course_filter)
    if student_filter:
        sql += " AND e.student_id = %s"
        params.append(student_filter)

    sql += " ORDER BY e.course_id ASC, e.student_id ASC"
    enrollment_list = query_db(sql, tuple(params))

    all_students = query_db("SELECT student_id, student_name FROM student ORDER BY student_id")
    all_courses = query_db("SELECT course_id, course_name FROM course ORDER BY course_id")

    return render_template('admin/enrollments.html',
                           enrollments=enrollment_list,
                           students=all_students,
                           courses=all_courses,
                           selected_course=course_filter,
                           selected_student=student_filter)

@admin_bp.route('/enrollments/add', methods=['POST'])
def add_enrollment():
    student_id = request.form.get('student_id', '').strip()
    course_id = request.form.get('course_id', '').strip()
    semester = request.form.get('semester', 'Fall 2026').strip()

    if not student_id or not course_id:
        flash("Student and Course must be selected.", "danger")
        return redirect(url_for('admin.enrollments'))

    existing = query_db("SELECT enrollment_id FROM enrollment WHERE student_id = %s AND course_id = %s",
                        (student_id, course_id), one=True)
    if existing:
        flash("This student is already enrolled in this course.", "warning")
        return redirect(url_for('admin.enrollments'))

    try:
        execute_db("""
            INSERT INTO enrollment (student_id, course_id, semester, enrollment_date)
            VALUES (%s, %s, %s, CURDATE())
        """, (student_id, course_id, semester))
        flash(f"Student {student_id} enrolled in {course_id} successfully.", "success")
    except Exception as e:
        flash(f"Enrollment failed: {str(e)}", "danger")

    return redirect(url_for('admin.enrollments'))

@admin_bp.route('/enrollments/delete/<int:enrollment_id>', methods=['POST'])
def delete_enrollment(enrollment_id):
    try:
        execute_db("DELETE FROM enrollment WHERE enrollment_id = %s", (enrollment_id,))
        flash("Enrollment removed successfully.", "success")
    except Exception as e:
        flash(f"Failed to remove enrollment: {str(e)}", "danger")
    return redirect(url_for('admin.enrollments'))

# -------------------------------------------------------------
# ALL ATTENDANCE RECORDS & MONITORING
# -------------------------------------------------------------
@admin_bp.route('/attendance', methods=['GET'])
def attendance():
    course_filter = request.args.get('course_id', '').strip()
    student_filter = request.args.get('student_id', '').strip()
    date_filter = request.args.get('date', '').strip()
    status_filter = request.args.get('status', '').strip()

    sql = """
        SELECT a.attendance_id, a.student_id, s.student_name, a.course_id, c.course_name,
               a.date, a.status, a.remarks, f.faculty_name
        FROM attendance a
        JOIN student s ON a.student_id = s.student_id
        JOIN course c ON a.course_id = c.course_id
        LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
        WHERE 1=1
    """
    params = []
    if course_filter:
        sql += " AND a.course_id = %s"
        params.append(course_filter)
    if student_filter:
        sql += " AND (a.student_id LIKE %s OR s.student_name LIKE %s)"
        like_term = f"%{student_filter}%"
        params.extend([like_term, like_term])
    if date_filter:
        sql += " AND a.date = %s"
        params.append(date_filter)
    if status_filter:
        sql += " AND a.status = %s"
        params.append(status_filter)

    sql += " ORDER BY a.date DESC, a.course_id ASC, a.student_id ASC LIMIT 250"
    records = query_db(sql, tuple(params))

    courses = query_db("SELECT course_id, course_name FROM course ORDER BY course_id")

    return render_template('admin/attendance.html',
                           records=records,
                           courses=courses,
                           selected_course=course_filter,
                           student_search=student_filter,
                           selected_date=date_filter,
                           selected_status=status_filter)

@admin_bp.route('/attendance/delete/<int:attendance_id>', methods=['POST'])
def delete_attendance(attendance_id):
    try:
        execute_db("DELETE FROM attendance WHERE attendance_id = %s", (attendance_id,))
        flash("Attendance entry deleted successfully.", "success")
    except Exception as e:
        flash(f"Failed to delete attendance: {str(e)}", "danger")
    return redirect(url_for('admin.attendance'))
