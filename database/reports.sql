-- =====================================================================
-- DATABASE SYSTEMS - PROJECT
-- STUDENT ATTENDANCE MANAGEMENT SYSTEM
-- Analytical SQL Queries for Attendance Reports & DBMS Demonstration
-- Authors: Marthav Ganesh (24BCE0662), Saketh Kolluri (24BAI0250), Kota Reeyan (24BCT0308)
-- =====================================================================

USE student_attendance_db;

-- ---------------------------------------------------------------------
-- 1. OVERALL ATTENDANCE SUMMARY ACROSS ALL COURSES
-- Computes total classes conducted, total presences, and aggregate attendance %
-- ---------------------------------------------------------------------
SELECT 
    COUNT(*) AS total_attendance_entries,
    SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS total_present,
    SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS total_absent,
    ROUND((SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) AS overall_attendance_percentage
FROM attendance;

-- ---------------------------------------------------------------------
-- 2. COURSE-WISE ATTENDANCE REPORT
-- Demonstrates INNER JOIN, COUNT, SUM(CASE ...), and GROUP BY
-- ---------------------------------------------------------------------
SELECT 
    c.course_id,
    c.course_name,
    c.credits,
    f.faculty_name,
    COUNT(DISTINCT a.date) AS classes_conducted,
    COUNT(a.attendance_id) AS total_records,
    SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS total_present,
    SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS total_absent,
    ROUND(
        (SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2
    ) AS course_attendance_percentage
FROM course c
LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
LEFT JOIN attendance a ON c.course_id = a.course_id
GROUP BY c.course_id, c.course_name, c.credits, f.faculty_name
ORDER BY c.course_id;

-- ---------------------------------------------------------------------
-- 3. STUDENT-WISE ATTENDANCE REPORT (ALL ENROLLED COURSES)
-- Demonstrates formula: (Attended / Total) * 100 with status warning flag
-- ---------------------------------------------------------------------
SELECT 
    s.student_id,
    s.student_name,
    s.department,
    c.course_id,
    c.course_name,
    COUNT(a.attendance_id) AS total_classes,
    SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS attended_classes,
    SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_classes,
    ROUND(
        (SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2
    ) AS attendance_percentage,
    CASE 
        WHEN ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2) < 75.0 
        THEN 'WARNING: LOW ATTENDANCE' 
        ELSE 'SATISFACTORY' 
    END AS status_badge
FROM enrollment e
JOIN student s ON e.student_id = s.student_id
JOIN course c ON e.course_id = c.course_id
LEFT JOIN attendance a ON e.student_id = a.student_id AND e.course_id = a.course_id
GROUP BY s.student_id, s.student_name, s.department, c.course_id, c.course_name
ORDER BY s.student_id, c.course_id;

-- ---------------------------------------------------------------------
-- 4. LOW-ATTENDANCE REPORT (STUDENTS WITH ATTENDANCE < 75%)
-- Demonstrates HAVING clause for filtering aggregated results
-- ---------------------------------------------------------------------
SELECT 
    s.student_id,
    s.student_name,
    s.email,
    s.phone,
    c.course_id,
    c.course_name,
    f.faculty_name,
    COUNT(a.attendance_id) AS total_classes,
    SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS classes_attended,
    ROUND(
        (SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2
    ) AS attendance_percentage,
    -- Calculation: classes needed to attend consecutively to reach 75%
    GREATEST(0, CEIL((0.75 * COUNT(a.attendance_id) - SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END)) / 0.25)) AS classes_needed_for_75
FROM enrollment e
JOIN student s ON e.student_id = s.student_id
JOIN course c ON e.course_id = c.course_id
LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
LEFT JOIN attendance a ON e.student_id = a.student_id AND e.course_id = a.course_id
GROUP BY s.student_id, s.student_name, s.email, s.phone, c.course_id, c.course_name, f.faculty_name
HAVING attendance_percentage < 75.0
ORDER BY attendance_percentage ASC;

-- ---------------------------------------------------------------------
-- 5. DATE-WISE ATTENDANCE SUMMARY
-- Groups attendance by date to see daily trends
-- ---------------------------------------------------------------------
SELECT 
    a.date,
    COUNT(DISTINCT a.course_id) AS courses_held,
    COUNT(a.attendance_id) AS total_students_marked,
    SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
    SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
    ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / COUNT(a.attendance_id)) * 100, 2) AS daily_attendance_rate
FROM attendance a
GROUP BY a.date
ORDER BY a.date DESC;

-- ---------------------------------------------------------------------
-- 6. FACULTY-WISE PERFORMANCE & ATTENDANCE SUMMARY
-- ---------------------------------------------------------------------
SELECT 
    f.faculty_id,
    f.faculty_name,
    f.department,
    COUNT(DISTINCT c.course_id) AS courses_taught,
    COUNT(DISTINCT a.date) AS total_lecture_days,
    COUNT(a.attendance_id) AS total_student_sessions,
    SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS total_present,
    ROUND(
        (SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / NULLIF(COUNT(a.attendance_id), 0)) * 100, 2
    ) AS average_student_attendance
FROM faculty f
LEFT JOIN course c ON f.faculty_id = c.faculty_id
LEFT JOIN attendance a ON c.course_id = a.course_id
GROUP BY f.faculty_id, f.faculty_name, f.department
ORDER BY f.faculty_id;
