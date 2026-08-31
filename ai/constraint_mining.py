import json
from ai.ollama_client import query_ollama

def build_field_context(field_name: str, field_schema: dict) -> str:
    parts=[f"Field name: {field_name}"]
    if field_schema.get("title"):
        parts.append(f"Title: {field_schema['title']}")
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

def _violates_formal_field_schema(value, schema: dict) -> bool:

    schema_type = schema.get("type")

    if schema_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return True

    elif schema_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return True

    elif schema_type == "string":
        if not  isinstance(value, str):
            return True
    elif schema_type == "boolean":
        if not isinstance(value, bool):
            return True

    minimum = schema.get("minimum")
    if minimum is not None and  isinstance(value, (int, float)):
        if value < minimum:
            return True
        
    maximum = schema.get("maximum")
    if maximum is not None and isinstance(value, (int, float)):
        if value > maximum:
            return True

    exclusive_minimum  = schema.get("exclusiveMinimum")
    if exclusive_minimum  is not None and  isinstance(value, (int, float)):
        if value <= exclusive_minimum :
            return True
        
    exclusive_maximum  = schema.get("exclusiveMaximum")
    if exclusive_maximum  is not None and isinstance(value, (int, float)):
        if value >= exclusive_maximum :
            return True

    enum = schema.get("enum")
    if enum is not None and value not in enum:
        return True

    pattern = schema.get("pattern")
    if pattern is not None and isinstance(value ,str):
        import re
        if re.fullmatch(pattern,value) is None:
            return True

    min_length = schema.get("minLength")
    if min_length is not None and isinstance(value, str):
        if len(value) < min_length:
            return True
        
    max_length = schema.get("maxLength")
    if max_length is not None and isinstance(value, str):
        if len(value) > max_length:
            return True

    return False


def mine_implicit_constraint(field_name: str, field_schema: dict, ai_model: str | None = None) -> dict | None:
    has_hints = field_schema.get("description") or field_schema.get("example") is not None
    if not has_hints:
        return None
    #context = build_field_context(field_name, field_schema)
    declared_type = field_schema.get("type", "unknown")
    formal_constraints = {
        key: field_schema[key]
         for key in (             
            "format",
            "pattern",
            "enum",
            "minimum",
            "maximum",
            "exclusiveMinimum",
            "exclusiveMaximum",
            "minLength",
            "maxLength",
            "minItems",
            "maxItems",
            "uniqueItems",
        )
        if field_schema.get(key) is not None
    }
    # type_hint = ""

    # if declared_type == "object":
    #     type_hint = "\nIMPORTANT: Since this field is an OBJECT, suggested_valid_example and suggested_invalid_example must be JSON objects (not plain strings), matching the nested properties described above."


    prompt = f"""
        You are analyzing an OpenAPI field for possible implicit validation constraints.

        Field name: {field_name}
        Declared type: {declared_type}
        Description: {field_schema.get("description")}
        Example: {field_schema.get("example")}
        Declared formal constraints: {formal_constraints or "none"}

        Your task is to identify ONLY an additional single-field constraint that is
        clearly implied by the field description or example, but is NOT already
        represented by the declared OpenAPI/JSON Schema constraints above.

        Important rules:

        1. Do NOT infer constraints from the field name alone.

        2. Do NOT treat an automatically generated OpenAPI title or human-readable
        field label as evidence of a constraint.

        3. Do NOT report constraints that are already formally declared through:
        - format
        - pattern
        - enum
        - minimum / maximum
        - exclusiveMinimum / exclusiveMaximum
        - minLength / maxLength
        - minItems / maxItems
        - uniqueItems

        4. Do NOT report relationships involving another field.
        For example:
        - "discount_price must be lower than price"
        - "start_date must be before end_date"
        - "password_confirmation must equal password"

        These are cross-field constraints and must be handled separately.

        5. Do NOT invent general semantic expectations such as:
        - a title should be concise or descriptive
        - an author should be a person's name
        - a genre should belong to a known category
        unless the description or example explicitly states such a requirement.

        6. A description that merely restates a formal schema constraint does NOT
        count as an additional implicit constraint.

        Examples:
        - description says "must be positive" and exclusiveMinimum=0
            -> no implicit constraint
        - description says "cannot be negative" and minimum=0
            -> no implicit constraint
        - description says "must be a valid date" and format="date"
            -> no implicit constraint

        7. Only return has_implicit_constraint=true when there is clear evidence of
        an additional single-field rule that is not formally represented in the
        schema.

        8. If the evidence is weak, ambiguous, stylistic, domain-assumptive, or
        already covered by the schema, return has_implicit_constraint=false.

        Return ONLY valid JSON in this exact structure:

        {{
            "has_implicit_constraint": true or false,
            "constraint": "short description of the additional constraint, or null",
            "valid_example": "example satisfying the constraint, or null",
            "invalid_example": "example violating the constraint, or null",
            "reason": "brief explanation based only on the provided description/example"
        }}
        """
    raw_response = query_ollama(prompt, model = ai_model)
    #print("DEBUG raw_response:", repr(raw_response))
    if raw_response is None:
        return None

    try:
        result = json.loads(raw_response)
        #print("DEBUG parsed:", result)
        if not result.get("has_implicit_constraint"):
            return None

        constraint_description = result.get("constraint")
        valid_example = result.get("valid_example")
        invalid_example = result.get("invalid_example")

        if (not isinstance(constraint_description, str) or not constraint_description.strip()):
            return None
        
        if valid_example is None or invalid_example is None:
            return None
        
        if _violates_formal_field_schema(invalid_example, field_schema):
            return None
        
        if _violates_formal_field_schema(valid_example, field_schema):
            return None
        

        return {
            "field": field_name,
            "constraint_description": constraint_description.strip(),
            "suggested_valid_example": valid_example,
            "suggested_invalid_example": invalid_example,
        }
    except (json.JSONDecodeError, KeyError):
        #print("DEBUG JSON parse error:", e)
        return None







def mine_cross_field_constraint(schema: dict, ai_model: str | None = None) -> dict | None:
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

    
    raw_response = query_ollama(prompt, model=ai_model)
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

    if _violates_formal_field_schema(value_a, properties[field_a]):
        return None
    
    if _violates_formal_field_schema(value_b, properties[field_b]):
        return None

    constraint_description = result.get("constraint_description")
    if (not isinstance(constraint_description, str) or not constraint_description.strip()):
        return None
        
    return {
        "has_cross_field_constraint": True,
        "constraint_description": constraint_description.strip(),
        "field_a": field_a,
        "field_b": field_b,
        "invalid_value_a": value_a,
        "invalid_value_b": value_b,
    }

