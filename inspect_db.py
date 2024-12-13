from app import app, db, NewsArticle
import json

def inspect_database():
    try:
        # Get all articles
        articles = NewsArticle.query.all()
        print("\n=== Database Inspection ===")
        print(f"Total articles: {len(articles)}")
        print("\nDetailed Article Information:")
        
        for idx, article in enumerate(articles, 1):
            article_data = {
                'id': article.id,
                'title': article.title,
                'slug': article.slug,
                'source_url': article.source_url,
                'category': article.category,
                'created_at': str(article.created_at)
            }
            print(f"\nArticle {idx}:")
            print(json.dumps(article_data, indent=2))
            
        # Get table info
        table_info = db.inspect(db.engine).get_table_names()
        print("\nDatabase Tables:", table_info)
        
        # Show table schema
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        for table_name in inspector.get_table_names():
            print(f"\nColumns in {table_name}:")
            for column in inspector.get_columns(table_name):
                print(f"- {column['name']}: {column['type']}")

    except Exception as e:
        print(f"Error inspecting database: {str(e)}")

if __name__ == "__main__":
    with app.app_context():
        inspect_database()
