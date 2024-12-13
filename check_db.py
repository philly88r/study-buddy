import sqlite3
import os

def check_database():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'studybuddy.db')
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
            
    # Check news articles
    cursor.execute("SELECT COUNT(*) FROM news_article;")
    count = cursor.fetchone()[0]
    print(f"\nNumber of news articles: {count}")
    
    if count > 0:
        cursor.execute("SELECT id, title, category FROM news_article;")
        articles = cursor.fetchall()
        print("\nNews articles:")
        for article in articles:
            print(f"  - [{article[0]}] {article[1]} (category: {article[2]})")
    
    conn.close()

if __name__ == '__main__':
    check_database()
