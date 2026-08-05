import os
import json
from dotenv import load_dotenv
from tools.llm_client import llm_json_call

load_dotenv()

print("Testing OpenRouter with JSON...")

try:
    res = llm_json_call(
        system_prompt="You are a JSON assistant.",
        user_prompt="Output {\"hello\": \"world\"}."
    )
    print("Parsed JSON:", res)
except Exception as e:
    print("Error:", e)
