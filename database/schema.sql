-- =====================================================================
-- DATABASE SYSTEMS - PROJECT
-- STUDENT ATTENDANCE MANAGEMENT SYSTEM
-- Authors: Marthav Ganesh (24BCE0662), Saketh Kolluri (24BAI0250), Kota Reeyan (24BCT0308)
-- Schema Definition
-- =====================================================================

CREATE DATABASE IF NOT EXISTS student_attendance_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE student_attendance_db;

-- ---------------------------------------------------------------------
-- 1. Table: student (Core Entity 1)
-- Stores student identification, personal, and academic details.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student (
    student_id VARCHAR(20) NOT NULL,
    student_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20) DEFAULT NULL,
    department VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id),
    INDEX idx_student_dept (department),
    INDEX idx_student_name (student_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 2. Table: faculty (Core Entity 2)
-- Stores faculty identification and department information.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS faculty (
    faculty_id VARCHAR(20) NOT NULL,
    faculty_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    department VARCHAR(50) NOT NULL,
    phone VARCHAR(20) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (faculty_id),
    INDEX idx_faculty_dept (department)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 3. Table: course (Core Entity 3)
-- Stores course information, credits, and assigned faculty.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS course (
    course_id VARCHAR(20) NOT NULL,
    course_name VARCHAR(100) NOT NULL,
    credits INT NOT NULL DEFAULT 3,
    faculty_id VARCHAR(20) DEFAULT NULL,
    department VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (course_id),
    CONSTRAINT fk_course_faculty FOREIGN KEY (faculty_id) 
        REFERENCES faculty(faculty_id) 
        ON DELETE SET NULL 
        ON UPDATE CASCADE,
    INDEX idx_course_dept (department)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 4. Table: attendance (Core Entity 4)
-- Stores attendance status of students for particular courses and dates.
-- Constraint: unique_student_course_date prevents duplicate entries.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INT AUTO_INCREMENT NOT NULL,
    student_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    status ENUM('Present', 'Absent') NOT NULL,
    remarks VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (attendance_id),
    CONSTRAINT fk_attendance_student FOREIGN KEY (student_id) 
        REFERENCES student(student_id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    CONSTRAINT fk_attendance_course FOREIGN KEY (course_id) 
        REFERENCES course(course_id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    CONSTRAINT unique_attendance_entry UNIQUE KEY (student_id, course_id, date),
    INDEX idx_attendance_date (date),
    INDEX idx_attendance_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 5. Table: enrollment (Relational mapping between Student and Course)
-- Connects students with their registered courses.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS enrollment (
    enrollment_id INT AUTO_INCREMENT NOT NULL,
    student_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    semester VARCHAR(20) NOT NULL DEFAULT 'Fall 2026',
    enrollment_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (enrollment_id),
    CONSTRAINT fk_enrollment_student FOREIGN KEY (student_id) 
        REFERENCES student(student_id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    CONSTRAINT fk_enrollment_course FOREIGN KEY (course_id) 
        REFERENCES course(course_id) 
        ON DELETE CASCADE 
        ON UPDATE CASCADE,
    CONSTRAINT unique_student_course_enrollment UNIQUE KEY (student_id, course_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 6. Table: users (Authentication and Role-Based Access Control)
-- Stores hashed credentials for Admin, Faculty, and Students.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'faculty', 'student') NOT NULL,
    reference_id VARCHAR(20) DEFAULT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    INDEX idx_user_role (role),
    INDEX idx_user_ref (reference_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 7. Table: leave_request (Attendance Regularization / OD / Medical Leave)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS leave_request (
    request_id INT AUTO_INCREMENT NOT NULL,
    student_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    leave_date DATE NOT NULL,
    leave_type ENUM('Medical Leave', 'On Duty (OD)', 'Personal Leave', 'Academic Event') NOT NULL,
    reason TEXT NOT NULL,
    status ENUM('Pending', 'Approved', 'Rejected') NOT NULL DEFAULT 'Pending',
    faculty_remarks VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (request_id),
    CONSTRAINT fk_leave_student FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_leave_course FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_leave_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 8. Table: notification (System & Academic Warning Notices)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notification (
    notification_id INT AUTO_INCREMENT NOT NULL,
    student_id VARCHAR(20) DEFAULT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    type ENUM('warning', 'info', 'success', 'danger') NOT NULL DEFAULT 'info',
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (notification_id),
    CONSTRAINT fk_notif_student FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_notif_read (is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

