from generator import constants

def generate_path_param_cases() -> list[dict]:
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