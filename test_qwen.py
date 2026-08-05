import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="EMPTY",
)

print("Testing local vLLM Qwen/Qwen3-8B...")
try:
    response = client.chat.completions.create(
        model="Qwen/Qwen3-8B",
        messages=[{"role": "user", "content": "Hello!"}],
        temperature=0.0,
        max_tokens=100
    )
    print("Response object:", response.model_dump_json(indent=2))
except Exception as e:
    print("API Error:", e)
