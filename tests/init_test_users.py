#!/usr/bin/env python
"""Initialize test users with proper bcrypt hashes"""
import sys
sys.path.insert(0, r'D:\code')

import pymysql
from app.security import get_password_hash

admin_hash = get_password_hash('admin123')
emp_hash = get_password_hash('emp123')

print(f"admin hash: {admin_hash}")
print(f"emp hash: {emp_hash}")

conn = pymysql.connect(
    host='localhost', port=3306, user='root', password='101704',
    database='asset_management', charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
try:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE username IN ('testadmin', 'testemp')")
        
        cur.execute(
            "INSERT INTO users (username, email, hashed_password, role, is_active) VALUES (%s, %s, %s, %s, %s)",
            ('testadmin', 'testadmin@company.com', admin_hash, 'admin', 1)
        )
        cur.execute(
            "INSERT INTO users (username, email, hashed_password, role, is_active) VALUES (%s, %s, %s, %s, %s)",
            ('testemp', 'testemp@company.com', emp_hash, 'employee', 1)
        )
        conn.commit()
        print("Users created successfully")
        
        # Verify
        cur.execute("SELECT username, hashed_password FROM users WHERE username IN ('testadmin', 'testemp')")
        for row in cur.fetchall():
            print(f"Stored: {row['username']}: {row['hashed_password'][:30]}...")
finally:
    conn.close()