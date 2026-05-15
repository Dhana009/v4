from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY", "").strip()
if not api_key:
    raise SystemExit("Set OPENAI_API_KEY in .env or the environment.")
client = OpenAI(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "Say hello if this API key works."}
        ],
        max_tokens=10
    )

    print("✅ API key is working!")
    print("Response:", response.choices[0].message.content)

except Exception as e:
    print("❌ API key failed!")
    print("Error:", str(e))