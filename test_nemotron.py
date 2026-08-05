import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

print("Testing OpenRouter nemotron-nano-9b-v2:free...")
try:
    response = client.chat.completions.create(
        model="nvidia/nemotron-nano-9b-v2:free",
        messages=[{"role": "user", "content": "Hello!"}],
        temperature=0.0,
        max_tokens=100
    )
    print("Response object:", response.model_dump_json(indent=2))
except Exception as e:
    print("API Error:", e)
