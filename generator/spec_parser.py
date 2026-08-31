import requests
import re
#print("STARTING--we in spec_parser--") #debug

ALL_HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]

def fetch_openapi_spec(base_url: str) -> dict:
    response = requests.get(f"{base_url}/openapi.json", timeout = 5)
    response.raise_for_status()
    return response.json()


def extract_endpoints(spec: dict) -> list[dict]:
    endpoints = []

    valid_methods = {
        "get",
        "post",
        "put",
        "delete",
        "patch",
        "head",
        "options",
        "trace",
    }
    for path, path_item in spec.get("paths", {}).items():
        path_paramaters = path_item.get("parameters", [])

        for method, details, in path_item.items():
            if method.lower() not in valid_methods:
                continue

            if not isinstance(details, dict):
                continue

            operation_paramaters = details.get("parameters", [])

            merged_parameters = {(param.get("name"), param.get("in")): param for param in path_paramaters}

            for param in operation_paramaters:
                merged_parameters[(param.get("name"), param.get("in"))] = param

            endpoints.append({
                "path": path,
                "method": method.upper(),
                "parameters": list(merged_parameters.values()),
                "request_body": details.get("requestBody",{}),
                "responses": details.get("responses", {}),
            })

    return endpoints

def get_expected_success_status(endpoint: dict) ->  int | None:
    success_codes = get_success_status_codes(endpoint)

    if not success_codes:
        return None

    return min(success_codes)

def get_success_status_codes(endpoint: dict) -> set[int]:
    responses = endpoint.get("responses", {})

    return {int(status_code) for status_code in responses if str(status_code).isdigit() and 200<= int(status_code) < 300}

def resolve_schema_ref(spec: dict, ref: str) -> dict:
    #ref "#/components/schemas/Book"
    ref_path = ref.replace("#/", "").split("/")
    schema = spec
    for part in ref_path:
        schema = schema[part]
    return schema

def resolve_all_refs(spec: dict, schema: dict, _seen: set = None, _depth: int = 0, _max_depth: int = 15) -> dict:
    if _depth > _max_depth:
        return {}

    if _seen is None:
        _seen = set()

    if not isinstance(schema, dict):
        return schema

    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in _seen:
            return {}
        _seen = _seen | {ref}
        resolved = resolve_schema_ref(spec,ref)
        return resolve_all_refs(spec, resolved, _seen, _depth + 1, _max_depth)

    result = dict(schema)
    if "properties" in result:
        result["properties"] = {
            k: resolve_all_refs(spec, v, _seen, _depth +1, _max_depth) for k, v in result["properties"].items()
        }

    if "items" in result:
        result["items"] = resolve_all_refs(spec, result["items"], _seen, _depth + 1, _max_depth)

    if isinstance(result.get("additionalProperties"), dict):
        result["additionalProperties"] = resolve_all_refs(spec, result["additionalProperties"], _seen=_seen.copy(),_depth = _depth+1, _max_depth = _max_depth )

    for keyword in ("oneOf", "anyOf", "allOf"):
        if keyword in result and isinstance(result[keyword], list):
            result[keyword] = [resolve_all_refs(spec, item, _seen = _seen.copy(), _depth = _depth+1, _max_depth = _max_depth) if isinstance(item, dict) else item for item in result[keyword]]

    return result


def get_request_body_schema(spec: dict, endpoint: dict) -> dict | None:
    request_body = endpoint.get("request_body", {})
    if not request_body:
        return None

    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    schema_ref = json_content.get("schema", {})

    if "$ref" in schema_ref:
        schema =  resolve_schema_ref(spec, schema_ref["$ref"])
    else:
        schema = schema_ref

    return resolve_all_refs(spec, schema)

def get_response_schema(spec: dict, endpoint: dict, status_code: str) -> dict | None:
    responses = endpoint.get("responses", {})
    response = responses.get(status_code, {}) or responses.get("default", {})

    content = response.get("content", {})
    json_content = content.get("application/json", {})
    schema_ref = json_content.get("schema", {})

    if not schema_ref:
        return None

    return resolve_all_refs(spec, schema_ref)

def get_path_param_schema(endpoint: dict) -> dict | None:
    for param in endpoint.get("parameters", []):
        if param.get("in") == "path":
            return param.get("schema", {})
    return None

def get_path_params_schema(endpoint: dict) -> list[dict]:
    path_params = []

    for param in endpoint.get("parameters", []):
        if param.get("in") == "path":
            path_params.append({
                "name":param.get("name"),
                "required": param.get("required", True),
                "schema": param.get("schema", {}),
            })
            
    return path_params

def get_query_params_schema(endpoint: dict) -> list[dict]:
    query_params = []
    for param in endpoint.get("parameters", []):
        if param.get("in") == "query":
            query_params.append({
                "name": param.get("name"),
                "required": param.get("required", False),
                "schema": param.get("schema", {}),
            })
    return query_params


def get_declared_methods_for_path(endpoints: list[dict], path: str) -> list[str]:
    return [ep["method"] for ep in endpoints if ep["path"] == path]

def get_undeclared_method(declared_methods: list[str]) -> str | None:
    for method in ALL_HTTP_METHODS:
        if method not in declared_methods:
            return method
    return None

def find_matching_create_endpoint(endpoints: list[dict], delete_path: str) -> dict | None:
    base_path = re.sub(r"/\{[^}]+\}$","",delete_path)
    for ep in endpoints:
        if ep["method"] == "POST" and ep["path"] == base_path:
            return ep
    return None


if __name__ == "__main__":
    spec = fetch_openapi_spec("http://127.0.0.1:8000")
    endpoints = extract_endpoints(spec)
    for ep in endpoints:
        if ep["method"] in ("POST", "PUT"):
            schema = get_request_body_schema(spec,ep)
            print(schema)
            print("----end----")
