from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def create_admin_user():
    with app.app_context():
        # Check if admin already exists
        existing_admin = User.query.filter_by(email='pematthews41@gmail.com').first()
        if existing_admin:
            print("Admin user already exists!")
            return

        # Create new admin user
        admin = User(
            username='admin',
            email='pematthews41@gmail.com',
            password=generate_password_hash('Yitbos88'),
            is_admin=True
        )

        try:
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin: {str(e)}")

if __name__ == '__main__':
    create_admin_user()
