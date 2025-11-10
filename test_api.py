import requests
import json

url = "http://127.0.0.1:5000/api/auth/register"  # ðŸ‘ˆ LOCAL URL

data = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "123456",
    "role": "haunter"
}

response = requests.post(url, json=data)
print("Status:", response.status_code)
print("Response text:", response.text)