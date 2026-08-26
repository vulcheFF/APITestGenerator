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

    if field_schema.get("type") == "object" and field_schema.get("properties"):
        nested_props = ", ".join(
            f"{name} ({prop.get('type', 'unknown')})" for name, prop in field_schema["properties"].items()
        )
        parts.append(f"This is a nested OBJECT with properties: {nested_props}")

    return "\n".join(parts)


def mine_implicit_constraint(field_name: str, field_schema: dict) -> dict | None:
    has_hints = field_schema.get("title") or field_schema.get("description") or field_schema.get("example") is not None
    if not has_hints:
        return None
    context = build_field_context(field_name, field_schema)
    declared_type = field_schema.get("type", "unknown")
    type_hint = ""
    if declared_type == "object":
        type_hint = "\nIMPORTANT: Since this field is an OBJECT, suggested_valid_example and suggested_invalid_example must be JSON objects (not plain strings), matching the nested properties described above."


    prompt = f"""You are analyzing a REST API field to find implicit constraints not captured in its formal JSON Schema type.

{context}
Declared JSON Schema type: {declared_type}{type_hint}

Based ONLY on the field name, title, description, and example above, does this field imply a specific format or constraint that a generic "{declared_type}" type would NOT enforce (e.g. email format, URL format, phone format, date format, specific value range)?

Respond ONLY with valid JSON in this exact structure:
{{"has_implicit_constraint": true/false, "constraint_description": "short description or empty string", "suggested_valid_example": "a realistic example value (JSON object if the field type is object) that correctly satisfies this implicit constraint", "suggested_invalid_example": "an example value that violates this implicit constraint but still matches the declared type"}}"""
    raw_response = query_ollama(prompt)
    #print("DEBUG raw_response:", repr(raw_response))
    if raw_response is None:
        return None

    try:
        result = json.loads(raw_response)
        #print("DEBUG parsed:", result)
        if not result.get("has_implicit_constraint"):
            #print("DEBUG: has_implicit_constraint is False/missing")
            return None
        return {
            "field": field_name,
            "constraint_description": result.get("constraint_description", ""),
            "suggested_valid_example": result.get("suggested_valid_example"),
            "suggested_invalid_example": result.get("suggested_invalid_example"),
        }
    except (json.JSONDecodeError, KeyError):
        #print("DEBUG JSON parse error:", e)
        return None


def mine_cross_field_constraint(schema: dict) -> dict | None:
    properties = schema.get("properties", {})
    field_summaries = []
    for name, prop in properties.items():
        desc = prop.get("description", "")
        field_summaries.append(f"- {name} ({prop.get('type', 'unknown')}){': ' + desc if desc else ''}")

    if not field_summaries:
        return None
    fields_text  = "\n".join(field_summaries)


    prompt = f"""You are analyzing a REST API object schema to find RELATIONSHIPS between fields that a single-field type check cannot catch.

Fields:
{fields_text}

Does any pair of fields imply a cross-field business rule
(e.g. one date must be before another, one number must be less than another)?

Only report a rule if it is clearly implied by field names/descriptions above.
Do not invent rules not suggested by the data.

The invalid values you suggest MUST:
1. individually match the declared JSON Schema type of each field;
2. violate ONLY the cross-field relationship;
3. not rely on a type mismatch to make the request invalid.

Respond ONLY with valid JSON:
{{"has_cross_field_constraint": true/false,
"constraint_description": "short description or empty string",
"field_a": "name or empty",
"field_b": "name or empty",
"invalid_value_a": "value or null",
"invalid_value_b": "value or null"}}"""

    
    raw_response = query_ollama(prompt)
    if raw_response is None:
        return None

    try:
        result = json.loads(raw_response)
        # if not result.get("has_cross_field_constraint"):
        #     return None
        #return result
    except (json.JSONDecodeError, KeyError):
        return None

    if not result.get("has_cross_field_constraint"):
        return None

    field_a = result.get("field_a")
    field_b = result.get("field_b")

    if field_a not in properties or field_b not in properties:
        return None

    if field_a == field_b:
        return None

    value_a = result.get("invalid_value_a")
    value_b = result.get("invalid_value_b")

    if value_a is None or value_b is None:
        return None

    if not _value_matches_schema_type(value_a, properties[field_a]):
        return None
    
    if not _value_matches_schema_type(value_b, properties[field_b]):
        return None

    return {
        "has_cross_field_constraint": True,
        "constraint_description": result.get("constraint_description", ""),
        "field_a": field_a,
        "field_b": field_b,
        "invalid_value_a": value_a,
        "invalid_value_b": value_b,
    }

def _value_matches_schema_type(value, field_schema: dict) -> bool:
    field_type = field_schema.get("type")

    if field_type == "string":
        return isinstance(value,str)
    if field_type == "integer":
        return isinstance(value,int) and not isinstance(value, bool)
    if field_type == "number":
        return isinstance(value,(int, float)) and not isinstance(value, bool)
    if field_type == "boolean":
        return isinstance(value,bool)
    if field_type == "array":
        return isinstance(value,list)
    if field_type == "object":
        return isinstance(value,dict)

    return True