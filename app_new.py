from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from openai import OpenAI
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'pdf'}

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('homework_new.html')

@app.route('/upload_homework', methods=['POST'])
def upload_homework():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        # Create unique ID for this homework session
        homework_id = str(uuid.uuid4())
        
        # Ensure upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Save file with secure filename
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{homework_id}_{filename}")
        file.save(file_path)
        
        return jsonify({
            'message': 'File uploaded successfully',
            'id': homework_id
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/homework/<homework_id>')
def homework_page(homework_id):
    # This route will be implemented next to display the uploaded homework
    # and provide the interface for getting help
    return f"Homework page for ID: {homework_id}"

if __name__ == '__main__':
    app.run(debug=True)
