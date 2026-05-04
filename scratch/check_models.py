import requests
import json

try:
    url = "http://192.168.1.64:1234/v1/models"
    print(f"Checking models at {url}...")
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
        models = response.json()
        print(f"Models found: {json.dumps(models, indent=2)}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Connection failed: {e}")
