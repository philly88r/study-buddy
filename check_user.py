import sqlite3

def check_user():
    conn = sqlite3.connect('instance/studybuddy.db')
    cursor = conn.cursor()
    
    # Get user info
    cursor.execute('SELECT * FROM user WHERE email = ?', ('pematthews41@gmail.com',))
    user = cursor.fetchone()
    
    if user:
        print("User found:")
        print(f"ID: {user[0]}")
        print(f"Username: {user[1]}")
        print(f"Email: {user[2]}")
        print(f"Password Hash: {user[3]}")
        print(f"Is Admin: {user[4]}")
        print(f"Created At: {user[5]}")
    else:
        print("No user found with that email")
    
    conn.close()

if __name__ == '__main__':
    check_user()
