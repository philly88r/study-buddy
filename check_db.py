import sqlite3
import os

def check_database():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'app.db')
    print(f"Checking database at: {db_path}")
    
    if not os.path.exists(db_path):
        print("Database file does not exist!")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\nTables in database:")
    for table in tables:
        print(f"\nTable: {table[0]}")
        cursor.execute(f"PRAGMA table_info({table[0]});")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
            
    # Check blog posts
    cursor.execute("SELECT COUNT(*) FROM blog_post;")
    count = cursor.fetchone()[0]
    print(f"\nNumber of blog posts: {count}")
    
    if count > 0:
        cursor.execute("SELECT title, slug FROM blog_post;")
        posts = cursor.fetchall()
        print("\nBlog posts:")
        for post in posts:
            print(f"  - {post[0]} (slug: {post[1]})")
    
    conn.close()

if __name__ == '__main__':
    check_database()
