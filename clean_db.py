from app import app, db, NewsArticle

def clean_database():
    with app.app_context():
        # Get all articles with empty titles or slugs
        malformed_articles = NewsArticle.query.filter(
            (NewsArticle.title == '') | 
            (NewsArticle.slug == '') |
            (NewsArticle.slug.like('-%')) |  # Catches slugs like -1, -2, etc.
            (NewsArticle.title.like('Here are%'))  # Remove articles that are just title suggestions
        ).all()
        
        print(f"Found {len(malformed_articles)} malformed articles")
        
        # Delete them
        for article in malformed_articles:
            db.session.delete(article)
        
        # Commit the changes
        db.session.commit()
        
        # Print remaining articles count
        remaining = NewsArticle.query.count()
        print(f"Remaining articles: {remaining}")

if __name__ == "__main__":
    clean_database()
