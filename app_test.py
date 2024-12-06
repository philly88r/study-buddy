from flask import Flask, render_template, request, jsonify
import os
from openai import OpenAI
from functools import wraps
from datetime import datetime, timedelta
import threading
import logging
import base64
from PIL import Image
import io
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

app = Flask(__name__, 
    template_folder=template_dir,
    static_folder=static_dir
)

# Enable debug mode and detailed error messages
app.config['DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize OpenAI client
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    logger.error("OpenAI API key not found in environment variables!")

# Rate limiting configuration
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
MAX_REQUESTS_PER_WINDOW = 50  # Maximum requests per hour
rate_limit_data = {
    'requests': [],
    'lock': threading.Lock()
}

def encode_image(image_file):
    """Convert image file to base64 string"""
    try:
        # Open and convert image to RGB if needed
        img = Image.open(image_file)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Convert to JPEG format in memory
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        
        return base64.b64encode(img_byte_arr).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding image: {str(e)}")
        raise

def extract_questions_from_image(image_base64, grade_level):
    """Extract questions from image using OpenAI's Vision API"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful AI tutor. Your task is to extract homework questions from the image and format them clearly. Return only the questions, numbered."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"This is a grade {grade_level} homework assignment. Please extract all questions from this image. Format them as a numbered list."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        # Extract questions from the response
        content = response.choices[0].message.content
        questions = []
        
        # Split content into lines and process each line
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and any(line.startswith(str(i) + '.') for i in range(1, 100)):
                # Remove the number and dot from the start
                question_text = '.'.join(line.split('.')[1:]).strip()
                if question_text:
                    questions.append({"question": question_text})
        
        return questions
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        raise

def generate_step_by_step_help(question, grade_level):
    """Generate step-by-step help for a question using OpenAI"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a helpful tutor for grade {grade_level} students. Provide clear, step-by-step guidance for solving homework problems."
                },
                {
                    "role": "user",
                    "content": f"Please provide step-by-step help for solving this question: {question}"
                }
            ],
            max_tokens=500
        )
        
        steps = response.choices[0].message.content.strip().split('\n')
        return [step.strip() for step in steps if step.strip()]
    except Exception as e:
        logger.error(f"Error generating help: {str(e)}")
        raise

def is_rate_limited():
    """Check if the current request should be rate limited"""
    current_time = datetime.now()
    with rate_limit_data['lock']:
        # Remove old requests
        rate_limit_data['requests'] = [
            req_time for req_time in rate_limit_data['requests']
            if current_time - req_time < timedelta(seconds=RATE_LIMIT_WINDOW)
        ]
        
        # Check if we're over the limit
        if len(rate_limit_data['requests']) >= MAX_REQUESTS_PER_WINDOW:
            return True
        
        # Add current request
        rate_limit_data['requests'].append(current_time)
        return False

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if is_rate_limited():
            remaining_time = RATE_LIMIT_WINDOW - (datetime.now() - rate_limit_data['requests'][0]).seconds
            return jsonify({
                'error': f'Rate limit exceeded. Please try again in about {remaining_time//60} minutes.'
            }), 429
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not Found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/homework-generator')
def homework_generator():
    try:
        return render_template('homework_generator.html')
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate_homework', methods=['POST'])
@rate_limit
def generate_homework():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        grade = request.form.get('grade')
        
        if not grade:
            return jsonify({'error': 'Grade level is required'}), 400
            
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Process the image and extract questions
        try:
            image_base64 = encode_image(file)
            questions = extract_questions_from_image(image_base64, grade)
            
            if not questions:
                return jsonify({'error': 'No questions could be extracted from the image'}), 400
                
            return jsonify({"questions": questions})
            
        except Exception as e:
            if 'rate limit' in str(e).lower():
                return jsonify({
                    'error': 'OpenAI API rate limit reached. Please try again in about an hour.'
                }), 429
            else:
                return jsonify({
                    'error': f'OpenAI API error: {str(e)}'
                }), 503

    except Exception as e:
        logger.error(f"Error processing homework: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_homework_help', methods=['POST'])
@rate_limit
def get_homework_help():
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'No question provided'}), 400

        question = data['question']
        grade = data.get('grade', '9')  # Default to 9th grade if not specified
        
        try:
            steps = generate_step_by_step_help(question, grade)
            return jsonify({"steps": steps})
            
        except Exception as e:
            if 'rate limit' in str(e).lower():
                return jsonify({
                    'error': 'OpenAI API rate limit reached. Please try again in about an hour.'
                }), 429
            else:
                return jsonify({
                    'error': f'OpenAI API error: {str(e)}'
                }), 503

    except Exception as e:
        logger.error(f"Error getting homework help: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Template directory: {template_dir}")
    logger.info(f"Available templates: {os.listdir(template_dir)}")
    app.run(debug=True, port=5001)
