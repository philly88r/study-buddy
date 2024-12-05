from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
import os
import requests
import json
import traceback
from dotenv import load_dotenv
import traceback
from flask_cors import CORS
import base64
import io
import sys
from PIL import Image
import time
import threading
from collections import defaultdict
from cachetools import TTLCache
import functools
import random
import re
import hashlib
from openai import OpenAI
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from urllib.parse import urlparse
from datetime import timedelta

# Load environment variables first
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Set up configurations
if os.environ.get('FLASK_ENV') == 'production':
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=60)
    )

# Generate a secure secret key if not provided
def generate_secure_key():
    """Generate a secure random key."""
    try:
        # Try to use secrets module for more secure key generation
        import secrets
        return secrets.token_hex(32)
    except ImportError:
        # Fallback to os.urandom
        return os.urandom(32).hex()

# Set up secret key
secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    secret_key = generate_secure_key()
    print("Notice: Using generated SECRET_KEY for this session")
app.config['SECRET_KEY'] = secret_key

# Database configuration
if os.environ.get('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize database
with app.app_context():
    db.init_app(app)
    try:
        db.create_all()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {str(e)}")

# API Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not found in environment variables")
else:
    print("OpenAI API key found")

try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    # Test the API key
    client.models.list()
    print("OpenAI API connection successful")
except Exception as e:
    print(f"ERROR initializing OpenAI client: {str(e)}")
    client = None

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Rate limiting configuration
from datetime import datetime, timedelta
import time
from queue import Queue
import threading

# Rate limiting settings
RATE_LIMIT_WINDOW = 60  # 1 minute window
MAX_REQUESTS_PER_WINDOW = 50  # Maximum requests per minute
BACKOFF_FACTOR = 2  # Exponential backoff factor
MAX_RETRIES = 3  # Maximum number of retries

class RateLimiter:
    def __init__(self):
        self.requests = []
        self.lock = threading.Lock()
        self.request_queue = Queue()
        self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processing_thread.start()

    def _can_make_request(self):
        now = datetime.now()
        window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
        
        with self.lock:
            # Remove old requests
            self.requests = [req_time for req_time in self.requests if req_time > window_start]
            
            # Check if we can make a new request
            if len(self.requests) < MAX_REQUESTS_PER_WINDOW:
                self.requests.append(now)
                return True
            return False

    def _process_queue(self):
        while True:
            func, args, kwargs, result_queue = self.request_queue.get()
            success = False
            retry_count = 0
            
            while not success and retry_count < MAX_RETRIES:
                if self._can_make_request():
                    try:
                        result = func(*args, **kwargs)
                        result_queue.put(('success', result))
                        success = True
                    except Exception as e:
                        if 'rate limit' in str(e).lower():
                            retry_count += 1
                            wait_time = BACKOFF_FACTOR ** retry_count
                            time.sleep(wait_time)
                        else:
                            result_queue.put(('error', str(e)))
                            break
                else:
                    time.sleep(1)
            
            if not success:
                result_queue.put(('error', 'Rate limit exceeded after maximum retries'))
            
            self.request_queue.task_done()

    def execute(self, func, *args, **kwargs):
        result_queue = Queue()
        self.request_queue.put((func, args, kwargs, result_queue))
        status, result = result_queue.get()
        
        if status == 'error':
            raise Exception(result)
        return result

# Initialize rate limiter
rate_limiter = RateLimiter()

# Initialize cache for storing extracted text and generated problems
PROBLEMS_CACHE = {}
CACHE_TIMEOUT = 3600  # Cache timeout in seconds (1 hour)

def get_cache_key(data):
    return hashlib.md5(str(data).encode()).hexdigest()

# Set console encoding to UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Initialize template and static folders
template_dir = 'c:/Users/info/Desktop/ai_tutor-20241203T025709Z-001/ai_tutor/templates'
static_dir = 'c:/Users/info/Desktop/ai_tutor-20241203T025709Z-001/ai_tutor/static'
app.template_folder = template_dir
app.static_folder = static_dir

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Main routes
@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error rendering index template: {str(e)}")
        return render_template('error.html', error="An error occurred while loading the page. Please try again.")

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')

@app.route('/flashcards')
@login_required
def flashcards():
    return render_template('flashcards.html')

@app.route('/practice-by-topic')
@login_required
def practice_by_topic():
    return render_template('practice_by_topic.html')

@app.route('/homework-generator')
@login_required
def homework_generator():
    return render_template('homework_generator.html')

@app.route('/practice-by-upload')
@login_required
def practice_by_upload():
    return render_template('upload_practice_test.html')

# Homework related routes
@app.route('/homework', methods=['GET', 'POST'])
@login_required
def homework():
    if request.method == 'GET':
        return render_template('homework.html')
    
    # Handle POST request
    data = request.get_json()
    problem = data.get('problem', '')
    subject = data.get('subject', '')
    grade_level = data.get('grade_level', '')

    # Call OpenAI API for help
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful tutor assisting with homework problems."},
            {"role": "user", "content": f"Please help me solve this {subject} problem for grade {grade_level}: {problem}"}
        ]
    )
    
    help_text = response.choices[0].message.content
    return jsonify({'help': help_text})

@app.route('/homework-checker')
@login_required
def homework_checker():
    return render_template('homework_checker.html')

@app.route('/homework-upload', methods=['POST'])
@login_required
def homework_upload():
    if 'homework' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['homework']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    try:
        # Read and encode the file
        file_content = file.read()
        base64_image = base64.b64encode(file_content).decode('utf-8')
        
        # Get file extension
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        
        # Create the API request
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
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
                            "text": "Extract all the problems from this homework image. Format them as a JSON array with 'question' and 'answer' fields. For math problems, calculate the answers. For other subjects, leave the answer field empty."
                        }
                    ]
                }
            ],
            max_tokens=2048
        )
        
        # Extract the response text
        response_text = response.choices[0].message.content
        
        try:
            # Try to parse as JSON directly
            problems = json.loads(response_text)
        except json.JSONDecodeError:
            # If not valid JSON, try to extract problems manually
            problems = extract_problems_from_response(response_text)
        
        if not problems:
            return jsonify({'error': 'No problems could be extracted from the image'}), 400

        # Store problems in session for later use
        session['problems'] = problems
        return jsonify({'problems': problems})

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_problem_help', methods=['POST'])
@login_required
def get_problem_help():
    data = request.get_json()
    if not data or 'problem_text' not in data:
        return jsonify({'error': 'No problem text provided'}), 400

    problem_text = data['problem_text']
    try:
        # Generate step-by-step help using OpenAI
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a helpful math tutor. Provide step-by-step guidance for solving the problem, but don't give away the answer. Focus on teaching the problem-solving process."},
                {"role": "user", "content": f"Help me solve this problem step by step: {problem_text}"}
            ]
        )
        
        # Parse the steps from the response
        help_text = response.choices[0].message.content
        steps = [step.strip() for step in help_text.split('\n') if step.strip()]
        
        return jsonify({
            'steps': steps
        })
    
    except Exception as e:
        print(f"Error generating help: {str(e)}")
        return jsonify({'error': 'Error generating help steps'}), 500

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file:
        try:
            # Read the image file
            image_bytes = file.read()
            
            # Construct the prompt for homework problems
            prompt = """Analyze this homework image and create practice problems based on it.
For each problem:
1. Create a clear, specific question based on the content
2. Provide the correct answer
3. Format as:
   Question: [question here]
   Answer: [answer here]

Include at least 5 problems that test understanding of the concepts shown.
Make sure the answers are specific and can be automatically checked."""
            
            # Get response from Gemini
            response = get_gemini_response(image_bytes=image_bytes, text_prompt=prompt)
            if not response:
                return jsonify({'error': 'Failed to process image'}), 500
            
            # Parse the problems from the response
            problems = []
            current_question = None
            
            for line in response.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('Question:'):
                    if current_question and current_question.get('answer'):
                        problems.append(current_question)
                    current_question = {'question': line[9:].strip(), 'answer': ''}
                elif line.startswith('Answer:') and current_question:
                    current_question['answer'] = line[7:].strip()
            
            # Add the last problem if complete
            if current_question and current_question.get('answer'):
                problems.append(current_question)
            
            if not problems:
                return jsonify({'error': 'No problems could be generated from the image'}), 400
            
            return jsonify({'problems': problems})
            
        except Exception as e:
            print(f"Error processing upload: {e}")
            return jsonify({'error': str(e)}), 500

# Handle answer checking
@app.route('/check', methods=['POST'])
@login_required
def check_answer():
    # Only accept POST requests with JSON content
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
        
    try:
        print("Received check answer request")
        data = request.get_json()
        print("Request data:", data)
        
        if not data:
            print("No data received")
            return jsonify({'error': 'No data provided'}), 400
            
        problem_text = data.get('problem_text')
        answer = data.get('answer')
        print(f"Problem: {problem_text}, Answer: {answer}")
        
        if not problem_text:
            return jsonify({'error': 'Problem text is required'}), 400
        if not answer:
            return jsonify({'error': 'Answer is required'}), 400
            
        try:
            # Try to solve the problem directly first
            problem_text = problem_text.replace('×', '*').replace('x', '*')
            # Extract numbers from the problem
            numbers = [int(n) for n in re.findall(r'\d+', problem_text)]
            print("Extracted numbers:", numbers)
            
            if len(numbers) != 2:
                return jsonify({'error': 'Invalid problem format'}), 400
                
            correct_answer = numbers[0] * numbers[1]
            user_answer = int(answer)
            print(f"Correct answer: {correct_answer}, User answer: {user_answer}")
            
            result = {
                'correct': user_answer == correct_answer,
                'correct_answer': correct_answer
            }
            print("Returning result:", result)
            return jsonify(result)
            
        except ValueError as e:
            print(f"Value error: {str(e)}")
            return jsonify({'error': 'Please enter a valid number'}), 400
        except Exception as e:
            print(f"Error parsing problem: {str(e)}")
            return jsonify({'error': 'Could not parse the problem'}), 500
            
    except Exception as e:
        print(f"Error in check_answer: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/check-all', methods=['POST'])
@login_required
def check_all_answers():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
        
    try:
        data = request.get_json()
        if not data or 'answers' not in data:
            return jsonify({'error': 'No answers provided'}), 400
            
        answers = data['answers']
        results = []
        
        for answer_data in answers:
            try:
                problem_text = answer_data.get('problem_text', '').replace('×', '*').replace('x', '*')
                answer = answer_data.get('answer', '').strip()
                
                # Extract numbers from the problem
                numbers = [int(n) for n in re.findall(r'\d+', problem_text)]
                if len(numbers) != 2:
                    results.append({
                        'correct': False,
                        'error': 'Invalid problem format'
                    })
                    continue
                    
                correct_answer = numbers[0] * numbers[1]
                user_answer = int(answer)
                
                results.append({
                    'correct': user_answer == correct_answer,
                    'correct_answer': correct_answer
                })
                
            except ValueError:
                results.append({
                    'correct': False,
                    'error': 'Please enter a valid number'
                })
            except Exception as e:
                results.append({
                    'correct': False,
                    'error': str(e)
                })
                
        return jsonify(results)
        
    except Exception as e:
        print(f"Error checking answers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/learn', methods=['POST'])
@login_required
def learn_problem():
    try:
        print("Received learn request")
        data = request.get_json()
        print("Request data:", data)
        
        if not data:
            print("No JSON data received")
            return jsonify({'error': 'No JSON data received'}), 400
            
        problem_text = data.get('problem_text')
        print("Problem text:", problem_text)
        
        if not problem_text:
            print("Problem text is missing")
            return jsonify({'error': 'Problem text is required'}), 400
        
        # Create the prompt for Gemini
        prompt = f"""You are helping a 3rd grader solve this multiplication problem: {problem_text}

Please explain how to solve it in simple steps. Use language a third grader would understand.
Show two different ways to solve it:
1. Using repeated addition
2. Using groups or arrays

Keep it fun and use emojis! Make sure to show each step clearly."""
        
        print("Generated prompt:", prompt)
        
        # Call Gemini API
        headers = {
            'Content-Type': 'application/json'
        }
        
        data = {
            "contents": [{
                "parts": [
                    {"text": prompt}
                ]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "topK": 32,
                "topP": 1,
                "maxOutputTokens": 2048,
            }
        }

        print("Sending request to Gemini")
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent",
            headers=headers,
            json=data
        )
        
        print("Gemini response status:", response.status_code)
        if response.status_code != 200:
            print("Gemini error response:", response.text)
            return jsonify({'error': 'Failed to get explanation'}), 500
            
        result = response.json()
        if not result.get('candidates', []):
            print("No candidates in response:", result)
            return jsonify({'error': 'No explanation generated'}), 500
            
        explanation = result['candidates'][0]['content']['parts'][0]['text']
        print("Generated explanation:", explanation)
        return jsonify({'explanation': explanation})
        
    except Exception as e:
        print(f"Error in learn_problem: {str(e)}")
        print("Full error:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/check-homework', methods=['POST'])
@login_required
def check_homework():
    try:
        # Log incoming request
        print("Received homework analysis request")
        
        data = request.get_json()
        if not data or 'problems' not in data:
            print("Error: No problems provided in request")
            return jsonify({'error': 'No problems provided'}), 400

        problems = data['problems']
        print(f"Processing {len(problems)} problems")
        
        if not problems:
            print("Error: Empty problems list")
            return jsonify({'error': 'No problems to analyze'}), 400

        # First, have AI solve the problems to get correct answers
        solve_prompt = """Solve these homework problems. For each problem:
1. Extract the question
2. Solve it step by step
3. Provide the final answer

Return your response in this exact JSON format:
{
    "problems": [
        {
            "question": "problem text",
            "solution": "step by step solution",
            "correct_answer": "final answer"
        }
    ]
}

Problems to solve:
"""
        for i, problem in enumerate(problems, 1):
            solve_prompt += f"\n{i}. {problem['question']}\n"
        
        print("Sending request to OpenAI for solutions")
        try:
            solution_response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful math tutor. Solve these problems and return the solution in the exact JSON format specified."},
                    {"role": "user", "content": solve_prompt}
                ]
            )
            print("Received solution response from OpenAI")
        except Exception as e:
            print(f"OpenAI API error (solutions): {str(e)}")
            return jsonify({'error': f'Error getting solutions: {str(e)}'}), 500
        
        try:
            solutions = json.loads(solution_response.choices[0].message.content)
            print("Successfully parsed solutions JSON")
        except json.JSONDecodeError as e:
            print(f"JSON parsing error (solutions): {str(e)}")
            print(f"Raw response: {solution_response.choices[0].message.content}")
            return jsonify({'error': 'Invalid response format from AI'}), 500
        
        # Now have AI check the student's work against the solutions
        check_prompt = """Compare the student's work with the correct solutions. For each problem:
1. Determine if the student's answer matches the correct answer
2. For incorrect answers only, provide a helpful explanation

Return your response in this exact JSON format:
{
    "results": [
        {
            "question": "problem text",
            "student_answer": "extracted student answer",
            "correct_answer": "actual correct answer",
            "is_correct": true/false,
            "explanation": "explanation if incorrect, otherwise null"
        }
    ]
}

Problems to check:
"""
        for i, (problem, solution) in enumerate(zip(problems, solutions['problems']), 1):
            check_prompt += f"\n{i}. Problem: {problem['question']}"
            check_prompt += f"\n   Student answer: {problem.get('answer', '')}"
            check_prompt += f"\n   Correct answer: {solution['correct_answer']}\n"
        
        print("Sending request to OpenAI for checking")
        try:
            check_response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful math tutor. Compare the student's work with the correct solutions and return the results in the exact JSON format specified."},
                    {"role": "user", "content": check_prompt}
                ]
            )
            print("Received check response from OpenAI")
        except Exception as e:
            print(f"OpenAI API error (checking): {str(e)}")
            return jsonify({'error': f'Error checking answers: {str(e)}'}), 500
        
        try:
            results = json.loads(check_response.choices[0].message.content)
            print("Successfully parsed results JSON")
        except json.JSONDecodeError as e:
            print(f"JSON parsing error (results): {str(e)}")
            print(f"Raw response: {check_response.choices[0].message.content}")
            return jsonify({'error': 'Invalid response format from AI'}), 500
        
        print("Successfully completed homework analysis")
        return jsonify(results)
        
    except Exception as e:
        print(f"Unexpected error in analyze_homework: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/test')
def test():
    return "Test route working!"

@app.route('/study_guide')
def study_guide():
    try:
        return render_template('study_guide.html')
    except Exception as e:
        error_msg = f"Error in study_guide route: {str(e)}"
        print(f"Debug: {error_msg}")
        return render_template('study_guide.html', error=error_msg)

@app.route('/generate_from_topic', methods=['POST'])
@login_required
def generate_from_topic():
    try:
        data = request.get_json()
        if not data or 'subject' not in data or 'topic' not in data:
            return jsonify({'error': 'Subject and topic are required'}), 400

        subject = data['subject']
        topic = data['topic']
        grade_level = data.get('gradeLevel', 'high school')
        num_questions = min(int(data.get('numQuestions', 5)), 20)  # Cap at 20 questions

        prompt = f"""Create {num_questions} practice test questions about {subject} focusing on {topic} at {grade_level} level. 
For each question:
1. The question should be clear and grade-appropriate
2. Provide a specific, correct answer
3. Format each question and answer pair as:
   Question: [question here]
   Answer: [specific answer here]

Example format:
Question: What is 5 + 7?
Answer: 12

Question: What is the capital of France?
Answer: Paris

Please generate exactly {num_questions} questions following this format."""

        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {'role': 'system', 'content': 'You are a helpful tutor creating practice problems.'},
                {'role': 'user', 'content': prompt}
            ],
            max_tokens=4000
        )

        content = response.choices[0].message.content
        
        # Parse questions and answers
        questions = []
        current_question = {'question': '', 'answer': ''}
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.lower().startswith(('question', 'q:', 'q.')):
                if current_question['question']:  # Save previous question
                    questions.append(dict(current_question))
                    current_question = {'question': '', 'answer': ''}
                current_question['question'] = line.split(':', 1)[1].strip() if ':' in line else line
            elif line.lower().startswith(('answer', 'a:', 'a.')):
                current_question['answer'] = line.split(':', 1)[1].strip() if ':' in line else line

        # Add the last question if it exists
        if current_question['question'] and current_question['answer']:
            questions.append(current_question)

        if not questions:
            return jsonify({'error': 'No problems could be parsed'}), 500

        return jsonify({'problems': questions})

    except Exception as e:
        print(f"Error in generate_from_topic: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/check_answers', methods=['POST'])
@login_required
def check_answers():
    try:
        data = request.get_json()
        if not data or 'answers' not in data:
            return jsonify({'error': 'No answers provided'}), 400

        user_answers = data['answers']
        correct_answers = session.get('correct_answers', [])
        
        if not correct_answers:
            return jsonify({'error': 'No correct answers found in session'}), 400
        
        if len(user_answers) != len(correct_answers):
            return jsonify({'error': 'Invalid number of answers'}), 400

        results = []
        correct_count = 0
        
        for i, (user_ans, correct_ans) in enumerate(zip(user_answers, correct_answers)):
            is_correct = check_answer(user_ans, correct_ans)
            if is_correct:
                correct_count += 1
            
            results.append({
                'correct': is_correct,
                'message': f'{"Correct!" if is_correct else "Incorrect."} Your answer: {user_ans}. Correct answer: {correct_ans}'
            })

        response_data = {
            'score': {
                'correct': correct_count,
                'total': len(correct_answers)
            },
            'feedback': results
        }
        
        return jsonify(response_data)

    except Exception as e:
        print(f"Error in check_answers: {str(e)}")
        return jsonify({'error': str(e)}), 500

def check_answer(user_answer, correct_answer):
    """Compare user answer with correct answer, handling different formats."""
    if not user_answer or not correct_answer:
        return False
        
    user_ans = str(user_answer).strip().lower()
    correct_ans = str(correct_answer).strip().lower()
    
    # Remove punctuation and extra whitespace
    user_ans = ' '.join(user_ans.split())
    correct_ans = ' '.join(correct_ans.split())
    
    # Direct match
    if user_ans == correct_ans:
        return True
        
    # Number comparison (if both are numbers)
    try:
        user_num = float(user_ans)
        correct_num = float(correct_ans)
        return abs(user_num - correct_num) < 0.01  # Allow small difference for decimals
    except ValueError:
        pass
    
    return False

@app.route('/test_template')
def test_template():
    try:
        print("Attempting to render test.html")
        return render_template('test.html')
    except Exception as e:
        print(f"Error rendering test template: {str(e)}")
        return str(e), 500

@app.route('/simple_test')
def simple_test():
    return """
    <html>
        <head><title>Simple Test</title></head>
        <body>
            <h1>Simple Test Page</h1>
            <p>This is a test page without using templates.</p>
            <a href="/study_guide">Go to Study Guide</a>
        </body>
    </html>
    """

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/generate_from_documents', methods=['POST'])
@login_required
def generate_from_documents():
    try:
        print("Debug: Files in request:", request.files)
        print("Debug: Form data:", request.form)
        print("Debug: Content type:", request.content_type)
        print("Debug: Request headers:", dict(request.headers))

        if 'files[]' not in request.files:
            print("Debug: 'files[]' not found in request.files")
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['files[]']
        print("Debug: Received file:", file.filename)
        print("Debug: File content type:", file.content_type)

        if not file or file.filename == '':
            print("Debug: No file selected")
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            print(f"Debug: Invalid file type for {file.filename}")
            return jsonify({'error': 'Invalid file type. Please upload a PDF, JPG, or PNG file.'}), 400

        # Generate cache key from file content
        file_content = file.read()
        cache_key = get_cache_key(file_content)
        file.seek(0)  # Reset file pointer after reading

        # Try to get extracted text from cache
        if cache_key in PROBLEMS_CACHE:
            cache_time, problems = PROBLEMS_CACHE[cache_key]
            if time.time() - cache_time < CACHE_TIMEOUT:
                print("Debug: Using cached text")
                return jsonify({'problems': problems})

        try:
            # For images
            if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                print("Debug: Processing image file")
                try:
                    # Create a copy of the file in memory
                    file_copy = io.BytesIO(file_content)
                    
                    # Try to open the image
                    try:
                        image = Image.open(file_copy)
                        print("Debug: Image opened successfully")
                        print("Debug: Image size:", image.size)
                        print("Debug: Image mode:", image.mode)
                    except Exception as e:
                        print("Debug: Error opening image:", str(e))
                        return jsonify({'error': 'Could not open image file'}), 400
                    
                    # Process the image
                    text = process_image(image)
                    if text:
                        PROBLEMS_CACHE[cache_key] = (time.time(), text)
                    print("Debug: Extracted text:", text[:100] if text else None)
                except Exception as e:
                    print("Debug: Error processing file data:", str(e))
                    return jsonify({'error': 'Error processing image data'}), 400
            # For PDFs (to be implemented)
            elif file.filename.lower().endswith('.pdf'):
                return jsonify({'error': 'PDF processing not yet implemented'}), 400
            else:
                return jsonify({'error': 'Unsupported file type'}), 400

        except Exception as e:
            print(f"Error processing file: {str(e)}")
            print("Debug: Full error:", traceback.format_exc())
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500

        if not text:
            print("Debug: No text extracted from file")
            return jsonify({'error': 'No text could be extracted from the file'}), 400

        # Try to get problems from cache using the extracted text as key
        problems_cache_key = get_cache_key(text)
        if problems_cache_key in PROBLEMS_CACHE:
            print("Debug: Using cached problems")
            return jsonify({'problems': PROBLEMS_CACHE[problems_cache_key][1]})

        # Generate practice problems using Gemini
        prompt = f"""Based on the following study material, generate 5 practice problems:
        {text}
        
        Format each problem as:
        Question: [clear, specific question]
        Answer: [concise, correct answer]
        
        Make the problems challenging but fair, testing understanding rather than memorization."""

        print("Debug: Sending prompt to Gemini")
        response = get_gemini_response(text_prompt=prompt)
        if not response:
            print("Debug: No response from Gemini")
            return jsonify({'error': 'Failed to generate practice problems'}), 500

        problems = extract_problems_from_response(response)
        print("Debug: Extracted problems:", problems)
        
        if not problems:
            return jsonify({'error': 'No valid problems could be generated'}), 500

        # Cache the generated problems
        PROBLEMS_CACHE[problems_cache_key] = (time.time(), problems)

        return jsonify({'problems': problems})

    except Exception as e:
        print(f"Error in generate_from_documents: {str(e)}")
        print("Debug: Full traceback:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/analyze_homework', methods=['POST'])
@login_required
def analyze_homework():
    try:
        print("Starting analyze_homework endpoint")
        print(f"User: {current_user.id if current_user.is_authenticated else 'Not authenticated'}")
        
        if not client:
            print("OpenAI client not initialized")
            return jsonify({'error': 'OpenAI service not available. Please check your API key.'}), 503
        
        if 'file' not in request.files:
            print("No file in request.files")
            print(f"Files received: {request.files}")
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            print(f"Invalid file: {file.filename if file else 'No file'}")
            return jsonify({'error': 'Invalid file type'}), 400

        print(f"Processing file: {file.filename}")
        # Read the image file
        image_bytes = file.read()
        
        # Convert to base64 for API
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Call GPT-4 Vision to analyze the homework
        try:
            print("Calling OpenAI API")
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a helpful math tutor analyzing homework. For each problem in the image:
1. Extract the question and student's answer
2. Determine if the answer is correct
3. For incorrect answers, provide a clear explanation
Return your analysis in this exact JSON format:
{
    "results": [
        {
            "question": "problem text",
            "student_answer": "student's written answer",
            "correct_answer": "actual correct answer",
            "is_correct": true/false,
            "explanation": "explanation if incorrect, otherwise null"
        }
    ]
}"""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please analyze this homework and check if the answers are correct. Return the results in the specified JSON format."
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
                max_tokens=4000
            )
            
            # Parse the response
            content = response.choices[0].message.content
            try:
                results = json.loads(content)
                return jsonify(results)
            except json.JSONDecodeError:
                print(f"Failed to parse JSON response: {content}")
                return jsonify({'error': 'Invalid response format from AI'}), 500
                
        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            return jsonify({'error': f'Error analyzing homework: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Error in analyze_homework: {str(e)}")
        print("Full error:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/generate_flashcards', methods=['POST'])
@login_required
def generate_flashcards():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        card_type = request.form.get('type', 'exact')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        try:
            # Read and encode the image
            image_data = file.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare the system message based on card type
            if card_type == 'exact':
                system_message = """You are a helpful AI that creates flashcards from study materials. 
                Extract EXACTLY the questions and answers that appear in the image. Format them as a JSON array of 
                {question, answer} pairs. Do not create new questions - only use what's in the image."""
            else:
                system_message = """You are a helpful AI that creates flashcards from study materials. 
                Analyze the content and create 15-20 similar but different questions that test the same concepts. 
                Make sure the questions are varied and test different aspects of understanding. 
                Format them as a JSON array of {question, answer} pairs."""
            
            # Call OpenAI API using the client
            response = client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "system",
                        "content": system_message
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Create flashcards from this study material. Return them in this exact format: [{\"question\": \"Q1\", \"answer\": \"A1\"}, {\"question\": \"Q2\", \"answer\": \"A2\"}]"
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
                max_tokens=4000
            )
            
            # Extract the flashcards from the response
            flashcards_text = response.choices[0].message.content
            # Find the JSON array in the response
            flashcards_match = re.search(r'\[.*\]', flashcards_text, re.DOTALL)
            if not flashcards_match:
                return jsonify({'error': 'Failed to parse flashcards'}), 500
            
            flashcards = json.loads(flashcards_match.group())
            return jsonify({'flashcards': flashcards})
            
        except Exception as e:
            print(f"Error: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate_homework', methods=['POST'])
@login_required
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
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
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
            max_tokens=2048
        )
        
        content = response.choices[0].message.content
        
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
@login_required
def get_homework_help():
    data = request.json
    if not data or 'question' not in data:
        return jsonify({'error': 'No question provided'}), 400

    question = data['question']
    question_number = data.get('questionNumber', 'unknown')
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a step-by-step solution provider. Provide detailed steps to solve the given problem."
                },
                {
                    "role": "user",
                    "content": f"Provide a step-by-step solution for this problem: {question}"
                }
            ],
            max_tokens=2048
        )
        
        steps = response.choices[0].message.content
        print(f"Steps for Question {question_number}:", steps)  # Debug print
        return jsonify({'steps': steps})

    except Exception as e:
        print(f"Error generating help for question {question_number}: {str(e)}")
        traceback.print_exc()  # Print full traceback
        return jsonify({'error': str(e)}), 500

@app.route('/generate_test', methods=['POST'])
@login_required
def generate_test():
    try:
        if not GEMINI_API_KEY:
            return jsonify({"error": "Gemini API key not found"}), 500

        data = request.get_json()
        grade = data.get('grade')
        subject = data.get('subject')
        topic = data.get('topic')
        question_count = int(data.get('questionCount', 5))
        
        if not all([grade, subject, topic]):
            return jsonify({"error": "Missing required fields"}), 400

        # Construct the prompt for Gemini
        prompt = f"""Generate {question_count} practice test questions for grade {grade} {subject} about {topic}.
For each question:
1. The question should be clear and grade-appropriate
2. Provide a specific, correct answer that can be automatically checked
3. Format each question and answer pair as:
   Question: [your question here]
   Answer: [specific answer here]

Example format:
Question: What is 5 + 7?
Answer: 12

Question: What is the capital of France?
Answer: Paris

Please generate exactly {question_count} questions following this format."""

        # Call Gemini API
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_API_KEY
            },
            json={
                "contents": [{
                    "parts": [
                        {"text": prompt}
                    ]
                }]
            }
        )

        # Print response for debugging
        print("Gemini API Response:", response.status_code)
        print("Response Text:", response.text)

        if response.status_code != 200:
            return jsonify({"error": f"Failed to generate questions. Status: {response.status_code}"}), 500

        # Parse Gemini response
        response_data = response.json()
        if not response_data.get('candidates', []):
            return jsonify({"error": "No response from AI model"}), 500

        text_content = response_data['candidates'][0]['content']['parts'][0]['text']
        
        # Parse questions and answers
        questions = []
        current_question = None
        lines = text_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('Question:'):
                if current_question and current_question.get('answer'):  # Only add if it has both question and answer
                    questions.append(current_question)
                current_question = {'question': line[9:].strip(), 'answer': ''}
                i = 1
                
                # Collect all text until the next Question or end
                while i < len(lines) and not lines[i].strip().startswith('Question'):
                    line = lines[i].strip()
                    
                    if line.startswith('Answer:'):
                        current_question['answer'] = line[7:].strip()
                    i += 1
            else:
                i += 1
                
        if current_question:
            questions.append(current_question)

        print("Generated Questions:", questions)  # Debug print
        return jsonify({"questions": questions})

    except Exception as e:
        print(f"Error generating test: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/upload_practice_test')
@login_required
def upload_practice_test():
    return render_template('upload_practice_test.html')

@app.route('/generate_upload_test', methods=['POST'])
@login_required
def generate_upload_test():
    try:
        if not GEMINI_API_KEY:
            return jsonify({"error": "Gemini API key not found"}), 500

        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        try:
            # Read image file and encode in base64
            image_bytes = file.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            grade = request.form.get('grade')
            question_count = int(request.form.get('questionCount', 5))

            if not grade:
                return jsonify({"error": "Missing grade level"}), 400

            # Construct the prompt for Gemini
            prompt = f"""Analyze this image and generate {question_count} practice test questions for grade {grade} students.
The questions should test understanding of the key concepts shown in the image.

For each question:
1. The question should be clear and grade-appropriate
2. Provide a specific, correct answer that can be automatically checked
3. Format each question and answer pair as:
   Question: [your question here]
   Answer: [specific answer here]

Example format:
Question: What is 5 + 7?
Answer: 12

Question: What is the capital of France?
Answer: Paris

Please generate {question_count} questions following this exact format."""

            # Call Gemini API with image
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent",
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": GEMINI_API_KEY
                },
                json={
                    "contents": [{
                        "parts": [
                            {
                                "text": prompt
                            },
                            {
                                "inlineData": {
                                    "mimeType": "image/jpeg",
                                    "data": image_base64
                                }
                            }
                        ]
                    }]
                }
            )

            # Print response for debugging
            print("Gemini API Response:", response.status_code)
            print("Response Text:", response.text)

            if response.status_code != 200:
                return jsonify({"error": f"Failed to generate questions. Status: {response.status_code}"}), 500

            # Parse Gemini response
            response_data = response.json()
            if not response_data.get('candidates', []):
                return jsonify({"error": "No response from AI model"}), 500

            text_content = response_data['candidates'][0]['content']['parts'][0]['text']
            
            # Parse questions and answers
            questions = []
            current_question = None
            
            for line in text_content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('Question:'):
                    if current_question and current_question.get('answer'):  # Only add if it has both question and answer
                        questions.append(current_question)
                    current_question = {'question': line[9:].strip(), 'answer': ''}
                elif line.startswith('Answer:') and current_question:
                    current_question['answer'] = line[7:].strip()
                    
            # Add the last question if it's complete
            if current_question and current_question.get('answer'):
                questions.append(current_question)

            if not questions:
                return jsonify({"error": "No valid questions generated"}), 500

            print("Generated Questions:", questions)  # Debug print
            return jsonify({"questions": questions})

        except Exception as e:
            print(f"Error generating test: {str(e)}")
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        print(f"Error generating test: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/practice_test')
@login_required
def practice_test():
    """Render the practice test page"""
    return render_template('practice_test.html')

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not email or not password:
                flash('Please provide both email and password', 'error')
                return render_template('login.html')
            
            try:
                user = User.query.filter_by(email=email).first()
                if user and check_password_hash(user.password, password):
                    login_user(user)
                    next_page = request.args.get('next')
                    if not next_page or urlparse(next_page).netloc != '':
                        next_page = url_for('dashboard')
                    return redirect(next_page)
                else:
                    flash('Invalid email or password', 'error')
            except Exception as e:
                print(f"Database error during login: {str(e)}")
                flash('An error occurred while accessing the database. Please try again.', 'error')
                
        return render_template('login.html')
    except Exception as e:
        print(f"Unexpected error in login route: {str(e)}")
        return render_template('error.html', error="An unexpected error occurred. Please try again later.")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not email or not password:
                flash('Please provide both email and password', 'error')
                return render_template('signup.html')
            
            try:
                if User.query.filter_by(email=email).first():
                    flash('Email already registered', 'error')
                    return render_template('signup.html')
                
                hashed_password = generate_password_hash(password)
                new_user = User(email=email, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                print(f"Database error during signup: {str(e)}")
                flash('An error occurred while creating your account. Please try again.', 'error')
                
        return render_template('signup.html')
    except Exception as e:
        print(f"Unexpected error in signup route: {str(e)}")
        return render_template('error.html', error="An unexpected error occurred. Please try again later.")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def validate_configuration():
    """Validate all required configurations and API keys on startup."""
    config_status = {
        'openai_api': False,
        'secret_key': False,
        'database': False
    }
    
    # Check OpenAI API
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not found in environment variables")
    else:
        try:
            test_client = OpenAI(api_key=OPENAI_API_KEY)
            # Simple API test
            test_client.models.list()
            config_status['openai_api'] = True
            print("✓ OpenAI API configuration validated")
        except Exception as e:
            print(f"ERROR: OpenAI API validation failed: {str(e)}")
    
    # Check Secret Key
    if not app.config['SECRET_KEY']:
        print("ERROR: SECRET_KEY not found in environment variables")
    else:
        config_status['secret_key'] = True
        print("✓ Secret key configuration validated")
    
    # Check Database
    try:
        with app.app_context():
            db.create_all()
        config_status['database'] = True
        print("✓ Database configuration validated")
    except Exception as e:
        print(f"ERROR: Database validation failed: {str(e)}")
    
    # Overall status
    if all(config_status.values()):
        print("\n✓ All configurations validated successfully")
    else:
        failed = [k for k, v in config_status.items() if not v]
        print(f"\n⚠ Configuration validation failed for: {', '.join(failed)}")
        print("The application may not function correctly without these configurations.")

# Run configuration validation at startup
validate_configuration()

if __name__ == '__main__':
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=True)
