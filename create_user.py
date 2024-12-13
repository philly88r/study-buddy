from app import app, db
from models import User

def create_user(username, email, password):
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            print("User with this username or email already exists")
            return False
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            print(f"Successfully created user {username}")
            return True
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    username = "Yitbos88"
    email = "pematthews89@gmail.com"
    password = "pematthews89"
    
    success = create_user(username, email, password)
    if success:
        print("User created successfully!")
    else:
        print("Failed to create user.")
