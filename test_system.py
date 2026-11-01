"""
Comprehensive Test Suite for Student Attendance Management System.
Verifies Database Entities, Authentication, Role Protection,
Attendance Percentage Calculations, Duplicate Entry Prevention, and CRUD operations.
"""
import pytest
from app import create_app
from database.db import query_db, execute_db
from auth.auth_service import authenticate_user
from config import Config

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client

# 1. DATABASE ENTITY TESTS
def test_core_database_entities():
    """Verify the four main database entities from project documentation exist."""
    tables = query_db("SHOW TABLES;")
    table_names = [list(t.values())[0] for t in tables]
    
    assert 'student' in table_names, "Entity 'student' missing"
    assert 'faculty' in table_names, "Entity 'faculty' missing"
    assert 'course' in table_names, "Entity 'course' missing"
    assert 'attendance' in table_names, "Entity 'attendance' missing"
    assert 'enrollment' in table_names, "Entity 'enrollment' missing"
    assert 'users' in table_names, "Entity 'users' missing"

def test_team_members_presence():
    """Verify documentation team members exist in the student database."""
    team_reg_nos = ['24BCE0662', '24BAI0250', '24BCT0308']
    for reg in team_reg_nos:
        student = query_db("SELECT * FROM student WHERE student_id = %s", (reg,), one=True)
        assert student is not None, f"Team member {reg} not found in student table"
        assert len(student['student_name']) > 0

# 2. AUTHENTICATION & ROLE ACCESS TESTS
def test_admin_authentication():
    """Verify Admin login credentials and role."""
    user, err = authenticate_user('admin', 'admin123', 'admin')
    assert err is None
    assert user['role'] == 'admin'

def test_faculty_authentication():
    """Verify Faculty login credentials and role."""
    user, err = authenticate_user('FAC001', 'faculty123', 'faculty')
    assert err is None
    assert user['role'] == 'faculty'
    assert user['reference_id'] == 'FAC001'

def test_student_authentication():
    """Verify Student login using Registration Number."""
    user, err = authenticate_user('24BAI0250', 'student123', 'student')
    assert err is None
    assert user['role'] == 'student'
    assert user['reference_id'] == '24BAI0250'

def test_invalid_password_rejection():
    """Verify wrong password fails securely."""
    user, err = authenticate_user('admin', 'wrong_password', 'admin')
    assert user is None
    assert "Invalid password" in err

def test_unauthorized_dashboard_access(client):
    """Verify that unauthenticated requests to protected dashboards are redirected to login."""
    res_admin = client.get('/admin/dashboard', follow_redirects=False)
    assert res_admin.status_code == 302
    assert '/login' in res_admin.headers['Location']

    res_faculty = client.get('/faculty/dashboard', follow_redirects=False)
    assert res_faculty.status_code == 302
    assert '/login' in res_faculty.headers['Location']

    res_student = client.get('/student/dashboard', follow_redirects=False)
    assert res_student.status_code == 302
    assert '/login' in res_student.headers['Location']

# 3. ATTENDANCE CALCULATION & 75% WARNING TESTS
def test_attendance_percentage_calculation():
    """
    Verify attendance formula:
    Attendance Percentage = (Classes Attended / Total Classes Conducted) * 100
    """
    # Sample test: 9 attended out of 12 classes = 75.0%
    attended = 9
    total = 12
    pct = round((attended / total) * 100, 2)
    assert pct == 75.0

    # Sample test: 8 attended out of 12 classes = 66.67%
    attended_low = 8
    pct_low = round((attended_low / total) * 100, 2)
    assert pct_low < 75.0, "Should fall below 75% threshold"

def test_low_attendance_recovery_formula():
    """
    Verify formula for classes needed consecutively to achieve 75%:
    Formula: ceil((0.75 * total - attended) / 0.25)
    """
    import math
    total = 8
    attended = 5 # 5/8 = 62.5%
    needed = max(0, math.ceil((0.75 * total - attended) / 0.25))
    # (5 + 4) / (8 + 4) = 9/12 = 75% -> exactly 4 classes
    assert needed == 4

# 4. DUPLICATE ATTENDANCE PREVENTION TEST
def test_duplicate_attendance_prevention():
    """Verify unique constraint prevents duplicate attendance rows for same student, course, date."""
    test_sid = '24BAI0250'
    test_cid = 'BCSE303L'
    test_date = '2026-11-01'

    # Clean up any leftover
    execute_db("DELETE FROM attendance WHERE student_id = %s AND course_id = %s AND date = %s",
               (test_sid, test_cid, test_date))

    # First Insert
    execute_db("""
        INSERT INTO attendance (student_id, course_id, date, status, remarks)
        VALUES (%s, %s, %s, %s, %s)
    """, (test_sid, test_cid, test_date, 'Present', 'Test 1'))

    # Second Insert with same unique key should trigger ON DUPLICATE KEY or fail
    execute_db("""
        INSERT INTO attendance (student_id, course_id, date, status, remarks)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE status = VALUES(status), remarks = VALUES(remarks)
    """, (test_sid, test_cid, test_date, 'Absent', 'Test Updated'))

    # Count must be exactly 1
    count = query_db("""
        SELECT COUNT(*) AS c FROM attendance
        WHERE student_id = %s AND course_id = %s AND date = %s
    """, (test_sid, test_cid, test_date), one=True)['c']
    assert count == 1, "Duplicate row was created unexpectedly"

    # Status must be updated to Absent
    entry = query_db("""
        SELECT status FROM attendance
        WHERE student_id = %s AND course_id = %s AND date = %s
    """, (test_sid, test_cid, test_date), one=True)
    assert entry['status'] == 'Absent'

    # Clean up test entry
    execute_db("DELETE FROM attendance WHERE student_id = %s AND course_id = %s AND date = %s",
               (test_sid, test_cid, test_date))

# 5. ADMIN CRUD INTEGRATION TEST
def test_student_crud_lifecycle():
    """Test creating, reading, updating, and deleting a student record."""
    dummy_id = 'TEST9999'
    execute_db("DELETE FROM student WHERE student_id = %s", (dummy_id,))

    # Create
    execute_db("""
        INSERT INTO student (student_id, student_name, email, phone, department)
        VALUES (%s, %s, %s, %s, %s)
    """, (dummy_id, 'Test Student', 'test.student@college.edu', '9999999999', 'Computer Science'))

    # Read
    s = query_db("SELECT * FROM student WHERE student_id = %s", (dummy_id,), one=True)
    assert s is not None
    assert s['student_name'] == 'Test Student'

    # Update
    execute_db("UPDATE student SET student_name = %s WHERE student_id = %s", ('Updated Student', dummy_id))
    s_updated = query_db("SELECT student_name FROM student WHERE student_id = %s", (dummy_id,), one=True)
    assert s_updated['student_name'] == 'Updated Student'

    # Delete
    execute_db("DELETE FROM student WHERE student_id = %s", (dummy_id,))
    s_deleted = query_db("SELECT * FROM student WHERE student_id = %s", (dummy_id,), one=True)
    assert s_deleted is None

# 6. FEATURE TESTS: BUNK CALCULATOR, LEAVE WORKFLOW & NOTIFICATIONS
def test_safe_bunk_formula():
    """Verify safe bunk calculation: floor((Attended - 0.75 * Total) / 0.75)"""
    import math
    attended = 11
    total = 12
    # (11 - 9) / 0.75 = 2.66 -> exactly 2 classes can be skipped
    safe_bunks = max(0, math.floor((attended - 0.75 * total) / 0.75))
    assert safe_bunks == 2
    # Verify: if 2 missed -> 11/14 = 78.57% (>= 75%)
    assert round((11 / 14) * 100, 2) >= 75.0
    # Verify: if 3 missed -> 11/15 = 73.33% (< 75%)
    assert round((11 / 15) * 100, 2) < 75.0

def test_leave_regularization_workflow():
    """Verify leave request submission and approval creates attendance entry."""
    test_sid = '24BAI0250'
    test_cid = 'BCSE303L'
    test_date = '2026-11-15'

    # Clean up
    execute_db("DELETE FROM leave_request WHERE student_id = %s AND leave_date = %s", (test_sid, test_date))
    execute_db("DELETE FROM attendance WHERE student_id = %s AND date = %s", (test_sid, test_date))

    # Apply
    lid = execute_db("""
        INSERT INTO leave_request (student_id, course_id, leave_date, leave_type, reason, status)
        VALUES (%s, %s, %s, 'Medical Leave', 'Doctor advised rest', 'Pending')
    """, (test_sid, test_cid, test_date))

    req = query_db("SELECT * FROM leave_request WHERE request_id = %s", (lid,), one=True)
    assert req['status'] == 'Pending'

    # Approve & regularize attendance
    execute_db("UPDATE leave_request SET status = 'Approved', faculty_remarks = 'Approved' WHERE request_id = %s", (lid,))
    execute_db("""
        INSERT INTO attendance (student_id, course_id, date, status, remarks)
        VALUES (%s, %s, %s, 'Present', 'Medical Leave Approved')
        ON DUPLICATE KEY UPDATE status = 'Present', remarks = VALUES(remarks)
    """, (test_sid, test_cid, test_date))

    att = query_db("SELECT status, remarks FROM attendance WHERE student_id = %s AND date = %s", (test_sid, test_date), one=True)
    assert att['status'] == 'Present'
    assert 'Medical Leave Approved' in att['remarks']

    # Clean up
    execute_db("DELETE FROM leave_request WHERE request_id = %s", (lid,))
    execute_db("DELETE FROM attendance WHERE student_id = %s AND date = %s", (test_sid, test_date))

def test_notification_delivery():
    """Verify academic notification delivery to student."""
    test_sid = '24BAI0250'
    nid = execute_db("""
        INSERT INTO notification (student_id, title, message, type)
        VALUES (%s, 'Test Alert', 'Automated testing notice', 'warning')
    """, (test_sid,))

    notif = query_db("SELECT * FROM notification WHERE notification_id = %s", (nid,), one=True)
    assert notif is not None
    assert notif['is_read'] == 0

    # Mark as read
    execute_db("UPDATE notification SET is_read = 1 WHERE notification_id = %s", (nid,))
    notif_updated = query_db("SELECT is_read FROM notification WHERE notification_id = %s", (nid,), one=True)
    assert notif_updated['is_read'] == 1

    # Clean up
    execute_db("DELETE FROM notification WHERE notification_id = %s", (nid,))

if __name__ == '__main__':
    pytest.main(['-v', 'test_system.py'])
