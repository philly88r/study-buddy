import sqlite3
from werkzeug.security import generate_password_hash

def recreate_admin():
    conn = sqlite3.connect('instance/studybuddy.db')
    cursor = conn.cursor()
    
    # Delete existing admin
    cursor.execute('DELETE FROM user WHERE email = ?', ('pematthews41@gmail.com',))
    
    # Create new admin with proper password hash
    password_hash = generate_password_hash('Yitbos88')
    cursor.execute('''
    INSERT INTO user (username, email, password_hash, is_admin)
    VALUES (?, ?, ?, ?)
    ''', ('admin', 'pematthews41@gmail.com', password_hash, True))
    
    conn.commit()
    conn.close()
    print("Admin user recreated successfully!")
    print("Email: pematthews41@gmail.com")
    print("Password: Yitbos88")

if __name__ == '__main__':
    recreate_admin()
