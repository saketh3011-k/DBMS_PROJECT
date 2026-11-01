"""
Reports and analytics routes:
Overall, Student-wise, Course-wise, Faculty-wise, Date-wise,
Low Attendance (<75%) reports, JSON chart endpoints, and CSV export.
"""
import io
import csv
from flask import Blueprint, render_template, request, Response, jsonify, flash, redirect, url_for
from auth.auth_service import login_required, role_required
from database.db import query_db, execute_db

report_bp = Blueprint('reports', __name__, url_prefix='/reports')

@report_bp.before_request
@login_required
@role_required('admin')
def check_report_access():
    pass

@report_bp.route('/')
def index():
    report_type = request.args.get('type', 'overall')

    data = {}
    if report_type == 'overall':
        data['summary'] = query_db("""
            SELECT 
                COUNT(*) AS total_entries,
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count,
                SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
                ROUND((SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) AS overall_pct
            FROM attendance
        """, one=True)
        data['by_course'] = query_db("""
            SELECT c.course_id, c.course_name,
                   COUNT(a.attendance_id) AS total,
                   SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present,
                   ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2) AS pct
            FROM course c
            LEFT JOIN attendance a ON c.course_id = a.course_id
            GROUP BY c.course_id, c.course_name
        """)

    elif report_type == 'student_wise':
        search = request.args.get('search', '').strip()
        sql = """
            SELECT 
                s.student_id, s.student_name, s.department,
                c.course_id, c.course_name,
                COUNT(a.attendance_id) AS total_classes,
                SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS attended_classes,
                SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_classes,
                ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2) AS attendance_pct
            FROM enrollment e
            JOIN student s ON e.student_id = s.student_id
            JOIN course c ON e.course_id = c.course_id
            LEFT JOIN attendance a ON e.student_id = a.student_id AND e.course_id = a.course_id
            WHERE 1=1
        """
        params = []
        if search:
            sql += " AND (s.student_id LIKE %s OR s.student_name LIKE %s)"
            like_term = f"%{search}%"
            params.extend([like_term, like_term])
        sql += " GROUP BY s.student_id, s.student_name, s.department, c.course_id, c.course_name ORDER BY s.student_id, c.course_id"
        data['rows'] = query_db(sql, tuple(params))
        data['search'] = search

    elif report_type == 'course_wise':
        data['rows'] = query_db("""
            SELECT c.course_id, c.course_name, c.credits, f.faculty_name,
                   COUNT(DISTINCT a.date) AS classes_held,
                   COUNT(a.attendance_id) AS total_records,
                   SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
                   SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
                   ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2) AS attendance_pct
            FROM course c
            LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
            LEFT JOIN attendance a ON c.course_id = a.course_id
            GROUP BY c.course_id, c.course_name, c.credits, f.faculty_name
            ORDER BY c.course_id
        """)

    elif report_type == 'faculty_wise':
        data['rows'] = query_db("""
            SELECT f.faculty_id, f.faculty_name, f.department,
                   COUNT(DISTINCT c.course_id) AS courses_taught,
                   COUNT(DISTINCT a.date) AS lecture_days,
                   COUNT(a.attendance_id) AS total_marked,
                   SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
                   ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2) AS average_pct
            FROM faculty f
            LEFT JOIN course c ON f.faculty_id = c.faculty_id
            LEFT JOIN attendance a ON c.course_id = a.course_id
            GROUP BY f.faculty_id, f.faculty_name, f.department
            ORDER BY f.faculty_id
        """)

    elif report_type == 'date_wise':
        date_param = request.args.get('date', '').strip()
        sql = """
            SELECT a.date,
                   COUNT(DISTINCT a.course_id) AS courses_count,
                   COUNT(a.attendance_id) AS total_marked,
                   SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
                   SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
                   ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / COUNT(a.attendance_id)) * 100, 2) AS pct
            FROM attendance a
            WHERE 1=1
        """
        params = []
        if date_param:
            sql += " AND a.date = %s"
            params.append(date_param)
        sql += " GROUP BY a.date ORDER BY a.date DESC"
        data['rows'] = query_db(sql, tuple(params))
        data['date_filter'] = date_param

    elif report_type == 'low_attendance':
        data['rows'] = query_db("""
            SELECT 
                s.student_id, s.student_name, s.email, s.phone, s.department,
                c.course_id, c.course_name, f.faculty_name,
                COUNT(a.attendance_id) AS total_classes,
                SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS classes_attended,
                SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS classes_absent,
                ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2) AS attendance_pct,
                GREATEST(0, CEIL((0.75 * COUNT(a.attendance_id) - SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END)) / 0.25)) AS classes_needed_for_75
            FROM enrollment e
            JOIN student s ON e.student_id = s.student_id
            JOIN course c ON e.course_id = c.course_id
            LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
            LEFT JOIN attendance a ON e.student_id = a.student_id AND e.course_id = a.course_id
            GROUP BY s.student_id, s.student_name, s.email, s.phone, s.department, c.course_id, c.course_name, f.faculty_name
            HAVING attendance_pct < 75.0
            ORDER BY attendance_pct ASC
        """)

    return render_template('admin/reports.html', report_type=report_type, data=data)

@report_bp.route('/export-csv')
def export_csv():
    report_type = request.args.get('type', 'low_attendance')
    si = io.StringIO()
    cw = csv.writer(si)

    if report_type == 'low_attendance':
        cw.writerow(['Student ID', 'Student Name', 'Course ID', 'Course Name', 'Total Classes', 'Attended', 'Absent', 'Attendance %', 'Classes Needed for 75%'])
        rows = query_db("""
            SELECT 
                s.student_id, s.student_name, c.course_id, c.course_name,
                COUNT(a.attendance_id) AS total,
                SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS attended,
                SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent,
                ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2) AS pct,
                GREATEST(0, CEIL((0.75 * COUNT(a.attendance_id) - SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END)) / 0.25)) AS needed
            FROM enrollment e
            JOIN student s ON e.student_id = s.student_id
            JOIN course c ON e.course_id = c.course_id
            LEFT JOIN attendance a ON e.student_id = a.student_id AND e.course_id = a.course_id
            GROUP BY s.student_id, s.student_name, c.course_id, c.course_name
            HAVING pct < 75.0
            ORDER BY pct ASC
        """)
        for r in rows:
            cw.writerow([r['student_id'], r['student_name'], r['course_id'], r['course_name'], r['total'], r['attended'], r['absent'], f"{r['pct']}%", r['needed']])

    elif report_type == 'course_wise':
        cw.writerow(['Course ID', 'Course Name', 'Credits', 'Faculty', 'Classes Held', 'Total Entries', 'Present', 'Absent', 'Attendance %'])
        rows = query_db("""
            SELECT c.course_id, c.course_name, c.credits, f.faculty_name,
                   COUNT(DISTINCT a.date) AS classes_held,
                   COUNT(a.attendance_id) AS total_records,
                   SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
                   SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
                   ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2) AS attendance_pct
            FROM course c
            LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
            LEFT JOIN attendance a ON c.course_id = a.course_id
            GROUP BY c.course_id, c.course_name, c.credits, f.faculty_name
        """)
        for r in rows:
            cw.writerow([r['course_id'], r['course_name'], r['credits'], r['faculty_name'], r['classes_held'], r['total_records'], r['present_count'], r['absent_count'], f"{r['attendance_pct']}%"])

    output = Response(si.getvalue(), mimetype='text/csv')
    output.headers["Content-Disposition"] = f"attachment; filename=attendance_{report_type}_report.csv"
    return output

@report_bp.route('/api/chart-data')
def chart_data():
    """
    JSON API endpoint for interactive dashboard charts.
    """
    courses = query_db("""
        SELECT c.course_id, c.course_name,
               SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent
        FROM course c
        LEFT JOIN attendance a ON c.course_id = a.course_id
        GROUP BY c.course_id, c.course_name
        ORDER BY c.course_id
    """)

    dept_stats = query_db("""
        SELECT department, COUNT(student_id) AS count
        FROM student
        GROUP BY department
    """)

    return jsonify({
        'courses': [c['course_id'] for c in courses],
        'present': [int(c['present'] or 0) for c in courses],
        'absent': [int(c['absent'] or 0) for c in courses],
        'departments': [d['department'] for d in dept_stats],
        'department_counts': [int(d['count']) for d in dept_stats]
    })

@report_bp.route('/send-warning', methods=['POST'])
def send_warning():
    student_id = request.form.get('student_id')
    course_id = request.form.get('course_id')
    pct = request.form.get('pct', 'Below 75%')

    title = f"Dean / Academic Office Attendance Notice: {course_id}"
    message = (f"Official Warning from Academic Administration for {course_id}. "
               f"Your recorded attendance is {pct}%. You must immediately meet with your course instructor "
               "and attend mandatory recovery sessions to prevent exam debarment.")

    execute_db("""
        INSERT INTO notification (student_id, title, message, type)
        VALUES (%s, %s, %s, 'danger')
    """, (student_id, title, message))

    flash(f"Official administrative notice delivered to student {student_id}!", "success")
    return redirect(url_for('reports.index', type='low_attendance'))

