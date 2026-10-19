
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

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
