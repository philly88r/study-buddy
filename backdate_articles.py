from app import app, db, NewsArticle
from datetime import datetime, timedelta
import random

def backdate_articles():
    # Get all articles
    articles = NewsArticle.query.all()
    
    # Calculate date range (6 months ago to now)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    print(f"Found {len(articles)} articles to backdate")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    
    # Update each article with a random date in the range
    for i, article in enumerate(articles, 1):
        # Generate random number of days to subtract from end_date
        days_ago = random.randint(0, 180)
        new_date = end_date - timedelta(days=days_ago)
        
        # Update article date
        article.created_at = new_date
        print(f"Article {i}/{len(articles)}: {article.title[:50]}... -> {new_date.date()}")
    
    # Commit changes to database
    db.session.commit()
    print(f"\nSuccessfully backdated {len(articles)} articles")

if __name__ == '__main__':
    with app.app_context():
        backdate_articles()
