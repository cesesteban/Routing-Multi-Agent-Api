import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def test_embeddings():
    url = os.getenv("LM_STUDIO_BASE_URL", "http://192.168.1.64:1234/v1") + "/embeddings"
    model = os.getenv("MODEL_NAME", "text-embedding-nomic-embed-text-v1.5")
    
    payload = {
        "model": model,
        "input": "Hola mundo"
    }
    
    print(f"Post to {url} with model {model}...")
    try:
        response = requests.post(url, json=payload, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_embeddings()
