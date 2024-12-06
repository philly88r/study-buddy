import unittest
from flask import Flask, render_template
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, 
            template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
        )
        
        # Add routes
        @self.app.route('/')
        def home():
            return "Home page works!"

        @self.app.route('/study_guide')
        def study_guide():
            return render_template('study_guide_test.html')
            
        self.client = self.app.test_client()
        self.api_key = os.getenv('OPENAI_API_KEY')

    def test_openai_connection(self):
        """Test that we can connect to OpenAI API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            response = requests.get('https://api.openai.com/v1/models', headers=headers)
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.fail(f"OpenAI connection failed: {str(e)}")

    def test_home_route(self):
        """Test the home route"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode(), "Home page works!")

    def test_study_guide_route(self):
        """Test the study guide route"""
        response = self.client.get('/study_guide')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
