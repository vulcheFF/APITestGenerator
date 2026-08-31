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

    # try:
    #     response = requests.post(OLLAMA_URL, json = {
    #         "model": model or MODEL,
    #         "prompt": prompt,
    #         "stream": False,
    #         "format": "json",
    #         "options": {"temperature":0}
    #         }, timeout=timeout)

    #     if json_mode:
    #         payload["format"]

    #     response.raise_for_status()
    #     return response.json()["response"]
    # except requests.exceptions.RequestException as e:
    #     print(f"[AI] Ollama unavailable: {e}")
    #     return None

    
