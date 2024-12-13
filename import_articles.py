import os
from bs4 import BeautifulSoup
from models import NewsArticle
from extensions import db
from app import app
from slugify import slugify
import re

def extract_article_info(html_file):
    """Extract article information from HTML file"""
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        
        # Get title from meta title or h1
        title = soup.find('title').text if soup.find('title') else soup.find('h1').text
        
        # Get description from meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        description = meta_desc['content'] if meta_desc else ''
        
        # Get main content
        main_content = soup.find('div', class_='main-content')
        content = str(main_content) if main_content else ''
        
        # Get image URL from hero section or first img
        hero_div = soup.find('div', class_='hero')
        if hero_div and 'style' in hero_div.attrs:
            # Extract URL from background-image style
            style = hero_div['style']
            match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', style)
            image_url = match.group(1) if match else ''
        else:
            img = soup.find('img')
            image_url = img['src'] if img else ''
        
        return {
            'title': title,
            'description': description,
            'content': content,
            'category': 'study-tips',  # As specified by user
            'image_url': image_url,
            'source_url': f'/news/study-tips/{slugify(title)}'  # Generate source URL from title
        }

def import_articles_from_folder(folder_path):
    """Import articles from a folder containing HTML files"""
    print(f"\nImporting articles from: {folder_path}")
    
    success_count = 0
    error_count = 0
    errors = []

    # Get all HTML files in the folder
    try:
        files = [f for f in os.listdir(folder_path) if f.endswith('.html')]
        print(f"Found {len(files)} HTML files")
    except Exception as e:
        print(f"Error reading folder: {str(e)}")
        return

    with app.app_context():
        for filename in files:
            try:
                file_path = os.path.join(folder_path, filename)
                print(f"\nProcessing file: {filename}")

                # Extract article info from HTML
                article = extract_article_info(file_path)
                
                # Create slug from title
                base_slug = slugify(article['title'])
                slug = base_slug
                counter = 1
                while NewsArticle.query.filter_by(slug=slug).first():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                # Create new article
                new_article = NewsArticle(
                    title=article['title'],
                    description=article['description'],
                    content=article['content'],
                    category=article['category'],
                    image_url=article['image_url'],
                    source_url=article['source_url'],
                    meta_title=article['title'][:60],
                    meta_description=article['description'][:160],
                    meta_keywords=f"study buddy, study tips, education",
                    slug=slug,
                    og_title=article['title'][:60],
                    og_description=article['description'][:200]
                )

                db.session.add(new_article)
                success_count += 1
                print(f"Added article: {article['title']}")

                # Commit every 50 articles to avoid memory issues
                if success_count % 50 == 0:
                    db.session.commit()
                    print(f"Committed batch of 50 articles. Total successful so far: {success_count}")

            except Exception as e:
                error_msg = str(e)
                print(f"Error processing {filename}: {error_msg}")
                errors.append({'file': filename, 'error': error_msg})
                error_count += 1
                continue

        # Final commit for any remaining articles
        try:
            db.session.commit()
            print("\nFinal commit successful")
        except Exception as e:
            print(f"\nError in final commit: {str(e)}")
            db.session.rollback()
            error_count += 1

    print(f"\nImport completed:")
    print(f"Successfully imported: {success_count} articles")
    print(f"Errors: {error_count} articles")
    
    if errors:
        print("\nError details:")
        for error in errors:
            print(f"File: {error['file']}")
            print(f"Error: {error['error']}\n")

if __name__ == "__main__":
    # Use the generated_blogs folder in the project directory
    articles_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'generated_blogs')
    
    if not os.path.exists(articles_folder):
        print(f"Error: Folder not found: {articles_folder}")
    else:
        import_articles_from_folder(articles_folder)
