def generate_path_param_cases() -> list[dict]:
    return [
        {"case_id": "valid_id", "value": "1", "description": "Valid existing ID"},
        {"case_id": "nonexistent_id","value": "999999", "description": "Non-existent ID"},
        {"case_id": "invalid_format","value": "abc", "description": "Invalid ID format (string insted of int)"},
        {"case_id": "negative_id","value": "-1", "description": "Negative ID"},
    ]