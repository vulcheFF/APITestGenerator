import re
from generator.spec_parser import fetch_openapi_spec, extract_endpoints, get_request_body_schema
from generator.data_generator import generate_valid_object, generate_invalid_objects
from executor.test_runner import execute_test

def fill_path_params(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", path)

def run_all_tests(base_url: str) -> list[dict]:
    spec = fetch_openapi_spec(base_url)
    endpoints = extract_endpoints(spec)
    results = []

    for endpoint in endpoints:
        if endpoint["method"] not in ("POST", "PUT"):
            continue #само с боди зася

        schema = get_request_body_schema(spec, endpoint)
        #print("DEBUG SCHEMA FOR", endpoint["path"], ":", schema)
        if not schema:
            continue

        filled_path = fill_path_params(endpoint["path"])

        
        #валидни
        valid_data = generate_valid_object(schema)
        result  = execute_test(base_url, endpoint["method"], filled_path, valid_data)
        result["test_type"] = "valid"
        result["description"] = "Valid data"
        results.append(result)


        #невалидни
        for case in generate_invalid_objects(schema):
            result = execute_test(base_url, endpoint["method"], filled_path, case["data"])
            result["test_type"] = "invalid"
            result["description"] = case["description"]
            results.append(result)

    return results



if __name__ == "__main__":
    results = run_all_tests("http://127.0.0.1:8000")
    for res in results:
        print(res["method"], res["path"], "-", res["description"], "->", res["status_code"])
        # if res["status_code"] == 422:
        #     print("   Sent:", res["data_sent"])
        #     print("   Error:", res["response_body"])
        # if res["description"] == "Valid data" and res["status_code"] == 422:
        #     print("   Sent:", res["data_sent"])
        #     print("   Error:", res["response_body"])