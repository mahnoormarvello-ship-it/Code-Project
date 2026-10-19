
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("AQ.Ab8RN6J4cXvBzkaqpVnOMUYE5fwvMnZe7OTATHSHoWOnE9b_PQ")

if not api_key:
    print("ERROR: GEMINI_API_KEY missing from .env")
    raise SystemExit(1)

client = genai.Client(api_key=api_key)

try:
    print("\nModels available for answer generation:\n")

    for model in client.models.list():
        supported_actions = model.supported_actions or []

        if "generateContent" in supported_actions:
            print(model.name)

except Exception as error:
    print("Could not list models:")
    print(error)
