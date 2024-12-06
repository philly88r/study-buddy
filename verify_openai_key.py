from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv('OPENAI_API_KEY')

def verify_openai_key(api_key):
    try:
        client = OpenAI(
            api_key=api_key
        )
        # Test the API key with a simple request
        response = client.models.list()
        return True
    except Exception as e:
        print(f"Error verifying OpenAI API key: {str(e)}")
        return False

# Verify the API key
if verify_openai_key(api_key):
    print("API Key is valid.")
else:
    print("Invalid API Key.")
