from app import app, db, User

def add_user():
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(email='pematthews41@gmail.com').first()
        if existing_user:
            print("User already exists")
            return
            
        # Create new user
        user = User(username='pematthews41', email='pematthews41@gmail.com')
        user.set_password('Yitbos88')
        
        try:
            db.session.add(user)
            db.session.commit()
            print('User added successfully')
        except Exception as e:
            print(f'Error adding user: {str(e)}')
            db.session.rollback()

if __name__ == '__main__':
    add_user()
