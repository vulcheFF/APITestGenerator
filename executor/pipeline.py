import re
import random
import time
from urllib.parse import quote
from analyzer.schema_validator import validate_response_against_schema
from generator import constants
from generator.spec_parser import fetch_openapi_spec, extract_endpoints, get_request_body_schema, get_response_schema, get_path_param_schema, get_query_params_schema, get_path_params_schema
from generator.spec_parser import get_declared_methods_for_path, get_undeclared_method, find_matching_create_endpoint
from generator.spec_parser import get_expected_success_status, get_success_status_codes
from generator.data_generator import generate_valid_object, generate_invalid_objects, get_skipped_categories, generate_valid_value, _invalid_type_value, generate_mass_assignment_case, get_skipped_query_categories
from generator.path_param_generator import generate_path_param_cases
from generator.malformed_json_generator import generate_malformed_json_cases
from executor.test_runner import execute_test
from analyzer.report import analyze_results, print_report
from analyzer.header_checks import check_allowed_header_present, check_accept_post_header_present
from storage.repository import save_run
from storage.database import init_db
from generator.data_generator import generate_ai_constraint_cases, generate_cross_field_case
from executor.state_helpers import fill_path_params_with_value, _is_id_like_name, find_id_like_field, create_resource_for_put_test, cleanup_created_resource, create_resource_for_stateful_test
from ai.ollama_client import MODEL as AI_MODEL


def is_ai_enabled_for_run(category_filter: list[str] | None) -> bool:
    if category_filter is None:
        return True

    ai_categories = {
        constants.AI_IMPLICIT_CONSTRAINT_VIOLATION,
        constants.AI_IMPLICIT_CONSTRAINT_VALID,
        constants.AI_CROSS_FIELD_VIOLATION,
    }

    return any(category in ai_categories for category in category_filter)

def get_selected_categories_for_run(category_filter: list[str] | None,) -> list[str]:
    if category_filter is not None:
        return list(category_filter)

    return list(constants.DETERMINISTIC_CATEGORIES + constants.AI_CATEGORIES)
    
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
    return "1"

def prepare_put_id_sync(base_url: str, endpoint: dict, schema: dict, path_param_schema: dict | None, ) -> dict | None:

    if endpoint["method"] != "PUT" or "{" not in endpoint["path"]:
        return None
    
    path_param_match =re.search(r"\{([^}]+)\}", endpoint["path"])
    path_param_name = path_param_match.group(1) if path_param_match else None

    id_field = find_id_like_field(schema, path_param_name)

    if not id_field or not path_param_schema:
        return None

    base_path = re.sub(r"/\{[^}]+\}$", "", endpoint["path"])

    real_id = (
        get_real_id_from_list(base_url, base_path, path_param_name) if path_param_name else None
    )

    path_value = (
        real_id if real_id is not None else get_default_path_value(path_param_schema)
    )

    sync_value = (
        int(path_value) if path_param_schema.get("type") == "integer" else path_value
    )

    return {
        "field": id_field,
        "value": sync_value,
    }


def fill_path_params(path: str, param_schema: dict | None = None) -> str:
    value = get_default_path_value(param_schema)
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
    parts = [] #[f"{key}={value}" for key, value in params.items()]

    for key, value in params.items():
        encoded_key = quote(str(key), safe="")
        if isinstance(value, list):
            for item in value:
                encoded_value = quote(str(item), safe="")
                parts.append(f"{encoded_key}={encoded_value}")
        else:
            encoded_value = quote(str(value), safe="")
            parts.append(f"{encoded_key}={encoded_value}")

    return "?" + "&".join(parts)

def fill_path_params_with_values(path: str, values: dict[str, object],) -> str:
    result = path

    for name, value in values.items():
        result = result.replace("{" + name + "}", quote(str(value), safe=""))

    return result


def run_all_tests(base_url: str, category_filter: list[str] = None, seed: int = None, ai_model:str | None = None) -> tuple[list[dict], list[dict]]:
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
            #expected_success_status = get_expected_success_status(endpoint) or 200
            success_codes = get_success_status_codes(endpoint)

            expected_success_status = (min(success_codes) if success_codes else 200)
            acceptable_success_statuses = (sorted(success_codes) if success_codes else [200])
            if category_filter is None or constants.VALID_DATA in category_filter:
                #валидни
                if endpoint["method"] == "PUT":
                    setup = create_resource_for_put_test(base_url, spec, endpoints, endpoint)
                    if setup is not None:
                        valid_data = generate_valid_value(schema)
                        if setup["id_field"] and isinstance(valid_data, dict):
                            valid_data[setup["id_field"]] = setup["id"]

                        #print(    "DEBUG VALID DATA:",    endpoint["method"],    endpoint["path"],    valid_data,)
                        result = execute_test(base_url, endpoint["method"], setup["path"], valid_data)
                        cleanup_created_resource(base_url, endpoints, setup["resource_path"], setup["id"])
                        result = attach_schema_conformance(result, spec, endpoint)
                        result = attach_template_path(result, endpoint)
                        result["test_type"] = "valid"
                        result["category"] = constants.VALID_DATA
                        result["field"] = None
                        result["expected_status"] = expected_success_status
                        result["acceptable_statuses"] = acceptable_success_statuses
                        result["description"] = "Valid data"
                        results.append(result)

                else:
                    valid_data = generate_valid_value(schema)
                    #print(    "DEBUG VALID DATA:",    endpoint["method"],    endpoint["path"],    valid_data,)
                    result = execute_test(base_url, endpoint["method"], filled_path, valid_data)  
                    response_body = result.get("response_body")
                    id_field = find_id_like_field(schema)
                    if id_field and isinstance(response_body, dict) and id_field in response_body:
                        cleanup_created_resource(base_url, endpoints, endpoint["path"], response_body[id_field])              
                    result = attach_schema_conformance(result, spec, endpoint)
                    result = attach_template_path(result, endpoint)
                    result["test_type"] = "valid"
                    result["category"] = constants.VALID_DATA
                    result["field"] = None
                    result["expected_status"] = expected_success_status
                    result["acceptable_statuses"] = acceptable_success_statuses
                    result["description"] = "Valid data"
                    results.append(result)


            #невалидни
            for case in generate_invalid_objects(schema):

                if category_filter is not None and case["category"] not in category_filter:
                    continue

                invalid_put_setup = None

                if endpoint["method"] == "PUT":
                    invalid_put_setup = create_resource_for_put_test(base_url, spec, endpoints, endpoint)

                test_path = filled_path

                if endpoint["method"] == "PUT" and invalid_put_setup is not None:
                    test_path = invalid_put_setup["path"]

                    id_field = invalid_put_setup["id_field"]
                    if(isinstance(case["data"], dict) and id_field in case["data"] and case["field"] != id_field):
                        case["data"][id_field] = invalid_put_setup["id"]

                result = execute_test(base_url, endpoint["method"], test_path, case["data"])

                if endpoint["method"] == "PUT" and invalid_put_setup is not None:
                    cleanup_created_resource(base_url,endpoints,invalid_put_setup["resource_path"],invalid_put_setup["id"],)

                    id_field = invalid_put_setup["id_field"]
                    if case["field"] == id_field:
                        mutated_id = case["data"].get(id_field)

                        if mutated_id is not None and mutated_id != invalid_put_setup["id"]:
                            cleanup_created_resource(base_url,endpoints,invalid_put_setup["resource_path"],mutated_id,)
                    
                result = attach_schema_conformance(result, spec, endpoint)
                result = attach_template_path(result, endpoint)
                result["test_type"] = "invalid"
                result["category"] = case["category"]
                result["field"] = case["field"]
                result["expected_status"] = case["expected_status"]
                result["description"] = case["description"]
                results.append(result)
                if endpoint["method"] == "POST":
                    cleanup_if_unexpectedly_succeeded(base_url, endpoints, endpoint, result, schema )

            mass_assignment_case = generate_mass_assignment_case(schema)
            if mass_assignment_case and (category_filter is None or constants.MASS_ASSIGNMENT in category_filter):
                mass_assignment_setup = None
                test_path = filled_path
                if endpoint["method"] =="PUT":
                    mass_assignment_setup = create_resource_for_put_test(base_url, spec, endpoints, endpoint)
                    if mass_assignment_setup is not None:
                        test_path = mass_assignment_setup["path"]
                        id_field = mass_assignment_setup["id_field"]
                        if(isinstance(mass_assignment_case["data"],dict) and id_field in mass_assignment_case["data"]):
                            mass_assignment_case["data"][id_field] = mass_assignment_setup["id"]


                result = execute_test(base_url, endpoint["method"], test_path, mass_assignment_case["data"])

                if mass_assignment_setup is not None:
                    cleanup_created_resource(base_url, endpoints, mass_assignment_setup["resource_path"], mass_assignment_setup["id"],)

                result = attach_schema_conformance(result, spec, endpoint)
                result = attach_template_path(result, endpoint)
                result["test_type"] = "invalid"
                result["category"] = mass_assignment_case["category"]
                result["field"] = mass_assignment_case["field"]
                result["expected_status"] = mass_assignment_case["expected_status"]
                result["description"] = mass_assignment_case["description"]
                results.append(result)

                if endpoint["method"] == "POST":
                    cleanup_if_unexpectedly_succeeded(base_url, endpoints, endpoint, result, schema)

            #put_id_sync = prepare_put_id_sync(base_url,endpoint,schema,path_param_schema,)
            if category_filter is None or constants.AI_IMPLICIT_CONSTRAINT_VIOLATION in category_filter or constants.AI_IMPLICIT_CONSTRAINT_VALID in category_filter:
                ai_cases = generate_ai_constraint_cases(schema, ai_model = ai_model)
                generate_ai_categories= {case["category"] for case in ai_cases}
                for ai_category in (constants.AI_IMPLICIT_CONSTRAINT_VIOLATION, constants.AI_IMPLICIT_CONSTRAINT_VALID):
                    if category_filter is not None and ai_category not in category_filter:
                        continue
                    if ai_category not in generate_ai_categories:
                        all_skipped.append({
                            "path": endpoint["path"],
                            "method": endpoint["method"],
                            "category": ai_category,
                            "reason": "No applicable AI implicit constraint test case was produced for this schema.",
                        })
                    
                for ai_case in ai_cases:
                    if category_filter is not None and ai_case["category"] not in category_filter:
                        continue
                    ai_put_setup = None
                    if endpoint["method"] == "PUT":
                        ai_put_setup = create_resource_for_put_test(base_url, spec, endpoints, endpoint)
                    ai_test_path = filled_path
                    if endpoint["method"] == "PUT" and ai_put_setup is not None:
                        ai_test_path = ai_put_setup["path"]
                        id_field = ai_put_setup["id_field"]
                        if(id_field in ai_case["data"] and ai_case["field"] != id_field):
                            ai_case["data"][id_field] = ai_put_setup["id"]
                    result = execute_test(base_url, endpoint["method"], ai_test_path, ai_case["data"])
                    if endpoint["method"] == "PUT" and ai_put_setup is not None:
                        cleanup_created_resource(base_url, endpoints, ai_put_setup["resource_path"], ai_put_setup["id"])
                        id_field = ai_put_setup["id_field"]

                        if ai_case["field"] == id_field:
                            mutated_id = ai_case["data"].get(id_field)
                            if (mutated_id is not None and mutated_id != ai_put_setup["id"]):
                                cleanup_created_resource(base_url, endpoints, ai_put_setup["resource_path"], mutated_id)



                    result = attach_schema_conformance(result, spec, endpoint)
                    result = attach_template_path(result, endpoint)
                    if ai_case["category"] == constants.AI_IMPLICIT_CONSTRAINT_VALID:
                        success_codes = get_success_status_codes(endpoint)

                        expected_status = (min(success_codes) if success_codes else 200)
                        acceptable_success_statuses = (sorted(success_codes) if success_codes else [200])
                    else:
                        expected_status = ai_case["expected_status"]
                        acceptable_success_statuses = None
                    result["test_type"] = ("valid" if ai_case["category"] == constants.AI_IMPLICIT_CONSTRAINT_VALID else "invalid")
                    result["category"] = ai_case["category"]
                    result["field"] = ai_case["field"]
                    result["expected_status"] = expected_status
                    if acceptable_success_statuses is not None:
                        result["acceptable_statuses"] = acceptable_success_statuses
                    result["description"] = ai_case["description"]
                    results.append(result)
                    if (endpoint["method"]=="POST" and ai_case["category"] == constants.AI_IMPLICIT_CONSTRAINT_VALID and result.get("status_code") is not None and 200<=result["status_code"] <300):
                        response_body = result.get("response_body")
                        id_field = find_id_like_field(schema)
                        if (id_field and isinstance(response_body,dict) and id_field in response_body):
                            cleanup_created_resource(base_url, endpoints, endpoint["path"], response_body[id_field])
                    if endpoint["method"] == "POST":
                        cleanup_if_unexpectedly_succeeded(base_url, endpoints, endpoint, result, schema)
                  
            if category_filter is None or constants.AI_CROSS_FIELD_VIOLATION in category_filter:
                cross_case = generate_cross_field_case(schema, ai_model = ai_model)
                if cross_case is None:
                    all_skipped.append({
                        "path": endpoint["path"],
                        "method": endpoint["method"],
                        "category": constants.AI_CROSS_FIELD_VIOLATION,
                        "reason": "No applicable AI cross-field constraint test case was produced for this schema.",
                    })
                if cross_case:
                    cross_put_setup = None
                    if endpoint["method"] == "PUT":
                        cross_put_setup = create_resource_for_put_test(base_url, spec, endpoints, endpoint)
                    cross_test_path = filled_path
                    if endpoint["method"] == "PUT" and cross_put_setup is not None:
                        cross_test_path = cross_put_setup["path"]

                        id_field = cross_put_setup["id_field"]
                        tested_fields = cross_case["field"].split("+")

                        if (id_field in cross_case["data"] and id_field not in tested_fields):
                            cross_case["data"][id_field] = cross_put_setup["id"]

                    result = execute_test(base_url, endpoint["method"], cross_test_path, cross_case["data"])
                    if endpoint["method"] == "PUT" and cross_put_setup is not None:
                        cleanup_created_resource(base_url, endpoints, cross_put_setup["resource_path"],cross_put_setup["id"])
                        id_field = cross_put_setup["id_field"]
                        tested_fields = cross_case["field"].split("+")

                        if id_field in tested_fields:
                            mutated_id = cross_case["data"].get(id_field)
                            if(mutated_id is not None and mutated_id != cross_put_setup["id"]):
                                cleanup_created_resource(base_url, endpoints, cross_put_setup["resource_path"], mutated_id)

                    #result = execute_test(base_url, endpoint["method"], ai_test_path, cross_case["data"])
                    result = attach_schema_conformance(result, spec, endpoint)
                    result = attach_template_path(result, endpoint)
                    result["test_type"] = "invalid"
                    result["category"] = cross_case["category"]
                    result["field"] = cross_case["field"]
                    result["expected_status"] = cross_case["expected_status"]
                    result["description"] = cross_case["description"]
                    results.append(result)
                    if endpoint["method"] == "POST":
                        cleanup_if_unexpectedly_succeeded(base_url, endpoints, endpoint, result, schema)


            if category_filter is  None or constants.MALFORMED_JSON in category_filter:
                for case in generate_malformed_json_cases():
                    malformed_put_setup = None
                    test_path = filled_path
                    if endpoint["method"] == "PUT":
                        malformed_put_setup = create_resource_for_stateful_test(base_url, spec, endpoints, endpoint)
                        if malformed_put_setup is not None:
                            test_path = malformed_put_setup["path"]

                             
                    result = execute_test(base_url, endpoint["method"], test_path, raw_body=case["body"])
                    if malformed_put_setup is not None:
                        cleanup_created_resource(base_url, endpoints, malformed_put_setup["resource_path"], malformed_put_setup["id"])
                    # result = attach_schema_conformance(result, spec, endpoint)
                    result["test_type"] = "invalid"
                    result["category"] = constants.MALFORMED_JSON
                    result["field"] = None
                    result["expected_status"] = 400
                    result["description"] = case["description"]
                    result["template_path"] = endpoint["path"]
                    results.append(result)     
            if category_filter is  None or constants.WRONG_CONTENT_TYPE in category_filter:
                valid_data_for_ct_test = generate_valid_object(schema)
                import json as json_module

                wrong_ct_put_setup = None
                test_path = filled_path

                if endpoint["method"] == "PUT":
                    wrong_ct_put_setup = create_resource_for_stateful_test(base_url, spec, endpoints, endpoint)
                    if wrong_ct_put_setup is not None:
                        test_path = wrong_ct_put_setup["path"]
                        id_field = wrong_ct_put_setup["id_field"]
                        if id_field in valid_data_for_ct_test:
                            valid_data_for_ct_test[id_field] = wrong_ct_put_setup["id"]
                            
                result = execute_test(base_url, endpoint["method"], test_path, raw_body=json_module.dumps(valid_data_for_ct_test), content_type="text/plain")
                if wrong_ct_put_setup is not None:
                    cleanup_created_resource(base_url, endpoints, wrong_ct_put_setup["resource_path"], wrong_ct_put_setup["id"])
                has_accept_post_header = check_accept_post_header_present(result.get("response_headers",{}))
                result["test_type"] = "invalid"
                result["category"] = constants.WRONG_CONTENT_TYPE
                result["field"] = None
                result["expected_status"] = 415
                result["description"] = f"Valid JSON body with wrong Content-Type (text/plain) (Accept-Post header present: {has_accept_post_header})"
                result["template_path"] = endpoint["path"]
                results.append(result)

            for skipped in get_skipped_categories(schema):
                if category_filter is not None and skipped["category"] not in category_filter:
                    continue
                all_skipped.append({
                    "path": endpoint["path"],
                    "method": endpoint["method"],
                    **skipped,
                })

                
        if endpoint["method"] == "GET" and "{" not in endpoint["path"]:
            query_params = get_query_params_schema(spec, endpoint)
            required_params = [p for p in query_params if p["required"]]
           # expected_success_status = get_expected_success_status(endpoint) or 200
            success_codes = get_success_status_codes(endpoint)

            expected_success_status = (min(success_codes) if success_codes else 200)
            acceptable_success_statuses = (sorted(success_codes) if success_codes else [200])           

            
            if required_params:
                if category_filter is None or constants.LIST_ENDPOINT in category_filter:
                    #valid req - valid values for req params
                    valid_query = {
                        p["name"]: generate_valid_value(p["schema"]) or "sample-value" for p in required_params
                    }
                    test_path = endpoint["path"] + build_query_string(valid_query)
                    result = execute_test(base_url, endpoint["method"], test_path, data=None)
                    result = attach_schema_conformance(result, spec, endpoint)
                    result = attach_template_path(result, endpoint)
                    result["test_type"] = "list_get"
                    result["category"] = constants.LIST_ENDPOINT
                    result["field"] = None
                    result["expected_status"] = expected_success_status
                    result["acceptable_statuses"] = acceptable_success_statuses
                    result["description"] = "Get list endpoint with required query params"
                    results.append(result)          

                if category_filter is None or constants.MISSING_REQUIRED_QUERY_PARAM in category_filter:
                    #invalid - without req params
                    for missing_param in required_params:
                        partial_query = {
                            p["name"]: generate_valid_value(p["schema"]) or "sample-value" for p in required_params if p["name"] != missing_param["name"]
                        }
                        test_path = endpoint["path"] + build_query_string(partial_query)
                        result = execute_test(base_url, endpoint["method"], test_path, data = None)
                        result = attach_schema_conformance(result, spec, endpoint)
                        result = attach_template_path(result, endpoint)
                        result["test_type"] = "list_get"
                        result["category"] = constants.MISSING_REQUIRED_QUERY_PARAM
                        result["field"] = missing_param["name"]
                        result["expected_status"] = 422
                        result["description"] = f"Missing required query param '{missing_param["name"]}'"
                        results.append(result)

                if category_filter is None or constants.INVALID_QUERY_PARAM_VALUE in category_filter:
                    #Invalid value for each required parameter individually
                    for target_param in required_params:
                        target_schema = target_param["schema"]
                        effective_type = (target_schema.get("items", {}).get("type") if target_schema.get("type") == "array" else target_schema.get("type"))

                        if effective_type in ("string", None):
                            continue

                        if target_schema.get("type") == "array":
                            invalid_value = _invalid_type_value(target_schema["items"])
                        else:
                            invalid_value = _invalid_type_value(target_schema)

                        invalid_query = {
                            p["name"]: generate_valid_value(p["schema"]) or "sample-value" for p in required_params if p["name"] != target_param["name"]
                        }
                        invalid_query[target_param["name"]] = invalid_value
                        test_path = endpoint["path"] + build_query_string(invalid_query)
                        result = execute_test(base_url, endpoint["method"], test_path, data = None)
                        result = attach_schema_conformance(result, spec, endpoint)
                        result = attach_template_path(result, endpoint)
                        result["test_type"] = "list_get"
                        result["category"] = constants.INVALID_QUERY_PARAM_VALUE
                        result["field"] = target_param["name"]
                        result["expected_status"] = 422
                        result["description"] = f"Invalid type for query param '{target_param["name"]}'"
                        results.append(result)

                if category_filter is None or constants.INVALID_QUERY_PARAM_ENUM in category_filter:
                    for enum_param in required_params:
                        param_schema = enum_param["schema"]
                        enum_source = param_schema.get("items", {}) if param_schema.get("type") == "array" else param_schema
                        if "enum" not in enum_source:
                            continue

                        invalid_query = {
                            p["name"]: generate_valid_value(p["schema"]) or "sample-value" for p in required_params if p["name"] != enum_param["name"]
                        }
                        invalid_query[enum_param["name"]] = "VALUE_NOT_IN_ENUM_LIST"
                        test_path = endpoint["path"] + build_query_string(invalid_query)
                        result = execute_test(base_url, endpoint["method"], test_path, data = None)
                        result = attach_schema_conformance(result, spec, endpoint)
                        result = attach_template_path(result, endpoint)
                        result["test_type"] = "list_get"
                        result["category"] = constants.INVALID_QUERY_PARAM_ENUM
                        result["field"] = enum_param["name"]
                        result["expected_status"] = 422
                        result["description"] = f"Value outside enum list for query param '{enum_param["name"]}'"
                        results.append(result)
            else:
                if category_filter is None or constants.LIST_ENDPOINT in category_filter:
                    #no req params
                    result = execute_test(base_url, endpoint["method"], endpoint["path"], data=None)
                    result = attach_schema_conformance(result, spec, endpoint)
                    result = attach_template_path(result, endpoint)
                    result["test_type"] = "list_get"
                    result["category"] = constants.LIST_ENDPOINT
                    result["field"] = None
                    result["expected_status"] = expected_success_status
                    result["acceptable_statuses"] = acceptable_success_statuses
                    result["description"] = "Get list endpoint (no filters)"
                    results.append(result)
            for skipped in get_skipped_query_categories(query_params):
                if category_filter is not None and skipped["category"] not in category_filter:
                    continue
                all_skipped.append({
                    "path": endpoint["path"],
                    "method": endpoint["method"],
                    **skipped,
                })
                    
        if endpoint["method"] in ("GET", "DELETE") and "{" in endpoint["path"]:

            path_params = get_path_params_schema(endpoint)

            if len(path_params) == 1:
                param_schema = path_params[0]["schema"]
                path_param_name = path_params[0]["name"]

                base_path = re.sub(r"/\{[^}]+\}$", "", endpoint["path"])

                real_id = (get_real_id_from_list(base_url, base_path, path_param_name,) if path_param_name else None)
            # param_schema = get_path_param_schema(endpoint)
            # base_path = re.sub(r"/\{[^}]+\}$", "", endpoint["path"])
            # path_param_match = re.search(r"\{([^}]+)\}", endpoint["path"])
            # path_param_name = path_param_match.group(1) if path_param_match else None
            # real_id = get_real_id_from_list(base_url, base_path, path_param_name) if path_param_name else None

                for case in generate_path_param_cases(param_schema):
                    if category_filter is not None and case["category"] not in category_filter:
                        continue
                    delete_setup = None
                    if (endpoint["method"] == "DELETE" and case["category"] == constants.VALID_ID):
                        delete_setup = create_resource_for_stateful_test(base_url, spec, endpoints, endpoint)
                    if delete_setup is not None:
                        value = str(delete_setup["id"])
                    else:
                        value = real_id if (case["category"] == constants.VALID_ID and real_id is not None) else case["value"]
                    test_path = fill_path_params_with_value(endpoint["path"], value)
                    result = execute_test(base_url, endpoint["method"], test_path, data=None)
                    if delete_setup is not None:
                        status = result.get("status_code")
                        if status is None or not(200<=status<300):
                            cleanup_created_resource(base_url, endpoints, delete_setup["resource_path"], delete_setup["id"])
                    result = attach_schema_conformance(result, spec, endpoint)
                    result = attach_template_path(result, endpoint)
                    result["test_type"] = "path_param"
                    result["category"] = case["category"]
                    result["field"] = None
                    if case["category"] == constants.VALID_ID:
                        success_codes = get_success_status_codes(endpoint)
                        result["expected_status"] = min(success_codes) if success_codes else 200
                        result["acceptable_statuses"] = sorted(success_codes) if success_codes else [200]
                    else:
                        result["expected_status"] = case["expected_status"]
                    result["description"] = case["description"] if value == case["value"] else f"{case['description']} (real id = {value})"
                    results.append(result)
            else:
                for target_param in path_params:
                    target_name = target_param["name"]
                    target_schema = target_param["schema"]

                    for case in generate_path_param_cases(target_schema):
                        if (category_filter is not None and case["category"] not in category_filter):
                            continue

                        if case["category"] == constants.VALID_ID:
                            continue

                        values = {}

                        for path_param in path_params:
                            param_name = path_param["name"]
                            param_schema = path_param["schema"]

                            if param_name == target_name:
                                values[param_name] = case["value"]
                            else:
                                values[param_name] = generate_valid_value(param_schema)

                        test_path = fill_path_params_with_values(endpoint["path"],values)
                        result = execute_test(base_url, endpoint["method"], test_path, data=None)
                        result = attach_schema_conformance(result, spec, endpoint)
                        result = attach_template_path(result, endpoint)
                        result["test_type"] = "path_param"
                        result["category"] = case["category"]
                        result["field"] = target_name
                        result["expected_status"] = case["expected_status"]
                        result["description"] = (
                            f"{case['description']} "
                            f"(path parameter: {target_name})"
                        )
                        results.append(result)



    if category_filter is None or constants.METHOD_NOT_ALLOWED in category_filter:
        unique_paths = list(set(ep["path"] for ep in endpoints))
        for path in unique_paths:
            declared_methods = get_declared_methods_for_path(endpoints, path)
            undeclared_methods = get_undeclared_method(declared_methods)

            if undeclared_methods is None:
                continue

            path_param_schema = None
            for ep in endpoints:
                if ep["path"] == path and "{" in path:
                    path_param_schema = get_path_param_schema(ep)
                    break
            test_path = fill_path_params(path, path_param_schema)

            result = execute_test(base_url, undeclared_methods, test_path, data=None)
            has_allow_header = check_allowed_header_present(result.get("response_headers",{}))
            result["test_type"] = "invalid"
            result["category"] = constants.METHOD_NOT_ALLOWED
            result["field"] = None
            result["expected_status"] = 405
            result["description"] = f"Undeclared method '{undeclared_methods}' on path (Allow header present: {has_allow_header})"
            result["template_path"] = path
            results.append(result)

    if category_filter is None or constants.DELETE_IDEMPOTENCY in category_filter:
        for endpoint in endpoints:
            if endpoint["method"] == "DELETE" and "{" in endpoint["path"]:
                result = test_delete_idempotency(base_url, spec, endpoints, endpoint)
                if result:
                    results.append(result)

    if category_filter is None or constants.PUT_IDEMPOTENCY in category_filter:
        for endpoint in endpoints:
            if endpoint["method"] == "PUT" and "{" in endpoint["path"]:
                result = test_put_idempotency(base_url, spec, endpoints, endpoint)
                if result:
                    results.append(result)


    return results, all_skipped


def test_delete_idempotency(base_url: str, spec:dict, endpoints: list[dict], delete_endpoint: dict) -> dict | None:
    create_endpoint = find_matching_create_endpoint(endpoints, delete_endpoint["path"])
    if create_endpoint is None:
        return None

    success_codes = get_success_status_codes(create_endpoint)
    if not success_codes:
        success_codes = {200}

    schema = get_request_body_schema(spec, create_endpoint)
    if not schema: 
        return None

    create_data = generate_valid_object(schema)
    id_field = find_id_like_field(schema)
    if id_field:
        create_data[id_field] = random.randint(10_000_000,99_999_999)
    create_result = execute_test(base_url, "POST", create_endpoint["path"], create_data)
    if create_result.get("status_code") not in success_codes:
        return {
            "category": constants.DELETE_IDEMPOTENCY,
            "field": None,
            "expected_status": None,
            "description": "Setup (POST) failed, cannot test DELETE idempotency",
            "status_code": create_result["status_code"],
            "test_type": "sequence",
            "method": "DELETE",
            "path": delete_endpoint["path"],
            "template_path": delete_endpoint["path"],
            "response_body": create_result.get("response_body"),
            "error": "Setup failed",
        }


    
    response_body = create_result.get("response_body")

    if isinstance(response_body, dict):
        create_id = response_body.get("id", create_data.get("id"))
    else:
        create_id = create_data.get("id")

    if create_id is None:
        return {
            "category": constants.DELETE_IDEMPOTENCY,
            "field": None,
            "expected_status": None,
            "description": "Setup POST succeded, but no resource ID could be determined; cannot test DELETE idempotency",
            "status_code": create_result.get("status_code"),
            "test_type": "sequence",
            "method": "DELETE",
            "path": delete_endpoint["path"],
            "template_path": delete_endpoint["path"],
            "response_body": response_body,
            "error": "Missing resource ID after setup",

        }

    test_path = fill_path_params_with_value(delete_endpoint["path"], str(create_id))
    first_delete = execute_test(base_url, "DELETE", test_path, data=None)
    #print("DEBUG: first_delete status:", first_delete["status_code"], "body:", first_delete.get("response_body"))
    time.sleep(0.1)
    second_delete = execute_test(base_url, "DELETE", test_path, data=None)
    #print("DEBUG: second_delete status:", second_delete["status_code"], "body:", second_delete.get("response_body"))

    second_delete["category"] = constants.DELETE_IDEMPOTENCY
    second_delete["field"] = None
    second_delete["expected_status"] = 404
    second_delete["test_type"] = "sequence"
    second_delete["description"] = (        f"Second DELETE on same result (id={create_id}) after successful first DELETE (first delete status:{first_delete['status_code']})")
    second_delete["template_path"] = delete_endpoint["path"]
    return second_delete



def test_put_idempotency(base_url: str, spec: dict, endpoints: list[dict], put_endpoint: dict) -> dict | None:
    schema = get_request_body_schema(spec,put_endpoint)
    if not schema:
        return None
    
    create_endpoint = find_matching_create_endpoint(endpoints, put_endpoint["path"])
    
    if create_endpoint is None:
        return None

    success_codes = get_success_status_codes(create_endpoint)
    if not success_codes:
        success_codes = {200}
    create_schema = get_request_body_schema(spec, create_endpoint)
    if not create_schema:
        return None

    #own data with unique id
    create_data = generate_valid_object(create_schema)
    id_field = find_id_like_field(create_schema)

    if id_field:
        create_data[id_field] = random.randint(10_000_000,99_999_999)

    create_result = execute_test(base_url, "POST", create_endpoint["path"], create_data)
    if create_result.get("status_code") not in success_codes:
        return {
            "category": constants.PUT_IDEMPOTENCY,
            "field": None,
            "expected_status": None,
            "description": "Setup (POST) failed, cannot test PUT idempotency",
            "status_code": create_result["status_code"],
            "test_type": "sequence",
            "method": "PUT",
            "path": put_endpoint["path"],
            "template_path": put_endpoint["path"],
            "response_body": create_result.get("response_body"),
            "error": "Setup failed",
        }  

    #created_id = create_result["response_body"].get(id_field, create_data.get(id_field)) if id_field else None
    response_body = create_result.get("response_body")
    if id_field and isinstance(response_body, dict):
        created_id  = response_body.get(id_field, create_data.get(id_field))
    elif id_field:
        created_id  = create_data.get(id_field)
    else:
        created_id = None

    path_param_schema = get_path_param_schema(put_endpoint)
    test_path = fill_path_params_with_value(put_endpoint["path"], str(created_id)) if created_id else fill_path_params(put_endpoint["path"], path_param_schema)

    #generate valid update data
    update_data = generate_valid_object(schema)
    put_id_field = find_id_like_field(schema)

    if put_id_field and created_id is not None:
        update_data[put_id_field] = int(created_id) if isinstance(created_id, int) else created_id

    first_put = execute_test(base_url, "PUT", test_path, update_data)
    second_put = execute_test(base_url, "PUT", test_path, update_data)

    #both PUT should have same result
    is_consistent = first_put["status_code"] == second_put["status_code"]

    second_put["category"] = constants.PUT_IDEMPOTENCY
    second_put["field"] = None
    second_put["expected_status"] = first_put["status_code"]
    second_put["test_type"] = "sequence"
    second_put["description"] = (
        f"Second PUT with identical data (id={created_id}): first status "
        f"{first_put['status_code']}, second status {second_put['status_code']} "
        f"({'consistent' if is_consistent else 'INCONSISTENT'})"
    )
    if created_id is not None:
        resource_path = re.sub(r"/\{[^}]+\}$","",put_endpoint["path"])
        cleanup_created_resource(base_url, endpoints, resource_path, created_id)
    second_put["template_path"] = put_endpoint["path"]
    return second_put


def get_real_id_from_list(base_url: str, list_path: str, path_param_name: str) -> str | None:
    result = execute_test(base_url, "GET", list_path, data=None)
    if result["status_code"] !=200:
        return None

    items = result.get("response_body")
    if not isinstance(items, list) or len(items) == 0:
        return None

    first_item = items[0]
    if not isinstance(first_item, dict):
        return None

    if path_param_name in first_item:
        return str(first_item[path_param_name])

    for key,value in first_item.items():
        if _is_id_like_name(key):
            return str(value)

    return None


def cleanup_if_unexpectedly_succeeded(base_url: str, endpoints: list[dict], endpoint: dict, result: dict, schema: dict):
    success_codes = get_success_status_codes(endpoint) or {200}
    if result.get("status_code") not in success_codes:
        return

    expected = result.get("expected_status")
    if expected is None or expected <400:
        return

    id_field = find_id_like_field(schema)
    if id_field is None:
        return

    response_body = result.get("response_body")
    request_data = result.get("data_sent")

    created_id = None

    if isinstance(response_body, dict) and id_field in response_body:
        created_id = response_body[id_field]
    elif isinstance(request_data, dict) and id_field in request_data:
        created_id = request_data[id_field]

    if created_id is None:
        return

    base_path = endpoint["path"]
    delete_endpoint = next( (ep for ep in endpoints if ep["method"] == "DELETE" and re.sub(r"/\{[^}]+\}$","", ep["path"]) == base_path) , None)
    if delete_endpoint is None:
        return
    cleanup_path = fill_path_params_with_value(delete_endpoint["path"], str(created_id))
    try:
        execute_test(base_url, "DELETE", cleanup_path, data=None)
    except:
        pass

def attach_template_path(result: dict, endpoint: dict) -> dict:
    result["template_path"] = endpoint["path"]
    return result

if __name__ == "__main__":
    init_db()

    base_url = "http://127.0.0.1:8000"
    category_filter = None

    run_seed = random.SystemRandom().randint(0, 2**32 -1)

    started_at = time.perf_counter()

    results, skipped = run_all_tests(base_url, category_filter = category_filter, seed = run_seed)

    duration_ms = round((time.perf_counter() - started_at) * 1000)


    #results, skipped = run_all_tests("http://127.0.0.1:8000", category_filter=["valid_id","invalid_id_format","nonexistent_id","negative_id",])
    #results, skipped = run_all_tests("http://127.0.0.1:8000", category_filter= ["put_idempotency","delete_idempotency",])
    #results, skipped = run_all_tests("http://127.0.0.1:8000", category_filter=["list_endpoint","missing_required_query_param","invalid_query_param_enum","invalid_query_param_value",])
    #results, skipped = run_all_tests("http://127.0.0.1:8000")
    #results, skipped = run_all_tests("http://127.0.0.1:8000", category_filter=["ai_implicit_constraint_violation", "ai_implicit_constraint_valid", "ai_cross_field_violation"])
    #results, skipped = run_all_tests("https://petstore3.swagger.io/api/v3", category_filter=["ai_implicit_constraint_violation", "ai_implicit_constraint_valid", "ai_cross_field_violation"])




    analysis = analyze_results(results)
    print_report(analysis)
    if skipped:
        print("\n--------Skipped categories(not defined)------------")
        for s in skipped:
            print(f"{s['method']} {s['path']} - {s['category']}: {s['reason']}")

    ai_enabled = is_ai_enabled_for_run(category_filter)
    selected_categories = get_selected_categories_for_run(category_filter)
    run_id = save_run(base_url, results, analysis, seed = run_seed, ai_enabled=ai_enabled, ai_model=AI_MODEL if ai_enabled else None, duration_ms=duration_ms, selected_categories=selected_categories)
    print(f"\nSaved as run#{run_id}")
    print(
        f"Run metadata: seed = {run_seed}, "
        f"AI = {'enabled' if ai_enabled else 'disabled'}, "
        f"model = {AI_MODEL  if ai_enabled else 'N/A'}, "
        f"duration={duration_ms} ms"
    )