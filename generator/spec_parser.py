import requests
print("STARTING--we in spec_parser--") #debug


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
                "request_body": details.get("requestBody",{})
            })
    return endpoints


def resolve_schema_ref(spec: dict, ref: str) -> dict:
    #ref "#/components/schemas/Book"
    ref_path = ref.replace("#/", "").split("/")
    schema = spec
    for part in ref_path:
        schema = schema[part]
    return schema


def get_request_body_schema(spec: dict, endpoint: dict) -> dict | None:
    request_body = endpoint.get("request_body", {})
    if not request_body:
        return None

    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    schema_ref = json_content.get("schema", {})

    if "$ref" in schema_ref:
        return resolve_schema_ref(spec, schema_ref["$ref"])
    return schema_ref




if __name__ == "__main__":
    spec = fetch_openapi_spec("http://127.0.0.1:8000")
    endpoints = extract_endpoints(spec)
    for ep in endpoints:
        if ep["method"] in ("POST", "PUT"):
            schema = get_request_body_schema(spec,ep)
            print(schema)
            print("----end----")
