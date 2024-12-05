from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
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
from openai import OpenAI

# Set console encoding to UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# API Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Flask app
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

app = Flask(__name__, 
    template_folder=template_dir,
    static_folder=static_dir
)

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev')
CORS(app)

# Main routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/flashcards')
def flashcards():
    return render_template('flashcards.html')

@app.route('/practice-by-topic')
def practice_by_topic():
    return render_template('practice_test.html')

@app.route('/practice-by-upload')
def practice_by_upload():
    return render_template('upload_practice_test.html')

@app.route('/homework-checker')
def homework_checker():
    return render_template('homework_checker.html')

@app.route('/homework-generator')
def homework_generator():
    return render_template('homework_generator.html')

# API routes
@app.route('/generate_flashcards', methods=['POST'])
def generate_flashcards():
    data = request.json
    if not data or 'topic' not in data:
        return jsonify({'error': 'No topic provided'}), 400

    topic = data['topic']
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "Generate 5 flashcards for studying. Each flashcard should have a front (question/term) and back (answer/definition)."},
                {"role": "user", "content": f"Generate flashcards for studying {topic}"}
            ]
        )
        
        flashcards = response.choices[0].message.content
        return jsonify({'flashcards': flashcards})
    
    except Exception as e:
        print(f"Error generating flashcards: {str(e)}")
        return jsonify({'error': 'Error generating flashcards'}), 500

@app.route('/generate_test', methods=['POST'])
def generate_test():
    data = request.json
    if not data or 'topic' not in data:
        return jsonify({'error': 'No topic provided'}), 400

    topic = data['topic']
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "Generate 5 practice questions with answers for the given topic."},
                {"role": "user", "content": f"Generate practice questions for {topic}"}
            ]
        )
        
        questions = response.choices[0].message.content
        return jsonify({'questions': questions})
    
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
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
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
            max_tokens=2048
        )
        
        content = response.choices[0].message.content
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
def check_homework():
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
                            "text": "Check this homework and provide feedback. Point out any errors and suggest improvements."
                        }
                    ]
                }
            ],
            max_tokens=2048
        )
        
        feedback = response.choices[0].message.content
        return jsonify({'feedback': feedback})

    except Exception as e:
        print(f"Error checking homework: {str(e)}")
        return jsonify({'error': 'Error checking homework'}), 500

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

if __name__ == '__main__':
    app.run(debug=True)
