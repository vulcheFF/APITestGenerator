import re
from generator.path_param_generator import generate_path_param_cases
from generator.spec_parser import fetch_openapi_spec, extract_endpoints, get_request_body_schema
from generator.data_generator import generate_valid_object, generate_invalid_objects
from executor.test_runner import execute_test
from analyzer.report import analyze_results, print_report

def fill_path_params(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", path)

def fill_path_params_with_value(path: str, value: str) -> str:
    return re.sub(r"\{[^}]+\}", value, path)


def run_all_tests(base_url: str) -> list[dict]:
    spec = fetch_openapi_spec(base_url)
    endpoints = extract_endpoints(spec)
    results = []

    for endpoint in endpoints:
        if endpoint["method"] in ("POST", "PUT"):
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

        if endpoint["method"] in ("GET", "DELETE") and "{" in endpoint["path"]:
            for case in generate_path_param_cases():
                test_path = fill_path_params_with_value(endpoint["path"], case["value"])
                result = execute_test(base_url, endpoint["method"], test_path, data=None)
                result["test_type"] = "path_param"
                result["description"] = case["description"]
                result["case_id"] = case["case_id"]
                results.append(result)

    return results



if __name__ == "__main__":
    results = run_all_tests("http://127.0.0.1:8000")
    analysis = analyze_results(results)
    print_report(analysis)
    # for res in results:
    #     print(res["method"], res["path"], "-", res["description"], "->", res["status_code"])
    #     # if res["status_code"] == 422:
    #     #     print("   Sent:", res["data_sent"])
    #     #     print("   Error:", res["response_body"])
    #     # if res["description"] == "Valid data" and res["status_code"] == 422:
    #     #     print("   Sent:", res["data_sent"])
    #     #     print("   Error:", res["response_body"])