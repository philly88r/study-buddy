from app import app, db, User

def create_test_accounts():
    # Read emails from file
    with open('test_emails.txt', 'r') as f:
        emails = [line.strip() for line in f.readlines()]
    
    # Create application context
    with app.app_context():
        # Create accounts for each email
        for email in emails:
            # Check if user already exists
            if not User.query.filter_by(email=email).first():
                # Create new user with default password 'password123'
                username = email.split('@')[0]  # Use part before @ as username
                new_user = User(username=username, email=email)
                new_user.set_password('password123')
                db.session.add(new_user)
                print(f"Created account for {email}")
            else:
                print(f"Account already exists for {email}")
        
        # Commit changes
        db.session.commit()
        print("All accounts created successfully!")

if __name__ == '__main__':
    create_test_accounts()
