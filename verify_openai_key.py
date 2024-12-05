import openai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client
openai.api_key = api_key

try:
    # Make a simple request to verify the API key
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Say hello"}],
        max_tokens=5
    )
    print("API Key is valid.")
except openai.error.AuthenticationError:
    print("Invalid API Key.")
except openai.error.OpenAIError as e:
    print(f"An OpenAI error occurred: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
