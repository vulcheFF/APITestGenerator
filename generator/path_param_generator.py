from generator import constants

def generate_path_param_cases(param_schema: dict | None= None) -> list[dict]:
    param_type = (param_schema or {}).get("type", "integer")

    if param_type == "integer":
        return _generate_integer_cases()
    elif param_type == "string":
        return _generate_string_cases(param_schema)
    elif param_type == "number":
        return _generate_number_cases()
    elif param_type == "boolean":
        return _generate_boolean_cases()
    else:
        return _generate_generic_cases()

    
def _generate_integer_cases() -> list[dict]:
    return [
        {
            #"case_id": constants.VALID_ID,
            "category": constants.VALID_ID,
            "value": "1",
            "expected_status": 200,
            "description": "Valid existing ID"
        },
        {
            #"case_id": constants.NONEXISTENT_ID,
            "category": constants.NONEXISTENT_ID,
            "value": "999999",
            "expected_status": 404,
            "description": "Non-existent ID"
        },
        {
            #"case_id": constants.INVALID_ID_FORMAT,
            "category": constants.INVALID_ID_FORMAT,
            "value": "abc",
            "expected_status": 422,
            "description": "Invalid ID format (string instead of int)"
        },
        {
            #"case_id": constants.NEGATIVE_ID,
            "category": constants.NEGATIVE_ID,
            "value": "-1",
            "expected_status": 404,
            "description": "Negative ID"
        },
    ]

def _generate_string_cases(param_schema: dict) -> list[dict]:
    cases = [
        {
            "category": constants.VALID_ID,
            "value": "existing-item",
            "expected_status": 200,
            "description": "Valid existing identifier",
        },
        {
            "category": constants.NONEXISTENT_ID,
            "value": "existing-item",
            "expected_status": 404,
            "description": "Valid existing identifier",
        },
    ]

    if param_schema and param_schema.get("pattern"):
        cases.append({
            "category": constants.INVALID_PATTERN,
            "value": "###does-not-match-pattern###",
            "expected_status": 422,
            "description": "Valid existing identifier",
        })

    return cases

def _generate_number_cases() -> list[dict]:
    return [
        {
            "category": constants.VALID_ID,
            "value": "1.5",
            "expected_status": 200,
            "description": "Valid existing ID (float)"
        },
        {
            "category": constants.NONEXISTENT_ID,
            "value": "999999.99",
            "expected_status": 404,
            "description": "Non-existent ID (float)"
        },
        {
            "category": constants.INVALID_ID_FORMAT,
            "value": "not-a-number",
            "expected_status": 422,
            "description": "Invalid ID format (string instead of number)"
        },
        {
            "category": constants.NEGATIVE_ID,
            "value": "-1.5",
            "expected_status": 404,
            "description": "Negative ID (float)"
        },  
    ]

def _generate_boolean_cases() -> list[dict]:
    return [
        {
            "category": constants.VALID_ID,
            "value": "true",
            "expected_status": 200,
            "description": "Valid boolean identifier"
        },
        {
            "category": constants.INVALID_ID_FORMAT,
            "value": "not-a-boolean",
            "expected_status": 422,
            "description": "Invalid boolean format"
        },
    ]

def _generate_generic_cases() -> list[dict]:
    return [
        {
            "category": constants.VALID_ID,
            "value": "1",
            "expected_status": 200,
            "description": "Valid boolean identifier (generic fallback)"
        },
        {
            "category": constants.NONEXISTENT_ID,
            "value": "999999",
            "expected_status": 422,
            "description": "Non-existent identified (generic fallback)"
        },
    ]