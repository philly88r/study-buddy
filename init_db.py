import os
import sqlite3
from werkzeug.security import generate_password_hash

def init_database():
    # Ensure instance directory exists
    instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    
    # Database path
    db_path = os.path.join(instance_dir, 'app.db')
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"Removed existing database: {db_path}")
        except Exception as e:
            print(f"Error removing database: {e}")
            return
    
    # Create new database and tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create user table
    cursor.execute('''
    CREATE TABLE user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(80) UNIQUE NOT NULL,
        email VARCHAR(120) UNIQUE NOT NULL,
        password_hash VARCHAR(256) NOT NULL,
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create admin user
    password_hash = generate_password_hash('Yitbos88')
    cursor.execute('''
    INSERT INTO user (username, email, password_hash, is_admin)
    VALUES (?, ?, ?, ?)
    ''', ('admin', 'pematthews41@gmail.com', password_hash, True))
    
    # Create blog_post table
    cursor.execute('''
    CREATE TABLE blog_post (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(200) NOT NULL,
        slug VARCHAR(200) UNIQUE NOT NULL,
        introduction TEXT NOT NULL,
        content TEXT NOT NULL,
        toc TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Database initialized at: {db_path}")
    print("Admin user created:")
    print("Email: pematthews41@gmail.com")
    print("Password: Yitbos88")

if __name__ == '__main__':
    init_database()
