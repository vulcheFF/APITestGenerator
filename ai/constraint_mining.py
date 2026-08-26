import json
from ai.ollama_client import query_ollama

def build_field_context(field_name: str, field_schema: dict) -> str:
    parts=[f"Field name: {field_name}"]
    if field_schema.get("title"):
        parts.append(f"Tittle: {field_schema['title']}")
    if field_schema.get("description"):
        parts.append(f"Description: {field_schema['description']}")
    if field_schema.get("example") is not None:
        parts.append(f"Example value: {field_schema['example']}")
    return "\n".join(parts)


def mine_implicit_constraint(field_name: str, field_schema: dict) -> dict | None:
    has_hints = field_schema.get("title") or field_schema.get("description") or field_schema.get("example") is not None
    if not has_hints:
        return None
    context = build_field_context(field_name, field_schema)
    declared_type = field_schema.get("type", "unknown")

    prompt = f"""You are analyzing a REST API field to find implicit constraints not captured in its formal JSON Schema type.

{context}
Declared JSON Schema type: {declared_type}

Based ONLY on the field name, title, description, and example above, does this field imply a specific format or constraint that a generic "{declared_type}" type would NOT enforce (e.g. email format, URL format, phone format, date format, specific value range)?

Respond ONLY with valid JSON in this exact structure:
{{"has_implicit_constraint": true/false, "constraint_description": "short description or empty string", "suggested_valid_example": "a realistic example value that correctly satisfies this implicit constraint", "suggested_invalid_example": "an example value that violates this implicit constraint but still matches the declared type"}}"""

    raw_response = query_ollama(prompt)
    if raw_response is None:
        return None

    try:
        result = json.loads(raw_response)
        if not result.get("has_implicit_constraint"):
            return None
        return {
            "field": field_name,
            "constraint_description": result.get("constraint_description", ""),
            "suggested_valid_example": result.get("suggested_valid_example"),
            "suggested_invalid_example": result.get("suggested_invalid_example"),
        }
    except (json.JSONDecodeError, KeyError):
        return None