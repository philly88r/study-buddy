from app import app, db, NewsArticle

def delete_articles():
    with app.app_context():
        # Find articles with 'beach' or 'interior design' in the title
        articles = NewsArticle.query.filter(
            (NewsArticle.title.ilike('%beach%')) | 
            (NewsArticle.title.ilike('%interior design%'))
        ).all()
        
        print(f"Found {len(articles)} articles to delete:")
        for article in articles:
            print(f"- {article.title}")
            db.session.delete(article)
        
        db.session.commit()
        print("\nArticles deleted successfully!")

if __name__ == '__main__':
    delete_articles()
