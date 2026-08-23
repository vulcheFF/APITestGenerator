import requests
#print("STARTING--we in spec_parser--") #debug

ALL_HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]

def fetch_openapi_spec(base_url: str) -> dict:
    response = requests.get(f"{base_url}/openapi.json")
    response.raise_for_status()
    return response.json()


def extract_endpoints(spec: dict) -> list[dict]:
    endpoints = []
    for path, methods in spec["paths"].items():
        for method, details, in methods.items():
            endpoints.append({
                "path": path,
                "method": method.upper(),
                "parameters": details.get("parameters",[]),
                "request_body": details.get("requestBody",{}),
                "responses": details.get("responses", {}),
            })

    return endpoints


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

    if "$ref" in schema_ref:
        return resolve_schema_ref(spec, schema_ref["$ref"])

    return schema_ref if schema_ref else None

def get_path_param_schema(endpoint: dict) -> dict | None:
    for param in endpoint.get("parameters", []):
        if param.get("in") == "path":
            return param.get("schema", {})
    return None


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



if __name__ == "__main__":
    spec = fetch_openapi_spec("http://127.0.0.1:8000")
    endpoints = extract_endpoints(spec)
    for ep in endpoints:
        if ep["method"] in ("POST", "PUT"):
            schema = get_request_body_schema(spec,ep)
            print(schema)
            print("----end----")
