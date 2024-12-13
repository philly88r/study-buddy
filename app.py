from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
import os
import requests
import json
from dotenv import load_dotenv
import traceback
from flask_cors import CORS
import base64
import io
import sys
from PIL import Image
import time
import threading
import hashlib
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from slugify import slugify
from datetime import datetime, timedelta
from cachetools import TTLCache
from flask_session import Session
from pyngrok import ngrok, conf
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from functools import wraps

# Constants
NEWS_CATEGORIES = [
    'study-tips',
    'productivity',
    'mental-health',
    'student-life',
    'technology',
    'career-advice'
]

# Set console encoding to UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Initialize Flask app
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
CORS(app)

# Configure secret key for session
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')  # Make sure to set a strong secret key in production

# Configure session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)  # Sessions last for 31 days
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize Flask-Session
Session(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database configuration
database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'studybuddy.db')
database_url = f'sqlite:///{database_path}'
print(f"Using database: {database_url}")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True  # This will log all SQL queries

# Initialize extensions
from extensions import db
db.init_app(app)

# Import models
from models import User, BlogPost, NewsArticle

# Create database tables
with app.app_context():
    db.create_all()
    print("Database tables created")

# Protected routes decorator
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this feature.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Login required decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Initialize cache for news articles (cache for 30 minutes)
news_cache = TTLCache(maxsize=100, ttl=1800)
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', '')  # Add this to your .env file

# News categories for education
NEWS_CATEGORIES_EDUCATION = [
    'study-tips',           # Study techniques, time management, and productivity tips
    'learning-tools',       # Educational software, apps, and AI tools for students
    'elementary-ed',        # Elementary school education news and resources
    'middle-school',        # Middle school education news and resources
    'high-school',          # High school education news and resources
    'college-prep',         # College preparation, SAT/ACT tips, application advice
    'college-life',         # College life, campus news, and university resources
    'stem-education',       # Science, Technology, Engineering, and Mathematics education
    'arts-humanities',      # Arts and Humanities education
    'special-education',    # Special education resources and news
    'homework-help',        # Homework assistance and tutoring resources
    'test-prep',           # Test preparation strategies and resources
    'parent-resources',     # Resources for parents to help their children
    'education-tech',       # Educational technology and digital learning
    'student-wellness'      # Mental health, stress management, and student well-being
]

# News routes
@app.route('/api/submit_articles', methods=['POST'])
def submit_articles():
    try:
        print("\n=== Submitting Articles ===")
        print("Request Method:", request.method)
        print("Request URL:", request.url)
        print("Request Headers:", dict(request.headers))
        print("Request Content-Type:", request.content_type)
        print("Request Data:", request.get_data(as_text=True))
        
        data = request.get_json()
        print("Parsed JSON Data:", data)
        print(f"Received {len(data)} articles")
        
        if not data or not isinstance(data, list):
            print("Error: Invalid data format")
            return jsonify({'error': 'Invalid data format. Expected a list of articles.'}), 400

        submitted_articles = []
        errors = []

        for i, article in enumerate(data):
            try:
                print(f"\nProcessing article {i+1}:")
                print(f"Title: {article.get('title', 'No title')}")
                print(f"Category: {article.get('category', 'No category')}")
                print(f"Article Data: {json.dumps(article, indent=2)}")
                
                # Validate required fields
                required_fields = ['title', 'description', 'content', 'category', 'image_url', 'source_url']
                missing_fields = [field for field in required_fields if field not in article]
                if missing_fields:
                    error_msg = f'Missing required fields: {missing_fields}'
                    print(f"Error: {error_msg}")
                    errors.append({
                        'title': article.get('title', 'Unknown'),
                        'error': error_msg
                    })
                    continue

                # Create base slug from title if not provided
                if not article.get('slug'):
                    base_slug = slugify(article['title'])
                    slug = base_slug
                    counter = 1

                    # Handle duplicate slugs by appending a number
                    while NewsArticle.query.filter_by(slug=slug).first():
                        slug = f"{base_slug}-{counter}"
                        counter += 1
                else:
                    slug = article['slug']
                print(f"Using slug: {slug}")

                # Format category to match our standard format
                category = article['category'].lower().replace(' ', '-')
                print(f"Formatted category: {category}")

                # Create new article
                try:
                    new_article = NewsArticle(
                        title=article['title'],
                        description=article['description'],
                        content=article['content'],
                        category=category,
                        image_url=article['image_url'],
                        source_url=article.get('source_url', f"/news/{category}/{slug}"),
                        meta_title=article.get('meta_title', article['title'][:60]),
                        meta_description=article.get('meta_description', article['description'][:160]),
                        meta_keywords=article.get('meta_keywords', f"study buddy, {category}, education"),
                        slug=slug,
                        og_title=article.get('og_title', article['title'][:60]),
                        og_description=article.get('og_description', article['description'][:200])
                    )
                    print("Created NewsArticle object:", new_article)
                    db.session.add(new_article)
                    print("Article added to session")
                    
                    submitted_articles.append({
                        'title': article['title'],
                        'slug': slug,
                        'category': category
                    })
                except Exception as article_error:
                    print(f"Error creating article: {str(article_error)}")
                    raise article_error

            except Exception as e:
                print(f"Error processing article: {str(e)}")
                errors.append({
                    'title': article.get('title', 'Unknown'),
                    'error': str(e)
                })

        if submitted_articles:
            try:
                print("\nCommitting changes to database...")
                db.session.commit()
                print("Changes committed successfully")
            except Exception as commit_error:
                print(f"Error during commit: {str(commit_error)}")
                db.session.rollback()
                raise commit_error

        response = {
            'submitted': submitted_articles,
            'errors': errors
        }
        print("\nFinal response:", response)

        if errors and not submitted_articles:
            return jsonify(response), 400
        elif errors:
            return jsonify(response), 207  # Partial success
        else:
            return jsonify(response), 201

    except Exception as e:
        print(f"\nError in submit_articles: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/news/<category>')
def get_news(category):
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get articles for the category with pagination
    pagination = NewsArticle.query.filter_by(category=category)\
        .order_by(NewsArticle.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    articles = pagination.items
    
    return jsonify({
        'articles': [{
            'title': article.title,
            'description': article.description,
            'content': article.content,
            'urlToImage': article.image_url,
            'url': article.source_url,
            'source': {'name': 'Study Buddy'},
            'publishedAt': article.created_at.isoformat(),
            'slug': article.slug
        } for article in articles],
        'pagination': {
            'total': pagination.total,
            'pages': pagination.pages,
            'current': pagination.page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })

@app.route('/news')
def news_page():
    return render_template('news.html', current_user=current_user, categories=NEWS_CATEGORIES_EDUCATION)

@app.route('/news/<category>')
def news_category(category):
    return render_template('news.html', current_user=current_user, categories=NEWS_CATEGORIES_EDUCATION)

@app.route('/news/<category>/<slug>')
def view_article(category, slug):
    try:
        # Query article from database
        article = NewsArticle.query\
            .filter_by(category=category, slug=slug)\
            .first_or_404()
        
        return render_template('article.html', article=article)
            
    except Exception as e:
        flash('Article not found', 'error')
        return redirect(url_for('news_page'))

# Authentication routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"Signup attempt - Username: {username}, Email: {email}")
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('signup'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            print(f"User {username} created successfully")
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            db.session.rollback()
            flash('Error creating user. Please try again.')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)  # Enable "remember me" functionality
            session.permanent = True  # Make the session permanent
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# Protected routes
@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/flashcards')
@auth_required
def flashcards():
    return render_template('flashcards.html')

@app.route('/practice_by_topic')
@auth_required
def practice_by_topic():
    return render_template('practice_by_topic.html')

@app.route('/practice_by_upload')
@auth_required
def practice_by_upload():
    return render_template('practice_by_upload.html')

@app.route('/homework_checker')
@auth_required
def homework_checker():
    return render_template('homework_checker.html')

@app.route('/homework_generator')
@auth_required
def homework_generator():
    return render_template('homework_generator.html')

# Main routes
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print("OpenAI API key not found in environment variables!")

def make_openai_request(endpoint, payload):
    """Make a request to OpenAI API"""
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    response = requests.post(f'https://api.openai.com/v1/{endpoint}', 
                           headers=headers, 
                           json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"OpenAI API request failed with status {response.status_code}: {response.text}")

@app.route('/generate_flashcards', methods=['POST'])
def generate_flashcards():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        card_type = request.form.get('cardType', 'exact')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        try:
            # Read the image file
            image_bytes = file.read()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # First, use GPT-4 Vision to extract text from the image with emphasis on finding all Q&A pairs
            payload = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please carefully examine this image and extract ALL questions and answers you can find. Make sure not to miss any question-answer pairs. Format them as 'Q: [question] A: [answer]' pairs."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1500
            }
            vision_response = make_openai_request('chat/completions', payload)
            
            # Extract the text content from the vision response
            extracted_text = vision_response['choices'][0]['message']['content']
            print(f"Extracted text from image: {extracted_text}")
            
            # For exact questions, parse the extracted text directly
            if card_type == 'exact':
                # Parse the extracted text for exact questions
                flashcard_list = parse_flashcards(extracted_text)
                
                if not flashcard_list:
                    return jsonify({'error': 'No questions could be extracted from the image'}), 400
                
            else:  # For similar questions, generate variations
                # First, ensure we have the original content well-structured
                system_prompt = """Generate 15-20 different but related flashcards based on the content below. 
                Create questions that:
                - Test deeper understanding of the concepts
                - Explore different aspects and implications
                - Include "why" and "how" questions
                - Make connections between different concepts
                - Apply the concepts to new situations
                
                Format each flashcard as:
                Q: [write the question here]
                A: [write the answer here]
                
                Make sure each Q&A pair is on separate lines."""
                
                # Generate similar flashcards using the extracted text
                payload = {
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Original content to base flashcards on:\n\n{extracted_text}"}
                    ],
                    "temperature": 0.8,
                    "max_tokens": 2500
                }
                flashcard_response = make_openai_request('chat/completions', payload)
                
                # Get the generated flashcards
                raw_flashcards = flashcard_response['choices'][0]['message']['content']
                print(f"Generated similar flashcards: {raw_flashcards}")
                
                # Parse the flashcards
                flashcard_list = parse_flashcards(raw_flashcards)
                
                if not flashcard_list:
                    return jsonify({'error': 'Failed to generate similar questions'}), 400
            
            print(f"Total flashcards: {len(flashcard_list)}")
            return jsonify({'flashcards': flashcard_list})
            
        except Exception as e:
            print(f"Error processing image or generating flashcards: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return jsonify({'error': f'Error processing image: {str(e)}'}), 500
    
    except Exception as e:
        print(f"Outer error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Server error occurred'}), 500

def parse_flashcards(raw_text):
    """Parse flashcards from raw text with more flexible format handling."""
    flashcards = []
    current_question = None
    current_answer = None
    
    # Split into lines and process each line
    lines = raw_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for question
        if line.startswith('Q:') or line.lower().startswith('question:'):
            # If we have a previous Q&A pair, save it
            if current_question and current_answer:
                flashcards.append({
                    'question': current_question.strip(),
                    'answer': current_answer.strip()
                })
            # Start new question
            current_question = line.split(':', 1)[1]
            current_answer = None
        # Check for answer
        elif line.startswith('A:') or line.lower().startswith('answer:'):
            if current_question:  # Only store answer if we have a question
                current_answer = line.split(':', 1)[1]
        # If line contains both Q and A
        elif 'Q:' in line and 'A:' in line:
            parts = line.split('A:')
            if len(parts) == 2:
                q_part = parts[0].split('Q:')[1].strip()
                a_part = parts[1].strip()
                flashcards.append({
                    'question': q_part,
                    'answer': a_part
                })
    
    # Don't forget the last pair if it exists
    if current_question and current_answer:
        flashcards.append({
            'question': current_question.strip(),
            'answer': current_answer.strip()
        })
    
    return flashcards

def chunk_content(content, max_chunk_size=50000):
    """Split content into chunks of approximately max_chunk_size characters."""
    # Split content into paragraphs
    paragraphs = content.split('\n\n')
    chunks = []
    current_chunk = []
    current_size = 0
    
    for paragraph in paragraphs:
        paragraph_size = len(paragraph)
        if current_size + paragraph_size > max_chunk_size and current_chunk:
            # Join current chunk and add to chunks
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [paragraph]
            current_size = paragraph_size
        else:
            current_chunk.append(paragraph)
            current_size += paragraph_size
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks

@app.route('/generate_test', methods=['POST'])
def generate_test():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    grade = data.get('grade')
    subject = data.get('subject')
    topic = data.get('topic')
    question_count = data.get('questionCount', 5)
    
    if not all([grade, subject, topic]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        payload = {
            "model": "gpt-4-turbo-preview",
            "messages": [
                {"role": "system", "content": "You are a professional educator creating practice tests."},
                {"role": "user", "content": f"Generate {question_count} practice questions for {subject} at grade {grade} level, focusing on {topic}.\nFor each question:\n1. Provide a clear question\n2. Provide the correct answer\n3. Include a brief explanation\n\nFormat your response as a JSON array with objects containing:\n{{\n    \"question\": \"the question text\",\n    \"answer\": \"the correct answer\",\n    \"explanation\": \"explanation of the answer\"\n}}"}
            ],
            "response_format": "json_object"
        }
        response = make_openai_request('chat/completions', payload)
        
        # Parse the response and ensure it's in the correct format
        content = response['choices'][0]['message']['content']
        questions_data = json.loads(content)
        
        # Ensure we have the expected structure
        if not isinstance(questions_data.get('questions'), list):
            raise ValueError("Invalid response format from AI")
            
        return jsonify(questions_data)
    
    except Exception as e:
        print(f"Error generating test: {str(e)}")
        return jsonify({'error': 'Error generating test'}), 500

@app.route('/generate_upload_test', methods=['POST'])
def generate_upload_test():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        # Read and encode the file
        file_content = file.read()
        base64_image = base64.b64encode(file_content).decode('utf-8')
        
        # Get file extension
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        
        # Create the API request
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a practice problem generator. Generate problems that exactly match the format and style of the given problems. Use the same type of questions but with different numbers or values."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{file_ext};base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Look at these problems carefully. Generate 5 new practice problems that follow EXACTLY the same format and style. For example, if the problems are multiplication like '9x9=', generate similar multiplication problems with different numbers. Keep the difficulty level the same. Format your response as:\nQ1: [Problem]\nA1: [Answer]\nQ2: [Problem]\nA2: [Answer]\n... and so on."
                        }
                    ]
                }
            ],
            "max_tokens": 2048
        }
        response = make_openai_request('chat/completions', payload)
        
        content = response['choices'][0]['message']['content']
        print("GPT Response:", content)  # Debug print
        
        # Parse the response into questions and answers
        questions = []
        lines = content.strip().split('\n')
        current_question = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith(('Q', 'Question')):
                # Extract question text after the number and colon
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_question = parts[1].strip()
            elif line.startswith(('A', 'Answer')) and current_question:
                # Extract answer text after the number and colon
                parts = line.split(':', 1)
                if len(parts) > 1:
                    answer = parts[1].strip()
                    if current_question and answer:  # Only add if both question and answer are non-empty
                        questions.append({
                            'question': current_question,
                            'answer': answer
                        })
                        current_question = None

        # Validate that we have questions
        if not questions:
            print("No questions were parsed from the response")  # Debug print
            return jsonify({'error': 'Failed to generate questions from the material'}), 500

        print("Parsed Questions:", questions)  # Debug print
        return jsonify({'questions': questions})

    except Exception as e:
        print(f"Error processing file: {str(e)}")
        traceback.print_exc()  # Print full traceback
        return jsonify({'error': str(e)}), 500

@app.route('/check_homework', methods=['POST'])
@login_required
def check_homework():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        try:
            # Read and encode the file
            file_content = file.read()
            if not file_content:
                return jsonify({'error': 'Empty file uploaded'}), 400
                
            base64_image = base64.b64encode(file_content).decode('utf-8')
            
            # Get file extension
            if '.' not in file.filename:
                return jsonify({'error': 'File has no extension'}), 400
                
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            if file_ext not in ['jpg', 'jpeg', 'png', 'gif']:
                return jsonify({'error': f'Unsupported file type: {file_ext}'}), 400

            prompt = """
            Analyze this homework solution and respond with a JSON object containing an array of answers.
            For each answer found in the image:
            1. Determine if it's correct or incorrect
            2. Rate your confidence (0-100%)
            3. If incorrect, provide the correct solution
            4. Consider equivalent answers (e.g., '1/2' vs '0.5')

            Return ONLY a JSON object like this (no other text):
            {
                "answers": [
                    {
                        "question_number": 1,
                        "is_correct": true,
                        "confidence": 95,
                        "correct_answer": null,
                        "explanation": null
                    }
                ]
            }
            """
            
            payload = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{file_ext};base64,{base64_image}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                "max_tokens": 2048,
                "temperature": 0.2  # Add lower temperature for more consistent output
            }
            
            print("Making OpenAI API request...")
            response = make_openai_request('chat/completions', payload)
            print("OpenAI API response received")
            
            if not response or 'choices' not in response:
                print("Invalid response structure:", response)
                return jsonify({'error': 'Invalid response from OpenAI API'}), 500
                
            content = response['choices'][0]['message']['content'].strip()
            print("Raw response content:", content)
            
            try:
                # Try to find JSON in the response if there's any extra text
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    content = json_match.group(0)
                
                feedback_data = json.loads(content)
                
                if 'answers' not in feedback_data:
                    print("Missing 'answers' key in parsed data:", feedback_data)
                    return jsonify({'error': 'Invalid response format from OpenAI API'}), 500
                
                # Ensure each answer has all required fields
                for answer in feedback_data['answers']:
                    answer['question_number'] = answer.get('question_number', 0)
                    answer['is_correct'] = answer.get('is_correct', False)
                    answer['confidence'] = answer.get('confidence', 0)
                    answer['correct_answer'] = answer.get('correct_answer', '')
                    answer['explanation'] = answer.get('explanation', '')
                    
                    # Convert confidence to number if it's a string
                    if isinstance(answer['confidence'], str):
                        answer['confidence'] = int(answer['confidence'].rstrip('%'))
                    
                    if answer['confidence'] < 90:
                        answer['needs_review'] = True
                        answer['is_correct'] = None
                
                return jsonify(feedback_data)

            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {str(e)}")
                print(f"Failed content: {content}")
                return jsonify({'error': 'Failed to parse OpenAI response'}), 500
                
            except Exception as e:
                print(f"Error processing response: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Error processing response: {str(e)}'}), 500

        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {str(e)}")
            print(f"Response content: {content}")
            return jsonify({'error': 'Failed to parse OpenAI response'}), 500
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500

    except Exception as e:
        print(f"Outer error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/generate_homework', methods=['POST'])
def generate_homework():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    try:
        # Read and encode the file
        file_content = file.read()
        base64_image = base64.b64encode(file_content).decode('utf-8')
        
        # Get file extension
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        
        # Create the API request
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a homework extractor. Extract problems exactly as they appear in the image."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{file_ext};base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Extract all problems from this homework image. Format your response as:\nQ1: [Problem]\nQ2: [Problem]\n... and so on."
                        }
                    ]
                }
            ],
            "max_tokens": 2048
        }
        response = make_openai_request('chat/completions', payload)
        
        content = response['choices'][0]['message']['content']
        print("GPT Response:", content)  # Debug print
        
        # Parse the response into questions
        questions = []
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith(('Q', 'Question')):
                # Extract question text after the number and colon
                parts = line.split(':', 1)
                if len(parts) > 1:
                    question_text = parts[1].strip()
                    questions.append({'question': question_text})

        # Validate that we have questions
        if not questions:
            print("No questions were parsed from the response")  # Debug print
            return jsonify({'error': 'Failed to extract questions from the material'}), 500

        print("Parsed Questions:", questions)  # Debug print
        return jsonify({'questions': questions})

    except Exception as e:
        print(f"Error processing file: {str(e)}")
        traceback.print_exc()  # Print full traceback
        return jsonify({'error': str(e)}), 500

@app.route('/get_homework_help', methods=['POST'])
def get_homework_help():
    data = request.json
    if not data or 'question' not in data:
        return jsonify({'error': 'No question provided'}), 400

    question = data['question']
    question_number = data.get('questionNumber', 'unknown')
    try:
        payload = {
            "model": "gpt-4-turbo-preview",
            "messages": [
                {
                    "role": "system",
                    "content": """You are a friendly, encouraging teacher helping young students with their homework. Use simple language, be enthusiastic, and make learning fun! Format your response like this:

Hi there! 👋 Ready to learn something cool?

What We're Learning Today: 
🌟 [Explain the topic in super simple, fun terms]
🌟 [Any helpful tricks to remember]

Let's Solve It Together!
Step 1: [First easy step with fun explanation]
   💡 Cool Tip: [Simple hint or trick]

Step 2: [Next step]
   💡 Remember: [Easy way to remember this part]

Step 3: [Keep going with more steps if needed]
   💫 You're doing great!

The Answer Is: [Simple, clear answer]

Let's Check What We Learned:
✨ Did you know? [Fun fact about this type of problem]
✨ Watch out for: [Common mistake explained in a friendly way]

Want to Practice More?
🎮 Try this fun way to remember: [Simple memory trick or game]

You're Amazing! Keep Going! 🌟
Remember: Making mistakes is how we learn and grow! 🌱"""
                },
                {
                    "role": "user",
                    "content": f"Help a young student solve this problem (use simple, encouraging language): {question}"
                }
            ],
            "max_tokens": 2048
        }
        response = make_openai_request('chat/completions', payload)
        
        steps = response['choices'][0]['message']['content']
        return jsonify({'steps': steps})

    except Exception as e:
        print(f"Error generating help for question {question_number}: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Blog API endpoints
@app.route('/api/blogs', methods=['GET'])
def get_blogs():
    try:
        blogs = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
        return jsonify({
            'success': True,
            'blogs': [{
                'id': blog.id,
                'title': blog.title,
                'slug': blog.slug,
                'introduction': blog.introduction,
                'content': blog.content,
                'toc': blog.toc,
                'created_at': blog.created_at.isoformat(),
                'updated_at': blog.updated_at.isoformat()
            } for blog in blogs]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/blogs/<int:blog_id>', methods=['GET'])
def get_blog(blog_id):
    try:
        blog = BlogPost.query.get_or_404(blog_id)
        return jsonify({
            'success': True,
            'blog': {
                'id': blog.id,
                'title': blog.title,
                'slug': blog.slug,
                'introduction': blog.introduction,
                'content': blog.content,
                'toc': blog.toc,
                'created_at': blog.created_at.isoformat(),
                'updated_at': blog.updated_at.isoformat()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/blogs', methods=['POST'])
@login_required
def create_blog():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'introduction', 'content', 'toc']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Generate slug from title
        slug = slugify(data['title'])
        
        # Check if slug already exists
        if BlogPost.query.filter_by(slug=slug).first():
            # Append a number to make it unique
            base_slug = slug
            counter = 1
            while BlogPost.query.filter_by(slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1
        
        blog = BlogPost(
            title=data['title'],
            slug=slug,
            introduction=data['introduction'],
            content=data['content'],
            toc=data['toc']
        )
        
        db.session.add(blog)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'blog': {
                'id': blog.id,
                'title': blog.title,
                'slug': blog.slug,
                'introduction': blog.introduction,
                'content': blog.content,
                'toc': blog.toc,
                'created_at': blog.created_at.isoformat(),
                'updated_at': blog.updated_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/blogs/<int:blog_id>', methods=['PUT'])
@login_required
def update_blog(blog_id):
    try:
        blog = BlogPost.query.get_or_404(blog_id)
        data = request.get_json()
        
        # Update fields if provided
        if 'title' in data:
            blog.title = data['title']
            # Update slug if title changes
            new_slug = slugify(data['title'])
            if new_slug != blog.slug:
                # Check if new slug exists
                if BlogPost.query.filter_by(slug=new_slug).first():
                    base_slug = new_slug
                    counter = 1
                    while BlogPost.query.filter_by(slug=new_slug).first():
                        new_slug = f"{base_slug}-{counter}"
                        counter += 1
                blog.slug = new_slug
                
        if 'introduction' in data:
            blog.introduction = data['introduction']
        if 'content' in data:
            blog.content = data['content']
        if 'toc' in data:
            blog.toc = data['toc']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'blog': {
                'id': blog.id,
                'title': blog.title,
                'slug': blog.slug,
                'introduction': blog.introduction,
                'content': blog.content,
                'toc': blog.toc,
                'created_at': blog.created_at.isoformat(),
                'updated_at': blog.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/blogs/<int:blog_id>', methods=['DELETE'])
@login_required
def delete_blog(blog_id):
    try:
        blog = BlogPost.query.get_or_404(blog_id)
        db.session.delete(blog)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Blog post deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Start the Flask server
    app.run(host='0.0.0.0', port=5000, debug=True)
