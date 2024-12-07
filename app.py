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
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Database configuration
database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'studybuddy.db')
database_url = f'sqlite:///{database_path}'
print(f"Using database: {database_url}")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Create database tables
with app.app_context():
    db.create_all()
    print("Database tables created")

# Login required decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

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
    print("\n=== Login Route ===")
    print(f"Method: {request.method}")
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"Login attempt - Username: {username}")
        print(f"Form data: {request.form}")
        
        user = User.query.filter_by(username=username).first()
        print(f"User found: {user is not None}")
        
        if user:
            password_check = user.check_password(password)
            print(f"Password check result: {password_check}")
            
            if password_check:
                session['user_id'] = user.id
                session['username'] = user.username
                print(f"Login successful for user {username}")
                print(f"Session data: {session}")
                flash('Logged in successfully!')
                return redirect(url_for('index'))
            else:
                print(f"Password check failed for user {username}")
        
        print(f"Login failed for user {username}")
        flash('Invalid username or password')
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('login'))

# Protected routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/flashcards')
@login_required
def flashcards():
    return render_template('flashcards.html')

@app.route('/practice_by_topic')
@login_required
def practice_by_topic():
    return render_template('practice_by_topic.html')

@app.route('/practice_by_upload')
@login_required
def practice_by_upload():
    return render_template('upload_practice_test.html')

@app.route('/homework_checker')
@login_required
def homework_checker():
    return render_template('homework_checker.html')

@app.route('/homework_generator')
@login_required
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

            # Create the API request with a more structured prompt
            prompt = """
            Analyze this homework solution carefully. For each answer:
            1. Determine if it's correct or incorrect
            2. Rate your confidence in this assessment (0-100%)
            3. If incorrect, provide the correct solution
            4. Consider multiple valid forms of the same answer (e.g., '1/2' vs '0.5')
            5. For math problems, check both the final answer and the work shown
            
            Format your response in JSON:
            {
                "answers": [
                    {
                        "question_number": 1,
                        "is_correct": true/false,
                        "confidence": 95,
                        "correct_answer": "only if incorrect",
                        "explanation": "only if incorrect"
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
                "response_format": { "type": "json_object" }
            }
            
            print("Making OpenAI API request...")
            response = make_openai_request('chat/completions', payload)
            print("OpenAI API response received")
            
            if not response:
                return jsonify({'error': 'No response from OpenAI API'}), 500
                
            content = response.get('choices', [{}])[0].get('message', {}).get('content')
            if not content:
                return jsonify({'error': 'Empty response from OpenAI API'}), 500
            
            print("Parsing JSON response...")
            feedback_data = json.loads(content)
            if 'answers' not in feedback_data:
                return jsonify({'error': 'Invalid response format from OpenAI API'}), 500
            
            # Filter out low-confidence assessments
            for answer in feedback_data['answers']:
                if answer.get('confidence', 0) < 90:
                    answer['needs_review'] = True
                    answer['is_correct'] = None
            
            return jsonify(feedback_data)

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
                    "content": "You are a step-by-step solution provider. Provide detailed steps to solve the given problem."
                },
                {
                    "role": "user",
                    "content": f"Provide a step-by-step solution for this problem: {question}"
                }
            ],
            "max_tokens": 2048
        }
        response = make_openai_request('chat/completions', payload)
        
        steps = response['choices'][0]['message']['content']
        print(f"Steps for Question {question_number}:", steps)  # Debug print
        return jsonify({'steps': steps})

    except Exception as e:
        print(f"Error generating help for question {question_number}: {str(e)}")
        traceback.print_exc()  # Print full traceback
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
