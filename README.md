# Student Attendance Management System

**Database Systems (DBMS) Academic Software Project**  
*Fully functional, end-to-end relational database application built with Python Flask and MySQL.*

---

## 👥 Project Team Members

| Registration No. | Student Name | Role |
| :--- | :--- | :--- |
| **24BCE0662** | Marthav Ganesh | Database Design & Backend Architecture |
| **24BAI0250** | Saketh Kolluri | Frontend Dashboards & Analytics |
| **24BCT0308** | Kota Reeyan | Authentication, Reporting & Testing |

---

## 🌟 Project Highlights & Features

- **Four Core Entities**: Implemented directly as specified in the project documentation: `Student`, `Faculty`, `Course`, and `Attendance`.
- **Role-Based Portals**:
  - **Admin**: Student CRUD, Faculty CRUD, Course allocation, Attendance master audit, Multi-parameter reports, 1-click official notice dispatch.
  - **Faculty**: Assigned courses overview, enrolled student rosters, daily bulk attendance marking, attendance update/history, **Leave/OD review & approval**, official shortage notice delivery.
  - **Student**: Registration number login, subject-wise attendance percentage calculation, automatic <75% shortage alert and recovery class calculation.
- **Attendance What-If Simulator & Bunk Calculator**:
  - **Safe to Miss (Bunk Margin)**: $\lfloor \frac{\text{Attended} - 0.75 \times \text{Total}}{0.75} \rfloor$
  - **Shortage Recovery**: $\lceil \frac{0.75 \times \text{Total} - \text{Attended}}{0.25} \rceil$
  - **Interactive Real-Time What-If Engine**: Simulate any number of upcoming attended vs skipped classes.
- **Leave & On-Duty (OD) Regularization Workflow**:
  - Students submit Medical, OD (Hackathon/Symposium), Academic Event, or Personal leave requests.
  - Faculty reviews and Approves or Rejects with remarks.
  - Approving a request automatically regularizes the student's attendance to 'Present' with leave remarks!
- **Academic Warning Notices & Notification Center**:
  - Instant delivery of shortage warnings from Faculty or Dean/Admin to student notice boards.
  - Notification alert tracking with read/unread statuses.
- **Duplicate Attendance Prevention**: Relational constraint `UNIQUE KEY (student_id, course_id, date)` ensures integrity.
- **Profile & Password Management**: Self-service secure credential update with PBKDF2 hashing.
- **Reports & Analytics**: Overall, Student-wise, Course-wise, Faculty-wise, Date-wise, and CSV export.
- **Interactive UI**: Responsive Bootstrap 5 layout with Chart.js charts and live search filters.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+ / Flask 3.x
- **Database**: MySQL Server 5.6+ / 8.x
- **Database Driver**: PyMySQL / mysql-connector-python with DictCursor
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons
- **Visualizations**: Chart.js 4.4
- **Security**: Werkzeug PBKDF2 Password Hashing, Session Management

---

## 🔐 Demo Login Credentials

You can test any role directly using the credentials below or click the pre-fill buttons on the login page:

| Role | Username / Identifier | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | System Administrator Portal |
| **Faculty** | `FAC001` | `faculty123` | Dr. Suresh Kumar (CSE Dept) |
| **Faculty** | `FAC002` | `faculty123` | Prof. Lakshmi Narayanan (AI Dept) |
| **Faculty** | `FAC003` | `faculty123` | Dr. Rajesh Iyer (IT Dept) |
| **Student** | `24BAI0250` | `student123` | Saketh Kolluri (AI Dept) |
| **Student** | `24BCE0662` | `student123` | Marthav Ganesh (CSE Dept) |
| **Student** | `24BCT0308` | `student123` | Kota Reeyan (IT Dept) |

---

## 📂 Project Directory Structure

```
compiler/
├── database/
│   ├── db.py                # Database connection manager with dictionary cursor
│   ├── schema.sql           # Complete MySQL DDL statements with constraints & keys
│   ├── init_db.py           # Automated schema creation & data seeding script
│   └── reports.sql          # Analytical SQL queries for DBMS review demonstration
├── auth/
│   ├── __init__.py
│   └── auth_service.py      # Password hashing, session control & role decorators
├── routes/
│   ├── __init__.py
│   ├── auth_routes.py       # Login, portal redirection & logout
│   ├── admin_routes.py      # Admin CRUD, course assignments & monitoring
│   ├── faculty_routes.py    # Faculty daily attendance marking & roster
│   ├── student_routes.py    # Student personal attendance & <75% warnings
│   └── report_routes.py     # Aggregated reports, CSV exports & chart APIs
├── templates/
│   ├── base.html            # Master layout with sidebar & top navbar
│   ├── auth/
│   │   └── login.html       # Clean multi-role login page with quick-fill buttons
│   ├── admin/
│   │   ├── dashboard.html   # Admin KPI metrics & Chart.js charts
│   │   ├── students.html    # Student CRUD with search by Reg No.
│   │   ├── faculty.html     # Faculty CRUD
│   │   ├── courses.html     # Course CRUD & faculty assignment
│   │   ├── enrollments.html # Student-course registration
│   │   ├── attendance.html  # System-wide attendance audit log
│   │   └── reports.html     # Comprehensive analytics & CSV export
│   ├── faculty/
│   │   ├── dashboard.html   # Faculty stats & low-attendance alerts
│   │   ├── courses.html     # Assigned course list
│   │   ├── course_students.html # Roster with individual attendance %
│   │   ├── mark_attendance.html # Interactive attendance marking table
│   │   ├── attendance_history.html # Past session view & edit modal
│   │   └── reports.html     # Course-wise attendance report
│   └── student/
│       ├── dashboard.html   # Subject-wise attendance %, warning banner
│       ├── courses.html     # Enrolled courses & instructors
│       └── history.html     # Complete date-wise attendance log
├── static/
│   ├── css/
│   │   └── custom.css       # Custom styling, animations & badges
│   └── js/
│       └── main.js          # Live search, bulk toggles & mobile menu
├── config.py                # Configuration & database credentials
├── app.py                   # Main Flask application entry point
├── test_system.py           # Pytest test suite (11 test cases)
└── requirements.txt         # Project Python dependencies
```

---

## 🗄️ Relational Database Schema

### 1. `student` (Core Entity 1)
```sql
CREATE TABLE student (
    student_id VARCHAR(20) PRIMARY KEY,
    student_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20),
    department VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. `faculty` (Core Entity 2)
```sql
CREATE TABLE faculty (
    faculty_id VARCHAR(20) PRIMARY KEY,
    faculty_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    department VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. `course` (Core Entity 3)
```sql
CREATE TABLE course (
    course_id VARCHAR(20) PRIMARY KEY,
    course_name VARCHAR(100) NOT NULL,
    credits INT NOT NULL DEFAULT 3,
    faculty_id VARCHAR(20),
    department VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id) ON DELETE SET NULL
);
```

### 4. `attendance` (Core Entity 4)
```sql
CREATE TABLE attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    status ENUM('Present', 'Absent') NOT NULL,
    remarks VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE,
    UNIQUE KEY unique_attendance_entry (student_id, course_id, date)
);
```

### 5. `enrollment` (Student-Course Mapping)
```sql
CREATE TABLE enrollment (
    enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    semester VARCHAR(20) NOT NULL DEFAULT 'Fall 2026',
    enrollment_date DATE NOT NULL,
    FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE,
    UNIQUE KEY unique_student_course (student_id, course_id)
);
```

### 6. `users` (Authentication & Security)
```sql
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'faculty', 'student') NOT NULL,
    reference_id VARCHAR(20),
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🚀 Step-by-Step Installation & Setup

### Prerequisites
- Python 3.10 or higher
- MySQL Server running locally (or XAMPP / MariaDB)

### Step 1: Clone / Open Project in VS Code
Open the project directory in VS Code:
```bash
cd "c:\Users\prane\OneDrive\Desktop\compiler"
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Database Credentials
Edit `config.py` if your local MySQL settings differ:
```python
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = 'your_mysql_password' # (e.g., 123456)
DB_NAME = 'student_attendance_db'
```

### Step 4: Initialize and Seed Database
Run the automated initialization script:
```bash
python database/init_db.py
```
*This creates the database, all normalized tables, foreign keys, constraints, and populates sample records including the documentation team members.*

### Step 5: Run Automated Tests
Verify all features and integrity constraints:
```bash
python -m pytest test_system.py -v
```
*(All 11 tests will pass successfully)*

### Step 6: Start the Application
```bash
python app.py
```
Open your browser and navigate to:
**[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 📊 DBMS Demonstration Queries (`reports.sql`)

During the faculty project review or viva, execute the queries from `database/reports.sql` to demonstrate key DBMS concepts:

1. **Course-wise Attendance with Aggregate Functions**:
   ```sql
   SELECT 
       c.course_id, c.course_name, f.faculty_name,
       COUNT(DISTINCT a.date) AS classes_conducted,
       SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS total_present,
       ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / COUNT(a.attendance_id)) * 100, 2) AS attendance_pct
   FROM course c
   LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
   LEFT JOIN attendance a ON c.course_id = a.course_id
   GROUP BY c.course_id, c.course_name, f.faculty_name;
   ```

2. **Identifying Students with Attendance < 75% using HAVING clause**:
   ```sql
   SELECT 
       s.student_id, s.student_name, c.course_id,
       COUNT(a.attendance_id) AS total_classes,
       SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS classes_attended,
       ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / COUNT(a.attendance_id)) * 100, 2) AS attendance_pct
   FROM enrollment e
   JOIN student s ON e.student_id = s.student_id
   JOIN course c ON e.course_id = c.course_id
   LEFT JOIN attendance a ON e.student_id = a.student_id AND e.course_id = a.course_id
   GROUP BY s.student_id, s.student_name, c.course_id
   HAVING attendance_pct < 75.0;
   ```
