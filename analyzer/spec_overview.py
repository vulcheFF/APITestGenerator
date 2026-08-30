from generator.spec_parser import extract_endpoints
from ai.ollama_client import query_ollama


def build_spec_overview(spec: dict) -> dict:
    info = spec.get("info", {})

    endpoints = extract_endpoints(spec)

    schemas = (spec.get("components", {}).get("schemas", {}))

    endpoint_items = []

    for endpoint in endpoints:
        endpoint_items.append({
            "method": endpoint["method"],
            "path": endpoint["path"],
        })

    schema_items = []

    for schema_name, schema in schemas.items():
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        schema_items.append({
            "name": schema_name,
            "fields": list(properties.keys()),
            "required_fields": list(required),
        })

    return {
        "title": info.get("title"),
        "api_version": info.get("version"),
        "openapi_version": spec.get("openapi"),
        "endpoints": endpoint_items,
        "schemas": schema_items,
    }

def format_spec_overview_for_llm(overview: dict) -> str:

    lines = [
        f"API title: {overview.get('title') or 'N/A'}",
        f"API version: {overview.get('api_version') or 'N/A'}",
        f"OpenAPI version:  {overview.get('openapi_version') or 'N/A'}",
        "",
        "Endpoints:", 
    ]

    for endpoint in overview["endpoints"]:
        lines.append(f"- {endpoint['method']} {endpoint['path']}")
    lines.append("")
    lines.append("Schemas:")

    for schema in overview["schemas"]:
        fields = ", ".join(schema["fields"]) or "none"
        required = ", ".join(schema["required_fields"]) or "none"

        lines.append(
            f"- {schema.get('name', 'Unnamed')}: "
            f"fields=[{fields}], "
            f"required=[{required}]"
        )

    return "\n".join(lines)

def analyze_spec_with_ai(overview_text: str) -> str:
    prompt = f"""
    You are analyzing an OpenAPI REST API specification.

    Based only on the structured specification summary below, provide a concise technical overview of the API.

    Include:
    - API purpose and main resources
    - Available operations and CRUD coverage
    - Important request/response data models
    - Required fields and notable structural constraints
    - Areas that appear especially important for API testing
    - Any obvious gaps or inconsistencies visible from the provided specification summary

    Do not invent endpoints, fields, constraints, authentication, or behavior that are not present in the provided data.
    If information is missing, state that it is not specified.

    OpenAPI specification summary:

    {overview_text}
    """

    response = query_ollama(prompt, timeout=60,)

    if response is None:
        return("AI analysis could not be completed because Ollama is unavailable.")

    return response