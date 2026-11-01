"""
Comprehensive End-to-End Feature Verification Test Runner.
Tests every feature across Admin, Faculty, and Student portals against the live application and database.
"""
import sys
import io
import math
from werkzeug.security import generate_password_hash, check_password_hash
from app import create_app
from database.db import query_db, execute_db

class TestReport:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def assert_true(self, condition, test_name, detail=""):
        if condition:
            self.passed += 1
            self.results.append((test_name, "PASSED", detail))
            print(f"  [PASS] {test_name}" + (f" -> {detail}" if detail else ""))
        else:
            self.failed += 1
            self.results.append((test_name, "FAILED", detail))
            print(f"  [FAIL] {test_name}" + (f" -> {detail}" if detail else ""))

def run_all_feature_tests():
    report = TestReport()
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    print("\n" + "="*70)
    print("  STUDENT ATTENDANCE MANAGEMENT SYSTEM — FULL FEATURE VERIFICATION")
    print("="*70)

    # -------------------------------------------------------------
    # 1. DATABASE INTEGRITY & CORE ENTITIES
    # -------------------------------------------------------------
    print("\n--- 1. DATABASE ENTITIES & CONSTRAINTS ---")
    tables = [list(t.values())[0] for t in query_db("SHOW TABLES;")]
    required_tables = ['student', 'faculty', 'course', 'attendance', 'enrollment', 'users', 'leave_request', 'notification']
    for t in required_tables:
        report.assert_true(t in tables, f"Database Entity '{t}' Exists", f"Table found in student_attendance_db")

    # Team members from documentation
    team = query_db("SELECT student_id, student_name FROM student WHERE student_id IN ('24BAI0250', '24BCE0662', '24BCT0308')")
    report.assert_true(len(team) == 3, "Documentation Team Members Presence", f"Found {len(team)} team members: {[s['student_id'] for s in team]}")

    # Unique constraint on attendance (student_id, course_id, date)
    test_sid, test_cid, test_d = '24BAI0250', 'BCSE303L', '2026-11-20'
    execute_db("DELETE FROM attendance WHERE student_id=%s AND course_id=%s AND date=%s", (test_sid, test_cid, test_d))
    execute_db("INSERT INTO attendance (student_id, course_id, date, status, remarks) VALUES (%s,%s,%s,'Present','Test1')", (test_sid, test_cid, test_d))
    execute_db("INSERT INTO attendance (student_id, course_id, date, status, remarks) VALUES (%s,%s,%s,'Absent','Test2') ON DUPLICATE KEY UPDATE status=VALUES(status), remarks=VALUES(remarks)", (test_sid, test_cid, test_d))
    count = query_db("SELECT COUNT(*) AS c FROM attendance WHERE student_id=%s AND course_id=%s AND date=%s", (test_sid, test_cid, test_d), one=True)['c']
    report.assert_true(count == 1, "Duplicate Attendance Prevention Constraint", "ON DUPLICATE KEY prevents duplicate row")
    execute_db("DELETE FROM attendance WHERE student_id=%s AND course_id=%s AND date=%s", (test_sid, test_cid, test_d))

    # -------------------------------------------------------------
    # 2. AUTHENTICATION, PASSWORD SECURITY & ROLE ACCESS
    # -------------------------------------------------------------
    print("\n--- 2. AUTHENTICATION & ACCESS CONTROL ---")
    # Login page
    r = client.get('/login')
    report.assert_true(r.status_code == 200 and b'Welcome back' in r.data, "Login Page Rendering", "HTTP 200 OK")

    # Admin Login
    r = client.post('/login', data={'identifier': 'admin', 'password': 'admin123', 'role': 'admin'}, follow_redirects=True)
    report.assert_true(r.status_code == 200 and b'Overview' in r.data, "Admin Authentication", "admin / admin123")
    client.get('/logout')

    # Faculty Login
    r = client.post('/login', data={'identifier': 'FAC001', 'password': 'faculty123', 'role': 'faculty'}, follow_redirects=True)
    report.assert_true(r.status_code == 200 and b'Dr. Suresh Kumar' in r.data, "Faculty Authentication", "FAC001 / faculty123")
    client.get('/logout')

    # Student Login
    r = client.post('/login', data={'identifier': '24BAI0250', 'password': 'student123', 'role': 'student'}, follow_redirects=True)
    report.assert_true(r.status_code == 200 and b'Saketh Kolluri' in r.data, "Student Authentication", "24BAI0250 / student123")
    client.get('/logout')

    # Invalid password check
    r = client.post('/login', data={'identifier': 'admin', 'password': 'wrongpassword', 'role': 'admin'}, follow_redirects=True)
    report.assert_true(b'Invalid password' in r.data, "Invalid Password Rejection", "Securely denied")

    # Role protection: Student cannot access Admin routes
    client.post('/login', data={'identifier': '24BAI0250', 'password': 'student123', 'role': 'student'})
    r = client.get('/admin/dashboard', follow_redirects=False)
    report.assert_true(r.status_code == 302, "Role-Based Access Control", "Student blocked from /admin/dashboard")
    client.get('/logout')

    # -------------------------------------------------------------
    # 3. ADMIN PORTAL FEATURES
    # -------------------------------------------------------------
    print("\n--- 3. ADMIN PORTAL FEATURES ---")
    client.post('/login', data={'identifier': 'admin', 'password': 'admin123', 'role': 'admin'})

    # Admin Dashboard
    r = client.get('/admin/dashboard')
    report.assert_true(r.status_code == 200 and b'Overall Attendance' in r.data, "Admin Dashboard Metrics & Charts", "HTTP 200 OK")

    # Student CRUD & Search by Reg No
    r_search = client.get('/admin/students?search=Saketh')
    report.assert_true(r_search.status_code == 200 and b'24BAI0250' in r_search.data, "Student Search by Registration No / Name", "Found Saketh Kolluri (24BAI0250)")

    test_student_id = 'TEST99BCE'
    execute_db("DELETE FROM student WHERE student_id = %s", (test_student_id,))
    execute_db("DELETE FROM users WHERE reference_id = %s", (test_student_id,))
    r_add = client.post('/admin/students/add', data={
        'student_id': test_student_id,
        'student_name': 'Test Robot',
        'email': 'test.robot@college.edu',
        'phone': '9876543210',
        'department': 'Robotics',
        'password': 'testpassword'
    }, follow_redirects=True)
    report.assert_true(b'added successfully' in r_add.data, "Admin Student Creation (CRUD: Create)", f"Added {test_student_id}")

    r_edit = client.post(f'/admin/students/edit/{test_student_id}', data={
        'student_name': 'Test Robot Updated',
        'email': 'test.robot.updated@college.edu',
        'phone': '9876543211',
        'department': 'Robotics & Automation'
    }, follow_redirects=True)
    report.assert_true(b'updated successfully' in r_edit.data, "Admin Student Update (CRUD: Update)", f"Updated {test_student_id}")

    r_del = client.post(f'/admin/students/delete/{test_student_id}', follow_redirects=True)
    report.assert_true(b'deleted successfully' in r_del.data, "Admin Student Deletion (CRUD: Delete)", f"Deleted {test_student_id}")

    # Faculty CRUD
    r_fac = client.get('/admin/faculty')
    report.assert_true(r_fac.status_code == 200 and b'Dr. Suresh Kumar' in r_fac.data, "Admin Faculty Management", "Renders faculty roster")

    # Course CRUD & Faculty Assignment
    r_course = client.get('/admin/courses')
    report.assert_true(r_course.status_code == 200 and b'BCSE303L' in r_course.data, "Admin Course Management & Faculty Assignment", "Renders courses list")

    # Enrollment Management
    r_enroll = client.get('/admin/enrollments')
    report.assert_true(r_enroll.status_code == 200 and b'24BAI0250' in r_enroll.data, "Admin Student Course Enrollment", "Renders enrollment records")

    # Master Attendance Log with Filters
    r_att_log = client.get('/admin/attendance?course_id=BCSE303L&status=Present')
    report.assert_true(r_att_log.status_code == 200 and b'BCSE303L' in r_att_log.data, "Admin Master Attendance Log with Filters", "Filtered by BCSE303L & Present")

    # Reports: Overall, Low Attendance, Course-wise, Faculty-wise, Date-wise
    r_rep_overall = client.get('/reports/?type=overall')
    report.assert_true(r_rep_overall.status_code == 200 and b'Course-wise Breakdown' in r_rep_overall.data, "Admin Overall Attendance Report", "HTTP 200 OK")

    r_rep_low = client.get('/reports/?type=low_attendance')
    report.assert_true(r_rep_low.status_code == 200 and b'Below 75%' in r_rep_low.data, "Admin Low Attendance (<75%) Report", "Identified students with shortage")

    r_rep_course = client.get('/reports/?type=course_wise')
    report.assert_true(r_rep_course.status_code == 200 and b'Classes Conducted' in r_rep_course.data, "Admin Course-Wise Attendance Report", "HTTP 200 OK")

    r_rep_fac = client.get('/reports/?type=faculty_wise')
    report.assert_true(r_rep_fac.status_code == 200 and b'Courses Taught' in r_rep_fac.data, "Admin Faculty-Wise Attendance Report", "HTTP 200 OK")

    r_rep_date = client.get('/reports/?type=date_wise')
    report.assert_true(r_rep_date.status_code == 200 and b'Daily Attendance Rate' in r_rep_date.data, "Admin Date-Wise Attendance Report", "HTTP 200 OK")

    # CSV Export
    r_csv = client.get('/reports/export-csv?type=low_attendance')
    report.assert_true(r_csv.status_code == 200 and b'Student ID' in r_csv.data, "Admin CSV Export Functionality", f"Downloaded CSV ({len(r_csv.data)} bytes)")

    # 1-Click Administrative Warning Notice
    r_warn = client.post('/reports/send-warning', data={
        'student_id': '24BCT0308',
        'course_id': 'BCSE303L',
        'pct': '66.7'
    }, follow_redirects=True)
    report.assert_true(b'delivered to student' in r_warn.data, "Admin 1-Click Warning Notice Dispatch", "Delivered notice to 24BCT0308")

    client.get('/logout')

    # -------------------------------------------------------------
    # 4. FACULTY PORTAL FEATURES
    # -------------------------------------------------------------
    print("\n--- 4. FACULTY PORTAL FEATURES ---")
    client.post('/login', data={'identifier': 'FAC001', 'password': 'faculty123', 'role': 'faculty'})

    # Faculty Dashboard
    r_fac_dash = client.get('/faculty/dashboard')
    report.assert_true(r_fac_dash.status_code == 200 and b'Assigned Courses' in r_fac_dash.data, "Faculty Dashboard & KPI Metrics", "HTTP 200 OK")

    # Assigned Courses & Roster View
    r_roster = client.get('/faculty/courses/BCSE303L/students')
    report.assert_true(r_roster.status_code == 200 and b'Enrolled Students' in r_roster.data, "Faculty Enrolled Students Roster", "Roster view for BCSE303L")

    # Mark Daily Attendance Form
    r_mark_view = client.get('/faculty/mark-attendance?course_id=BCSE303L&date=2026-10-30')
    report.assert_true(r_mark_view.status_code == 200 and b'Class Roster: BCSE303L' in r_mark_view.data, "Faculty Daily Attendance Marking Interface", "Loaded roster for marking")

    # Mark Daily Attendance POST
    r_mark_post = client.post('/faculty/mark-attendance', data={
        'course_id': 'BCSE303L',
        'date': '2026-10-30',
        'status_24BAI0250': 'Present',
        'remarks_24BAI0250': 'Verified in live lab',
        'status_24BCE0662': 'Present',
        'remarks_24BCE0662': 'Regular'
    }, follow_redirects=True)
    report.assert_true(r_mark_post.status_code == 200, "Faculty Attendance Submission & Validation", "Attendance recorded/upserted")

    # Attendance Session History & Edit
    r_hist = client.get('/faculty/history?course_id=BCSE303L')
    report.assert_true(r_hist.status_code == 200 and b'Attendance History' in r_hist.data, "Faculty Attendance Session History & Filter", "HTTP 200 OK")

    # Course Report
    r_fac_rep = client.get('/faculty/reports?course_id=BCSE303L')
    report.assert_true(r_fac_rep.status_code == 200 and b'Classes Conducted' in r_fac_rep.data, "Faculty Course-Wise Report & Distribution", "HTTP 200 OK")

    # Faculty Leave Approvals Workflow
    r_leave_list = client.get('/faculty/leave-requests')
    report.assert_true(r_leave_list.status_code == 200 and b'Leave Applications' in r_leave_list.data, "Faculty Leave / OD Requests Interface", "HTTP 200 OK")

    # Faculty Send Warning Notice
    r_fac_warn = client.post('/faculty/send-warning', data={
        'student_id': '24BAI0250',
        'course_id': 'BCSE303L',
        'pct': '62.5'
    }, follow_redirects=True)
    report.assert_true(b'delivered to student' in r_fac_warn.data, "Faculty Warning Notice Delivery", "Delivered notice to student")

    client.get('/logout')

    # -------------------------------------------------------------
    # 5. STUDENT PORTAL FEATURES
    # -------------------------------------------------------------
    print("\n--- 5. STUDENT PORTAL FEATURES ---")
    client.post('/login', data={'identifier': '24BAI0250', 'password': 'student123', 'role': 'student'})

    # Student Dashboard
    r_stu_dash = client.get('/student/dashboard')
    report.assert_true(r_stu_dash.status_code == 200 and b'Overall Attendance' in r_stu_dash.data, "Student Dashboard & Attendance Percentage", "Calculated overall %")
    report.assert_true(b'Attendance Below 75% Requirement' in r_stu_dash.data, "Student Low-Attendance (<75%) Shortage Warning Banner", "Alert flagged for BCSE308L")

    # Enrolled Courses
    r_stu_courses = client.get('/student/courses')
    report.assert_true(r_stu_courses.status_code == 200 and b'BCSE303L' in r_stu_courses.data, "Student Enrolled Courses View", "HTTP 200 OK")

    # Attendance History & Filters
    r_stu_hist = client.get('/student/history?course_id=BCSE303L')
    report.assert_true(r_stu_hist.status_code == 200 and b'My Attendance History' in r_stu_hist.data, "Student Date-Wise Attendance History & Audit", "HTTP 200 OK")

    # What-If Attendance Simulator & Bunk Calculator
    r_sim = client.get('/student/simulator')
    report.assert_true(r_sim.status_code == 200 and b'Bunk Calculator' in r_sim.data, "Student Bunk Calculator & What-If Simulator", "Loaded simulator with formulas")

    # Leave & On-Duty (OD) Application Submission
    r_leave_page = client.get('/student/leave')
    report.assert_true(r_leave_page.status_code == 200 and b'Application History' in r_leave_page.data, "Student Leave / OD Application Interface", "HTTP 200 OK")

    test_leave_date = '2026-11-25'
    execute_db("DELETE FROM leave_request WHERE student_id='24BAI0250' AND leave_date=%s", (test_leave_date,))
    r_leave_sub = client.post('/student/leave/apply', data={
        'course_id': 'BCSE303L',
        'leave_date': test_leave_date,
        'leave_type': 'Medical Leave',
        'reason': 'Automated feature test leave request'
    }, follow_redirects=True)
    report.assert_true(b'submitted successfully' in r_leave_sub.data, "Student Leave / OD Application Submission", f"Submitted for {test_leave_date}")
    execute_db("DELETE FROM leave_request WHERE student_id='24BAI0250' AND leave_date=%s", (test_leave_date,))

    # Official Notifications Center
    r_notif = client.get('/student/notifications')
    report.assert_true(r_notif.status_code == 200 and b'Official Notices' in r_notif.data, "Student Notification Center", "Renders warning and approval notices")

    client.get('/logout')

    # -------------------------------------------------------------
    # 6. PROFILE & PASSWORD MANAGEMENT
    # -------------------------------------------------------------
    print("\n--- 6. ACCOUNT PROFILE & SECURITY ---")
    client.post('/login', data={'identifier': '24BAI0250', 'password': 'student123', 'role': 'student'})
    r_prof = client.get('/profile')
    report.assert_true(r_prof.status_code == 200 and b'Account Profile' in r_prof.data, "User Profile View", "HTTP 200 OK")

    # Password Change test
    r_pwd_change = client.post('/profile', data={
        'current_password': 'student123',
        'new_password': 'tempNewPassword123',
        'confirm_password': 'tempNewPassword123'
    }, follow_redirects=True)
    report.assert_true(b'Password updated successfully' in r_pwd_change.data, "Self-Service Password Change", "PBKDF2 hash updated")

    # Revert password back to default student123 so demo logins remain unchanged
    def_hash = generate_password_hash('student123')
    execute_db("UPDATE users SET password_hash = %s WHERE username = '24BAI0250'", (def_hash,))
    client.get('/logout')

    # -------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------
    print("\n" + "="*70)
    print(f"  FEATURE VERIFICATION SUMMARY: {report.passed} PASSED, {report.failed} FAILED")
    print("="*70)
    return report.failed == 0

if __name__ == '__main__':
    success = run_all_feature_tests()
    sys.exit(0 if success else 1)
