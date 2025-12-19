
import google.generativeai as genai
import sys

API_KEY = "AIzaSyBuOScNR-FI818vE_JIZTx3J0X8YVgVpKw"

print(f"Testing Gemini API with key: {API_KEY[:10]}...")

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash-exp') # Using the experimental model from nlp_processor or commands
    
    response = model.generate_content("Hello, are you online?")
    print("SUCCESS: Connection established.")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"FAILURE: {e}")
