"""
Configuration settings for Student Attendance Management System.
"""
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'student_attendance_secret_key_2026_vit')
    
    # MySQL Database Configuration
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = int(os.environ.get('DB_PORT', 3306))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '123456')
    DB_NAME = os.environ.get('DB_NAME', 'student_attendance_db')
    
    # Business Logic Constants
    ATTENDANCE_THRESHOLD = 75.0  # Percentage below which warning is flagged
    
    # Session Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in HTTPS production
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
