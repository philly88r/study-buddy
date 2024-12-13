from app import app, db
from models import NewsArticle

print("Using database:", app.config['SQLALCHEMY_DATABASE_URI'])

with app.app_context():
    # Delete all articles
    NewsArticle.query.delete()
    db.session.commit()

    print("All articles have been deleted successfully!")
