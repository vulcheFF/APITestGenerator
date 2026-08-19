import string
import random
from generator import constants

def generate_valid_value(field_schema: dict):
    field_type = field_schema.get("type")

    if "enum" in field_schema:
        return random.choice(field_schema["enum"])

    if field_type == "boolean":
        return random.choice([True, False])


    if field_type == "string":
        if field_schema.get("format") == "date":
            return "2020-01-01"
        min_length = field_schema.get("minLength",1)
        max_length = field_schema.get("maxLength",8)
        length = random.randint(min_length, max_length)
        return "".join(random.choices(string.ascii_letters, k = length))

    if field_type == "integer":
        minimum = field_schema.get("minimum",1)
        maximum = field_schema.get("maximum",100)
        return random.randint(minimum, maximum)

    if field_type == "number":
        minimum = field_schema.get("minimum",1)
        maximum = field_schema.get("maximum",100)
        return round(random.uniform(minimum, maximum),2)

    return None #mroe to come



def generate_valid_object(schema: dict) -> dict:
    properties = schema.get("properties", {})
    return {
        field_name: generate_valid_value(field_schema)
        for field_name, field_schema in properties.items()
    }


def _invalid_type_value(field_schema: dict):
    field_type = field_schema.get("type")

    if field_type == "string":
        return 12345 

    if field_type == "integer":
        return "not_an_integer"

    if field_type == "number":
        return "not_a_number"
    
    if field_type == "boolean":
        return "not_a_boolean"
    
    return None 


def generate_invalid_objects(schema: dict) -> list[dict]:
    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])
    test_cases = []

    #1: mismatch type
    for field_name, field_schema in properties.items():
        field_type = field_schema.get("type")


        obj = generate_valid_object(schema)
        obj[field_name] = _invalid_type_value(field_schema)
        test_cases.append({
            "category": constants.TYPE_MISMATCH,
            "field": field_name,
            "expected_status": 422,
            "description": f"Invalid type for field '{field_name}'",
            "data": obj,
        })

        #boundary numeric - minimum
        if field_type in ("integer", "number") and field_schema.get("minimum") is not None:
            obj = generate_valid_object(schema)
            obj[field_name] = field_schema["minimum"] - 1
            test_cases.append({
                "category": constants.BOUNDARY_NUMERIC,
                "field": field_name,
                "expected_status": 422,
                "description": f"Value below minimum for field '{field_name}'",
                "data": obj,
            })

        #boundary string - maxLength
        if field_type == "string" and field_schema.get("maxLength") is not None:
            obj = generate_valid_object(schema)
            obj[field_name] = "x" * (field_schema["maxLength"] + 1)
            test_cases.append({
                "category": constants.BOUNDARY_STRING,
                "field": field_name,
                "expected_status": 422,
                "description": f"Value exceeds maxLength for field '{field_name}'",
                "data": obj,
            })
        #invalid enum
        if "enum" in field_schema:
            obj = generate_valid_object(schema)
            obj[field_name] = "VALUE_NOT_IN_ENUM_LIST"
            test_cases.append({
                "category": constants.INVALID_ENUM,
                "field": field_name,
                "expected_status": 422,
                "description": f"Value outside enum list for field '{field_name}'",
                "data": obj,
            })

        #invalid boolean
        if field_type == "boolean":
            obj = generate_valid_object(schema)
            obj[field_name] = "not_a_boolean"
            test_cases.append({
                "category": constants.INVALID_BOOLEAN,
                "field": field_name,
                "expected_status": 422,
                "description": f"Value outside enum list for field '{field_name}'",
                "data": obj,
            })
   
    # missing req
    for field_name in required_fields:
        obj = generate_valid_object(schema)
        del obj[field_name]
        test_cases.append({
                "category": constants.MISSING_REQUIRED,
                "field": field_name,
                "expected_status": 422,
                "description": f"Missing required for field '{field_name}'",
                "data": obj,
            })

    return test_cases


def get_skipped_categories(schema: dict) -> list[dict]:
    properties = schema.get("properties", {})


if __name__ == "__main__":
    # print(generate_valid_value({"type":"string"}))
    # print(generate_valid_value({"type":"integer"}))
    # print(generate_invalid_value({"type":"number"}))

    valid_book_schema = {
        "properties": {
            "title": {"type": "string"},
            "price": {"type": "number"},
            "quantity": {"type": "integer"},
        },
        "required": ["title", "price"],
    }


    print("Valid Object:")
    print(generate_valid_object(valid_book_schema))

    print("\nInvalid Cases:")
    for case in generate_invalid_objects(valid_book_schema):
        print(case)