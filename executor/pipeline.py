import re
import random
from analyzer.schema_validator import validate_response_against_schema
from generator import constants
from generator.spec_parser import fetch_openapi_spec, extract_endpoints, get_request_body_schema, get_response_schema, get_path_param_schema, get_query_params_schema
from generator.data_generator import generate_valid_object, generate_invalid_objects, get_skipped_categories, generate_valid_value
from generator.path_param_generator import generate_path_param_cases
from executor.test_runner import execute_test
from analyzer.report import analyze_results, print_report
from storage.repository import save_run
from storage.database import init_db


def get_default_path_value(param_schema: dict | None) -> str:
    param_type = (param_schema or {}).get("type", "integer")
    if param_type == "integer":
        return "1"
    if param_type == "string":
        return "existing-item"
    if param_type == "number":
        return "1.5"
    if param_type == "boolean":
        return "1"

def fill_path_params(path: str, param_schema: dict | None = None) -> str:
    value = get_default_path_value(param_schema)
    return re.sub(r"\{[^}]+\}", value, path)

def fill_path_params_with_value(path: str, value: str) -> str:
    return re.sub(r"\{[^}]+\}", value, path)

def attach_schema_conformance(result: dict, spec: dict, endpoint: dict) -> dict:
    response_schema = get_response_schema(spec, endpoint, str(result["status_code"]))
    if response_schema is not None:
        result["schema_conformance_errors"] = validate_response_against_schema(result["response_body"], response_schema)
    else:
        result["schema_conformance_errors"] = None
    return result

def build_query_string(params: dict) -> str:
    if not params:
        return ""
    parts = [f"{key}={value}" for key, value in params.items()]
    return "?" + "&".join(parts)

def find_id_like_field(schema: dict, path_param_name: str = None) -> str | None:
    properties = schema.get("properties", {})

    if path_param_name and path_param_name in properties:
        return path_param_name

    for field_name, field_schema in properties.items():
        if field_schema.get("type") != "integer":
            continue
        if _is_id_like_name(field_name):
            return field_name

    return None

def _is_id_like_name(field_name: str) -> bool:
    #snake_case
    snake_parts = field_name.lower().split("_")
    if "id" in snake_parts:
        return True
    camel_parts = re.findall(r'[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z][a-z0-9]*|[a-z0-9]+', field_name)
    return any(part.lower() == "id" for part in camel_parts)

def run_all_tests(base_url: str, category_filter: list[str] = None, seed: int = None) -> tuple[list[dict], list[dict]]:
    if seed is not None:
        random.seed(seed)

    spec = fetch_openapi_spec(base_url)
    endpoints = extract_endpoints(spec)
    results = []
    all_skipped = []

    for endpoint in endpoints:

        if endpoint["method"] in ("POST", "PUT"):
            schema = get_request_body_schema(spec, endpoint)
            if not schema:
                continue

            path_param_schema = get_path_param_schema(endpoint)
            filled_path = fill_path_params(endpoint["path"], path_param_schema)

            if category_filter is None or constants.VALID_DATA in category_filter:
                #валидни
                valid_data = generate_valid_object(schema)
                if endpoint["method"] == "PUT" and "{" in endpoint["path"]:
                    path_param_match = re.search(r"\{([^}]+)\}", endpoint["path"])
                    path_param_name = path_param_match.group(1) if path_param_match else None

                    id_field = find_id_like_field(schema, path_param_name)
                    if id_field and path_param_schema:
                        path_value = get_default_path_value(path_param_schema)
                        if path_param_schema.get("type") == "integer":
                            valid_data[id_field] = int(path_value)
                        elif path_param_schema.get("type") == "number":
                            valid_data[id_field] = float(path_value)
                        else:
                            valid_data[id_field] = path_value
                
                result = execute_test(base_url, endpoint["method"], filled_path, valid_data)
                result = attach_schema_conformance(result, spec, endpoint)
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
                result = attach_schema_conformance(result, spec, endpoint)
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

                
        if endpoint["method"] == "GET" and "{" not in endpoint["path"]:
            query_params = get_query_params_schema(endpoint)
            required_params = [p for p in query_params if p["required"]]

            if category_filter is None or constants.LIST_ENDPOINT in category_filter:
                if required_params:
                    #valid req - valid values for req params
                    valid_query = {
                        p["name"]: generate_valid_value(p["schema"]) or "sample-value" for p in required_params
                    }
                    test_path = endpoint["path"] + build_query_string(valid_query)
                    result = execute_test(base_url, endpoint["method"], test_path, data=None)
                    result = attach_schema_conformance(result, spec, endpoint)
                    result["test_type"] = "list_get"
                    result["category"] = constants.LIST_ENDPOINT
                    result["field"] = None
                    result["expected_status"] = 200
                    result["description"] = "Get list endpoint with required query params"
                    results.append(result)

                    #invalid - without req params
                    for missing_param in required_params:
                        partial_query = {
                            p["name"]: generate_valid_value(p["schema"]) or "sample-value" for p in required_params if p["name"] != missing_param["name"]
                        }
                        test_path = endpoint["path"] + build_query_string(partial_query)
                        result = execute_test(base_url, endpoint["method"], endpoint["path"], data = None)
                        result = attach_schema_conformance(result, spec, endpoint)
                        result["test_type"] = "list_get"
                        result["category"] = constants.MISSING_REQUIRED_QUERY_PARAM
                        result["field"] = required_params[0]["name"]
                        result["expected_status"] = 422
                        result["description"] = f"Missing required query param '{required_params[0]['name']}'"
                        results.append(result)
                else:
                    #no req params
                    result = execute_test(base_url, endpoint["method"], endpoint["path"], data=None)
                    result = attach_schema_conformance(result, spec, endpoint)
                    result["test_type"] = "list_get"
                    result["category"] = constants.LIST_ENDPOINT
                    result["field"] = None
                    result["expected_status"] = 200
                    result["description"] = "Get list endpoint (no filters)"
                    results.append(result)

        if endpoint["method"] in ("GET", "DELETE") and "{" in endpoint["path"]:
            param_schema = get_path_param_schema(endpoint)
            for case in generate_path_param_cases(param_schema):
                if category_filter is not None and case["category"] not in category_filter:
                    continue
                test_path = fill_path_params_with_value(endpoint["path"], case["value"])
                result = execute_test(base_url, endpoint["method"], test_path, data=None)
                result = attach_schema_conformance(result, spec, endpoint)
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