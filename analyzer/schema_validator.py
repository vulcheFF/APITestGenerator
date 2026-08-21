def validate_response_against_schema(response_body, schema: dict) -> list[str]:
    if schema is None:
        return []

    errors = []

    if "anyOf" in schema or "oneOf" in schema:
        alternatives = schema.get("anyOf") or schema.get("oneOf")
        for alt_schema in alternatives:
            alt_errors = validate_response_against_schema(response_body , alt_schema)
            if not alt_errors:
                return []
        return ["Response does not match any of the expected schemas (anyOf/oneOf)"]

    schema_type = schema.get("type")

    if schema_type == "object":
        if not isinstance(response_body, dict):
            return [f"Expected object, got {type(response_body).__name__}"]

        properties = schema.get("properties", {})
        for field_name, field_schema in properties.items():
            if field_name not in response_body:
                if field_name in schema.get("required", []):
                    errors.append(f"Missing required field '{field_name}' in response")
                continue
            field_errors = validate_response_against_schema(response_body[field_name], field_schema)
            errors.extend(field_errors)

    elif schema_type == "array":
        if not isinstance(response_body, list):
            return[f"Expected array, got {type(response_body).__name__}"]
        items_schema = schema.get("items", {})
        for i, item in enumerate(response_body):
            item_erros = validate_response_against_schema(item, items_schema)
            errors.extend([f"[item {i}] {e}" for e in item_erros])

    elif schema_type == "string":
        if not isinstance(response_body, str):
            errors.append(f"Expected string, got  {type(response_body).__name__}")

    elif schema_type == "integer":
        if not isinstance(response_body, int) or isinstance(response_body, bool):
            errors.append(f"Expected integer, got {type(response_body).__name__}")

    elif schema_type == "number":
        if not isinstance(response_body, (int, float)) or isinstance(response_body, bool):
            errors.append(f"Expected number, got {type(response_body).__name__}")

    elif schema_type == "boolean":
        if not isinstance(response_body, bool):
            errors.append(f"Expected boolean, got {type(response_body).__name__}")

    return errors