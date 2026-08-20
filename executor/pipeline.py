import re
from generator import constants
from generator.spec_parser import fetch_openapi_spec, extract_endpoints, get_request_body_schema
from generator.data_generator import generate_valid_object, generate_invalid_objects, get_skipped_categories
from generator.path_param_generator import generate_path_param_cases
from executor.test_runner import execute_test
from analyzer.report import analyze_results, print_report
from storage.repository import save_run
from storage.database import init_db

def fill_path_params(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", path)

def fill_path_params_with_value(path: str, value: str) -> str:
    return re.sub(r"\{[^}]+\}", value, path)


def run_all_tests(base_url: str, category_filter: list[str] = None) -> tuple[list[dict], list[dict]]:
    spec = fetch_openapi_spec(base_url)
    endpoints = extract_endpoints(spec)
    results = []
    all_skipped = []

    for endpoint in endpoints:
        if endpoint["method"] in ("POST", "PUT"):
            schema = get_request_body_schema(spec, endpoint)
            #print("DEBUG SCHEMA FOR", endpoint["path"], ":", schema)
            if not schema:
                continue

            filled_path = fill_path_params(endpoint["path"])


            if category_filter is None or constants.VALID_DATA in category_filter:
                #валидни
                valid_data = generate_valid_object(schema)
                result  = execute_test(base_url, endpoint["method"], filled_path, valid_data)
                result["test_type"] = "valid"
                result["category"] = constants.VALID_DATA
                result["field"] = None
                result["expected_status"] = 200
                result["description"] = "Valid data"
                results.append(result)


            #невалидни
            for case in generate_invalid_objects(schema):
                if category_filter is not None and case["category"] not in category_filter:
                    continue
                result = execute_test(base_url, endpoint["method"], filled_path, case["data"])
                result["test_type"] = "invalid"
                result["category"] = case["category"]
                result["field"] = case["field"]
                result["expected_status"] = case["expected_status"]
                result["description"] = case["description"]
                results.append(result)

            for skipped in get_skipped_categories(schema):
                all_skipped.append({
                    "path": endpoint["path"],
                    "method": endpoint["method"],
                    **skipped,
                })

        if endpoint["method"] in ("GET", "DELETE") and "{" in endpoint["path"]:
            for case in generate_path_param_cases():
                if category_filter is not None and case["category"] not in category_filter:
                    continue
                test_path = fill_path_params_with_value(endpoint["path"], case["value"])
                result = execute_test(base_url, endpoint["method"], test_path, data=None)
                result["test_type"] = "path_param"
                result["category"] = case["category"]
                result["field"] = None
                result["expected_status"] = case["expected_status"]
                result["description"] = case["description"]
                results.append(result)

    return results, all_skipped



if __name__ == "__main__":
    init_db()

    #results, skipped = run_all_tests("http://127.0.0.1:8000", category_filter=["type_mismatch"])
    results, skipped = run_all_tests("http://127.0.0.1:8000")
    analysis = analyze_results(results)
    print_report(analysis)
    if skipped:
        print("\n--------Skipped categories(not defined)------------")
        for s in skipped:
            print(f"{s['method']} {s['path']} - {s['category']}: {s['reason']}")

    run_id = save_run("http://127.0.0.1:8000", results, analysis)
    print(f"\nSaved as run#{run_id}")






    # for res in results:
    #     print(res["method"], res["path"], "-", res["description"], "->", res["status_code"])
    #     # if res["status_code"] == 422:
    #     #     print("   Sent:", res["data_sent"])
    #     #     print("   Error:", res["response_body"])
    #     # if res["description"] == "Valid data" and res["status_code"] == 422:
    #     #     print("   Sent:", res["data_sent"])
    #     #     print("   Error:", res["response_body"])