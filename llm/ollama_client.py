import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

def call_llm(prompt: str, temperature: float = 0.2) -> str:
    payload = {
        "model": "mistral:7b-instruct",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()

    return response.json()["response"]
