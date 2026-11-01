"""
Database connection manager and helper utilities.
Supports PyMySQL and mysql.connector with dictionary cursor results.
"""
import os
import sys

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pymysql
import pymysql.cursors
from config import Config

def get_connection(database=None):
    """
    Establish a MySQL connection using configured credentials.
    """
    db_to_use = database if database is not None else Config.DB_NAME
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=db_to_use,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

def query_db(query, args=(), one=False):
    """
    Execute a SELECT query and return results as dictionary or list of dictionaries.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, args)
            result = cursor.fetchall()
            return (result[0] if result else None) if one else result
    finally:
        conn.close()

def execute_db(query, args=(), commit=True):
    """
    Execute an INSERT, UPDATE, or DELETE query.
    Returns lastrowid or affected rows count.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, args)
            last_id = cursor.lastrowid
            affected = cursor.rowcount
        if commit:
            conn.commit()
        return last_id if last_id else affected
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_many(query, seq_of_args):
    """
    Execute a parameterized query against a sequence of arguments.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.executemany(query, seq_of_args)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
