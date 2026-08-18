import string
import random

def generate_valid_value(field_schema: dict):
    field_type = field_schema.get("type")

    if field_type == "string":
        if field_schema.get("format") == "date":
            return "2020-01-01"
        return "".join(random.choices(string.ascii_letters, k = 8))

    if field_type == "integer":
        return random.randint(1, 100)

    if field_type == "number":
        return round(random.uniform(1, 100), 2)

    return None #mroe to come

def generate_invalid_value(field_schema: dict):
    field_type = field_schema.get("type")

    if field_type == "string":
        return 12345 

    if field_type == "integer":
        return -1

    if field_type == "number":
        return -99.99
    
    return None #mroe to come

def generate_valid_object(schema: dict) -> dict:
    properties = schema.get("properties", {})
    return {
        field_name: generate_valid_value(field_schema)
        for field_name, field_schema in properties.items()
    }

def generate_invalid_objects(schema: dict) -> list[dict]:
    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])
    test_cases = []

    #1: за поле, правим валидна версия с грешен тип
    for field_name, field_schema in properties.items():
        obj = generate_valid_object(schema)
        obj[field_name] = generate_invalid_value(field_schema)
        test_cases.append({
            "description": f"Invalid type for field '{field_name}'",
            "data": obj,
        })

    #2: за req поле, правим версия без него
    for field_name in required_fields:
        obj = generate_valid_object(schema)
        del obj[field_name]
        test_cases.append({
            "description": f"Missing required field '{field_name}'",
            "data": obj,
        })

    return test_cases

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