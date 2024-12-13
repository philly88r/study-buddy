from app import app, db, NewsArticle

def cleanup_database():
    with app.app_context():
        try:
            # Fix categories and source_urls for all articles
            articles = NewsArticle.query.all()
            for article in articles:
                # Make category lowercase with hyphens
                article.category = article.category.lower().replace(' ', '-')
                # Update source_url to match our URL format
                article.source_url = f"/news/{article.category}/{article.slug}"
                print(f"Updated article: {article.title}")
                print(f"  Category: {article.category}")
                print(f"  URL: {article.source_url}")
            
            # Commit the changes
            db.session.commit()
            print("\nDatabase cleanup completed successfully!")
            
            # Print summary
            articles = NewsArticle.query.all()
            print(f"\nTotal articles: {len(articles)}")
            for article in articles:
                print(f"\nArticle {article.id}:")
                print(f"Title: {article.title}")
                print(f"Category: {article.category}")
                print(f"URL: {article.source_url}")
            
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    cleanup_database()
