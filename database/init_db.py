"""
Database initialization and data seeding script.
Connects to MySQL, creates database if missing, executes schema.sql,
and populates with realistic sample records and hashed user accounts.
"""
import os
import sys

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pymysql
from werkzeug.security import generate_password_hash
from config import Config

def init_database():
    print(f"Connecting to MySQL server at {Config.DB_HOST}:{Config.DB_PORT} as {Config.DB_USER}...")
    
    # Connect without database first to ensure database exists
    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        charset='utf8mb4',
        autocommit=True
    )
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            print(f"Database '{Config.DB_NAME}' ensured.")
    finally:
        conn.close()

    # Read and execute schema.sql
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset='utf8mb4',
        autocommit=False
    )
    
    try:
        with conn.cursor() as cursor:
            # Execute schema statements
            statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
            for stmt in statements:
                # Skip USE and CREATE DATABASE here as we already connected to DB_NAME
                if stmt.upper().startswith('CREATE DATABASE') or stmt.upper().startswith('USE '):
                    continue
                cursor.execute(stmt)
        conn.commit()
        print("Schema tables created successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error executing schema: {e}")
        raise e
    finally:
        conn.close()

    # Now populate sample data
    seed_sample_data()

def seed_sample_data():
    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset='utf8mb4',
        autocommit=False
    )
    
    try:
        with conn.cursor() as cursor:
            # 1. Seed Faculty
            faculty_data = [
                ('FAC001', 'Dr. Suresh Kumar', 'suresh.kumar@college.edu', 'Computer Science & Engineering', '+91 98765 43210'),
                ('FAC002', 'Prof. Lakshmi Narayanan', 'lakshmi.n@college.edu', 'Artificial Intelligence & Data Science', '+91 98765 43211'),
                ('FAC003', 'Dr. Rajesh Iyer', 'rajesh.iyer@college.edu', 'Information Technology', '+91 98765 43212')
            ]
            cursor.executemany("""
                INSERT INTO faculty (faculty_id, faculty_name, email, department, phone)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    faculty_name = VALUES(faculty_name),
                    email = VALUES(email),
                    department = VALUES(department),
                    phone = VALUES(phone)
            """, faculty_data)

            # 2. Seed Students (Includes documentation team members!)
            student_data = [
                ('24BAI0250', 'Saketh Kolluri', 'saketh.kolluri@college.edu', '+91 91234 56780', 'Artificial Intelligence'),
                ('24BCE0662', 'Marthav Ganesh', 'marthav.ganesh@college.edu', '+91 91234 56781', 'Computer Science & Engineering'),
                ('24BCT0308', 'Kota Reeyan', 'kota.reeyan@college.edu', '+91 91234 56782', 'Computer Science & IT'),
                ('24BCE0408', 'Ananya Sharma', 'ananya.sharma@college.edu', '+91 91234 56783', 'Computer Science & Engineering'),
                ('24BCE0690', 'Rahul Verma', 'rahul.verma@college.edu', '+91 91234 56784', 'Computer Science & Engineering'),
                ('24BAI0112', 'Priya Patel', 'priya.patel@college.edu', '+91 91234 56785', 'Artificial Intelligence')
            ]
            cursor.executemany("""
                INSERT INTO student (student_id, student_name, email, phone, department)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    student_name = VALUES(student_name),
                    email = VALUES(email),
                    phone = VALUES(phone),
                    department = VALUES(department)
            """, student_data)

            # 3. Seed Courses
            course_data = [
                ('BCSE303L', 'Database Systems', 4, 'FAC001', 'Computer Science & Engineering'),
                ('BCSE202L', 'Data Structures & Algorithms', 4, 'FAC001', 'Computer Science & Engineering'),
                ('BCSE308L', 'Operating Systems', 3, 'FAC002', 'Artificial Intelligence'),
                ('BCSE305L', 'Software Engineering', 3, 'FAC003', 'Information Technology')
            ]
            cursor.executemany("""
                INSERT INTO course (course_id, course_name, credits, faculty_id, department)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    course_name = VALUES(course_name),
                    credits = VALUES(credits),
                    faculty_id = VALUES(faculty_id),
                    department = VALUES(department)
            """, course_data)

            # 4. Seed Course Enrollments
            enrollments = [
                # Saketh Kolluri
                ('24BAI0250', 'BCSE303L', 'Fall 2026', '2026-08-01'),
                ('24BAI0250', 'BCSE202L', 'Fall 2026', '2026-08-01'),
                ('24BAI0250', 'BCSE308L', 'Fall 2026', '2026-08-01'),
                # Marthav Ganesh
                ('24BCE0662', 'BCSE303L', 'Fall 2026', '2026-08-01'),
                ('24BCE0662', 'BCSE202L', 'Fall 2026', '2026-08-01'),
                ('24BCE0662', 'BCSE305L', 'Fall 2026', '2026-08-01'),
                # Kota Reeyan
                ('24BCT0308', 'BCSE303L', 'Fall 2026', '2026-08-01'),
                ('24BCT0308', 'BCSE308L', 'Fall 2026', '2026-08-01'),
                ('24BCT0308', 'BCSE305L', 'Fall 2026', '2026-08-01'),
                # Ananya Sharma
                ('24BCE0408', 'BCSE303L', 'Fall 2026', '2026-08-01'),
                ('24BCE0408', 'BCSE202L', 'Fall 2026', '2026-08-01'),
                # Rahul Verma
                ('24BCE0690', 'BCSE303L', 'Fall 2026', '2026-08-01'),
                ('24BCE0690', 'BCSE308L', 'Fall 2026', '2026-08-01'),
                # Priya Patel
                ('24BAI0112', 'BCSE308L', 'Fall 2026', '2026-08-01'),
                ('24BAI0112', 'BCSE202L', 'Fall 2026', '2026-08-01')
            ]
            cursor.executemany("""
                INSERT INTO enrollment (student_id, course_id, semester, enrollment_date)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE semester = VALUES(semester)
            """, enrollments)

            # 5. Seed Users (Admin, Faculty, Students) with Secure Password Hashing
            admin_pwd = generate_password_hash('admin123')
            faculty_pwd = generate_password_hash('faculty123')
            student_pwd = generate_password_hash('student123')

            users = [
                # Admin
                ('admin', admin_pwd, 'admin', None, 'System Administrator', 'admin@college.edu'),
                # Faculty
                ('FAC001', faculty_pwd, 'faculty', 'FAC001', 'Dr. Suresh Kumar', 'suresh.kumar@college.edu'),
                ('FAC002', faculty_pwd, 'faculty', 'FAC002', 'Prof. Lakshmi Narayanan', 'lakshmi.n@college.edu'),
                ('FAC003', faculty_pwd, 'faculty', 'FAC003', 'Dr. Rajesh Iyer', 'rajesh.iyer@college.edu'),
                # Students (Reg No as username)
                ('24BAI0250', student_pwd, 'student', '24BAI0250', 'Saketh Kolluri', 'saketh.kolluri@college.edu'),
                ('24BCE0662', student_pwd, 'student', '24BCE0662', 'Marthav Ganesh', 'marthav.ganesh@college.edu'),
                ('24BCT0308', student_pwd, 'student', '24BCT0308', 'Kota Reeyan', 'kota.reeyan@college.edu'),
                ('24BCE0408', student_pwd, 'student', '24BCE0408', 'Ananya Sharma', 'ananya.sharma@college.edu'),
                ('24BCE0690', student_pwd, 'student', '24BCE0690', 'Rahul Verma', 'rahul.verma@college.edu'),
                ('24BAI0112', student_pwd, 'student', '24BAI0112', 'Priya Patel', 'priya.patel@college.edu')
            ]
            cursor.executemany("""
                INSERT INTO users (username, password_hash, role, reference_id, full_name, email)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    password_hash = VALUES(password_hash),
                    role = VALUES(role),
                    full_name = VALUES(full_name),
                    email = VALUES(email)
            """, users)

            # 6. Seed Attendance Records across 12 class dates
            dates = [
                '2026-10-05', '2026-10-07', '2026-10-09',
                '2026-10-12', '2026-10-14', '2026-10-16',
                '2026-10-19', '2026-10-21', '2026-10-23',
                '2026-10-26', '2026-10-28', '2026-10-30'
            ]

            # Attendance matrix for Course BCSE303L (Students: 24BAI0250, 24BCE0662, 24BCT0308, 24BCE0408, 24BCE0690)
            # 24BAI0250: Present on 11 dates, absent on 2026-10-16 -> 11/12 = 91.7%
            # 24BCE0662: Present on 12 dates -> 12/12 = 100%
            # 24BCT0308: Absent on 10-07, 10-14, 10-21, 10-28 -> 8/12 = 66.7% (<75% Warning!)
            # 24BCE0408: Present on 10/12 dates -> 83.3%
            # 24BCE0690: Absent on 10-05, 10-12, 10-19, 10-26 -> 8/12 = 66.7% (<75% Warning!)
            attendance_records = []
            
            # BCSE303L
            for d in dates:
                attendance_records.append(('24BAI0250', 'BCSE303L', d, 'Absent' if d == '2026-10-16' else 'Present', 'Medical Leave' if d == '2026-10-16' else 'Regular'))
                attendance_records.append(('24BCE0662', 'BCSE303L', d, 'Present', 'Regular'))
                attendance_records.append(('24BCT0308', 'BCSE303L', d, 'Absent' if d in ['2026-10-07', '2026-10-14', '2026-10-21', '2026-10-28'] else 'Present', 'Absent without leave' if d in ['2026-10-07', '2026-10-14', '2026-10-21', '2026-10-28'] else 'Regular'))
                attendance_records.append(('24BCE0408', 'BCSE303L', d, 'Absent' if d in ['2026-10-09', '2026-10-23'] else 'Present', 'Regular'))
                attendance_records.append(('24BCE0690', 'BCSE303L', d, 'Absent' if d in ['2026-10-05', '2026-10-12', '2026-10-19', '2026-10-26'] else 'Present', 'Regular'))

            # BCSE202L (Students: 24BAI0250, 24BCE0662, 24BCE0408, 24BAI0112)
            for d in dates[:10]: # 10 sessions
                attendance_records.append(('24BAI0250', 'BCSE202L', d, 'Absent' if d in ['2026-10-12', '2026-10-26'] else 'Present', 'Regular'))
                attendance_records.append(('24BCE0662', 'BCSE202L', d, 'Absent' if d in ['2026-10-09', '2026-10-21'] else 'Present', 'Regular'))
                attendance_records.append(('24BCE0408', 'BCSE202L', d, 'Present', 'Regular'))
                attendance_records.append(('24BAI0112', 'BCSE202L', d, 'Absent' if d in ['2026-10-05', '2026-10-07', '2026-10-14', '2026-10-21'] else 'Present', 'Regular'))

            # BCSE308L (Students: 24BAI0250, 24BCT0308, 24BCE0690, 24BAI0112)
            for d in dates[:8]: # 8 sessions
                # 24BAI0250: Absent on 3 dates -> 5/8 = 62.5% (<75% Warning!)
                attendance_records.append(('24BAI0250', 'BCSE308L', d, 'Absent' if d in ['2026-10-07', '2026-10-14', '2026-10-21'] else 'Present', 'Regular'))
                attendance_records.append(('24BCT0308', 'BCSE308L', d, 'Absent' if d in ['2026-10-05', '2026-10-19', '2026-10-26'] else 'Present', 'Regular'))
                attendance_records.append(('24BCE0690', 'BCSE308L', d, 'Present', 'Regular'))
                attendance_records.append(('24BAI0112', 'BCSE308L', d, 'Present', 'Regular'))

            # BCSE305L (Students: 24BCE0662, 24BCT0308)
            for d in dates[:6]: # 6 sessions
                attendance_records.append(('24BCE0662', 'BCSE305L', d, 'Present', 'Regular'))
                attendance_records.append(('24BCT0308', 'BCSE305L', d, 'Absent' if d == '2026-10-09' else 'Present', 'Regular'))

            cursor.executemany("""
                INSERT INTO attendance (student_id, course_id, date, status, remarks)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    status = VALUES(status),
                    remarks = VALUES(remarks)
            """, attendance_records)

        conn.commit()
        print(f"Sample data successfully seeded! Inserted {len(student_data)} students, {len(faculty_data)} faculty, {len(course_data)} courses, {len(enrollments)} enrollments, and {len(attendance_records)} attendance records.")
    except Exception as e:
        conn.rollback()
        print(f"Error seeding data: {e}")
        raise e
    finally:
        conn.close()

if __name__ == '__main__':
    init_database()
