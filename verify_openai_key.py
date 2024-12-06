import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from environment
api_key = os.getenv('OPENAI_API_KEY')

def verify_openai_key(api_key):
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        response = requests.get('https://api.openai.com/v1/models', headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"Error verifying OpenAI API key: {str(e)}")
        return False

# Verify the API key
if verify_openai_key(api_key):
    print("API Key is valid.")
else:
    print("Invalid API Key.")
