import os
import sys
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

# Ensure the root directory is in the path
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_APP_DIR)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

load_dotenv(os.path.join(_APP_DIR, ".env"))

api_key = os.getenv("GEMINI_API_KEY", "").strip()
base_url = os.getenv("GEMINI_BASE_URL", "").strip()
model_name = os.getenv("GEMINI_MODEL_NAME", "gc/gemini-3-flash-preview").strip()

print("=" * 60)
print("Gemini API Diagnostic Tool (Multi-Auth Test Mode)")
print("=" * 60)
print(f"API Key: {api_key}")
print(f"Base URL: {base_url}")
print(f"Model Name: {model_name}")

if not api_key or not base_url:
    print("[Error] GEMINI_API_KEY or GEMINI_BASE_URL is not set in app/.env")
    sys.exit(1)

# List of headers to test
tests = [
    {
        "name": "Standard Bearer Token",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    },
    {
        "name": "Direct Token (No Bearer)",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": api_key
        }
    },
    {
        "name": "api-key Custom Header",
        "headers": {
            "Content-Type": "application/json",
            "api-key": api_key
        }
    },
    {
        "name": "x-api-key Custom Header",
        "headers": {
            "Content-Type": "application/json",
            "x-api-key": api_key
        }
    }
]

url = f"{base_url.rstrip('/')}/chat/completions"
payload = {
    "model": model_name,
    "messages": [
        {"role": "user", "content": "Hai"}
    ],
    "temperature": 0.3
}

print(f"\nTarget Endpoint: {url}")

for i, test in enumerate(tests, 1):
    print(f"\n[{i}/4] Testing: {test['name']}...")
    print(f"Headers: {json.dumps(test['headers'])}")
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=test['headers'],
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            result = res_data["choices"][0]["message"]["content"]
            print(f"--> [SUCCESS] Response: {result.strip()}")
            print("\n*** KELAS AUTH INI BERHASIL! ***")
            # Kita bisa berhenti jika sudah ada yang sukses
            
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"--> [FAILED] HTTP {e.code}: {err_body}")
    except Exception as e:
        print(f"--> [FAILED] Error: {e}")
        
print("=" * 60)
