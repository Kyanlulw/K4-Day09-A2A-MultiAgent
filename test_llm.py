import os
from dotenv import load_dotenv
from tools.llm_client import llm_call, llm_json_call

load_dotenv()

print("Testing OpenRouter...")

try:
    res = llm_call(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say hello!"
    )
    print("Response text:", res)
except Exception as e:
    print("Error:", e)
