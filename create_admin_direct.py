import sqlite3
import os
from werkzeug.security import generate_password_hash

def create_admin_user():
    # Ensure instance directory exists
    os.makedirs('instance', exist_ok=True)
    
    # Connect to SQLite database
    conn = sqlite3.connect('instance/studybuddy.db')
    cursor = conn.cursor()
    
    # Create user table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(80) UNIQUE NOT NULL,
        email VARCHAR(120) UNIQUE NOT NULL,
        password_hash VARCHAR(256),
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Check if admin exists
    cursor.execute('SELECT * FROM user WHERE email = ?', ('pematthews41@gmail.com',))
    if cursor.fetchone() is not None:
        print("Admin user already exists!")
        conn.close()
        return
    
    # Create admin user
    hashed_password = generate_password_hash('Yitbos88')
    cursor.execute('''
    INSERT INTO user (username, email, password_hash, is_admin)
    VALUES (?, ?, ?, ?)
    ''', ('admin', 'pematthews41@gmail.com', hashed_password, True))
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Admin user created successfully!")
    print("Email: pematthews41@gmail.com")
    print("Password: Yitbos88")

if __name__ == '__main__':
    create_admin_user()
