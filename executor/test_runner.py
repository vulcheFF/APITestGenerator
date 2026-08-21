import requests

DEFAULT_TIMEOUT = 5 #sec


def execute_test(base_url: str, method: str, path: str, data: dict = None) -> dict:
    url = f"{base_url}{path}"

    try:
        response = requests.request(method=method, url=url, json=data, timeout=DEFAULT_TIMEOUT)

    except requests.exceptions.RequestException as e:
        return {
            "method": method,
            "path": path,
            "data_sent": data,
            "status_code": None,
            "response_body": None,
            "error": str(e),
        }


    return {
        "method": method,
        "path": path,
        "data_sent": data,
        "status_code": response.status_code,
        "response_body": safe_json(response),
    }


def safe_json(response):
    try:
        return response.json()
    except ValueError:
        return None


if __name__ == "__main__":
    result = execute_test(
        base_url = "http://127.0.0.1:8000",
        method = "POST",
        path="/books",
        data={
            "id": 99,
            "title": "Test Book 1",
            "author": "Test Auth 1",
            "isbn": "1234567890",
            "price": -5,
            "quantity": 3,
            "published_date": "2020-01-01",
            "genre": "Test"
        }

    )
    print(result)
