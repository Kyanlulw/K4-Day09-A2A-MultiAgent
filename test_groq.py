import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY"),
)

print("Testing Groq llama-3.1-8b-instant...")
try:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": "Hello!"}],
        temperature=0.0,
        max_tokens=100
    )
    print("Response object:", response.model_dump_json(indent=2))
except Exception as e:
    print("API Error:", e)
