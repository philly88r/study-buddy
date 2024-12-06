import os
import shutil
from app import app, db
from models import User

def setup_database():
    with app.app_context():
        # Remove old database files
        db_file = 'instance/studybuddy.db'
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
                print(f"Removed old database: {db_file}")
            except Exception as e:
                print(f"Could not remove old database: {str(e)}")
                print("Continuing with existing database...")
            
        # Create all tables
        db.create_all()
        print("Created database tables")
        
        # Check if admin exists
        existing_admin = User.query.filter_by(email='pematthews41@gmail.com').first()
        if existing_admin:
            print("Admin user already exists!")
            return
        
        # Create admin user
        admin = User(
            username='admin',
            email='pematthews41@gmail.com',
            is_admin=True
        )
        admin.set_password('Yitbos88')
        
        try:
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
            print(f"Email: pematthews41@gmail.com")
            print(f"Password: Yitbos88")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin: {str(e)}")
            raise

if __name__ == '__main__':
    setup_database()
