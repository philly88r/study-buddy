from app import app, db
from models import NewsArticle, User, BlogPost

def setup_database():
    print("Setting up database...")
    print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])
    
    with app.app_context():
        # Drop all tables
        db.drop_all()
        print("Dropped all existing tables")
        
        # Create all tables
        db.create_all()
        print("Created new tables")
        
        print("Database setup complete!")

if __name__ == "__main__":
    setup_database()
