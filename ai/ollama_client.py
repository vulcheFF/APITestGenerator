import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b"


def query_ollama(prompt: str, timeout: int = 30, model:str | None = None, json_mode: bool = True) -> str | None:

    payload = {
        "model": model or MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature":0}
    }

    if json_mode:
        payload["format"] = "json"

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.RequestException as e:
        print(f"[AI] Ollama unavailable: {e}")
        return None


def is_ollama_available(timeout: int = 3) ->bool:
    try:
        response = requests.get("http://localhost:11434/api/tags",timeout = timeout)
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False