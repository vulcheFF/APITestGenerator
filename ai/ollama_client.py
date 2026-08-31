import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b"


def query_ollama(prompt: str, timeout: int = 30, model:str | None = None) -> str | None:
    try:
        response = requests.post(OLLAMA_URL, json = {
            "model": model or MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature":0}
            }, timeout=timeout)
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.RequestException as e:
        print(f"[AI] Ollama unavailable: {e}")
        return None

    
