import string
import random
import exrex
from generator import constants

def generate_valid_object(schema: dict) -> dict:
    properties = schema.get("properties", {})
    return {
        field_name: generate_valid_value(field_schema)
        for field_name, field_schema in properties.items()
    }


def generate_valid_value(field_schema: dict):
    field_type = field_schema.get("type")

    if "enum" in field_schema:
        return random.choice(field_schema["enum"])

    if field_type == "boolean":
        return random.choice([True, False])


    if field_type == "string":
        if field_schema.get("pattern"):
            return exrex.getone(field_schema["pattern"])

        if field_schema.get("format") in ("date", "date-time"):
            if field_schema.get("format") == "date-time":
                return "2020-01-01T00:00:00Z"
            return "2020-01-01"
        
        min_length = field_schema.get("minLength",1)
        max_length = field_schema.get("maxLength",8)
        length = random.randint(min_length, max_length)
        return "".join(random.choices(string.ascii_letters, k = length))

    if field_type == "integer":
        minimum = field_schema.get("minimum")
        exclusive_min = field_schema.get("exclusiveMinimum")
        if exclusive_min is not None:
            minimum = int(exclusive_min)+1
        elif minimum is not None:
            minimum = int(minimum)
        else:
            minimum = 1

        maximum = field_schema.get("maximum")
        exclusive_max = field_schema.get("exclusiveMaximum")
        if exclusive_max is not None:
            maximum = int(exclusive_max)-1
        elif maximum is not None:
            maximum = int(maximum)
        else:
            maximum = 100

        return random.randint(minimum, maximum)

    if field_type == "number":
        minimum = field_schema.get("minimum")
        exclusive_min = field_schema.get("exclusiveMinimum")
        if exclusive_min is not None:
            minimum = exclusive_min + 0.01
        elif minimum is  None:
            minimum = 1

        maximum = field_schema.get("maximum")
        exclusive_max = field_schema.get("exclusiveMaximum")
        if exclusive_max is not None:
            maximum = exclusive_max- 0.01
        elif maximum is  None:
            maximum = 100

        return round(random.uniform(minimum, maximum),2)

    if field_type == "array":
        items_schema = field_schema.get("items", {})
        min_items = field_schema.get("minItems", 1)
        max_items = field_schema.get("maxItems", 3)
        count = random.randint(min_items, max_items) if max_items >= min_items else min_items
        return [generate_valid_value(items_schema) for _ in range(count)]

    if field_type == "object":
        return generate_valid_object(field_schema)

    return None





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

    if field_type == "array":
        return "not_an_array"

    if field_type == "object":
        return "not_an_object"
    
    
    return None 

def _valid_value_for_negative_test(field_schema: dict):
    field_type = field_schema.get("type")
    if field_type == "integer":
        return random.randint(1,100)
    if field_type == "number":
        return round(random.uniform(1,100),2)
    return 1



def generate_invalid_objects(schema: dict) -> list[dict]:
    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])
    test_cases = []

    
    for field_name, field_schema in properties.items():
        field_type = field_schema.get("type")

        #mismatch
        obj = generate_valid_object(schema)
        obj[field_name] = _invalid_type_value(field_schema)
        test_cases.append({
            "category": constants.TYPE_MISMATCH,
            "field": field_name,
            "expected_status": 422,
            "description": f"Invalid type for field '{field_name}'",
            "data": obj,
        })

        #info for false positive - negative numbers
        if (field_type in ("integer", "number") and field_schema.get("minimum") is None and field_schema.get("exclusiveMinimum") is None):
            obj = generate_valid_object(schema)
            obj[field_name] = -abs(_valid_value_for_negative_test(field_schema))
            test_cases.append({
                "category": constants.NEGATIVE_VALUE,
                "field": field_name,
                "expected_status": 422,
                "description": (
                    f"Field '{field_name}' has no declared 'minimum' - "
                    f"can be false positive due to testing negative value"
                                ),
                "data": obj,          
            })

        #boundary numeric - minimum
        if field_type in ("integer", "number"):
            minimum = field_schema.get("minimum")
            exclusive_minimum = field_schema.get("exclusiveMinimum")
            invalid_value = None
            if exclusive_minimum is not None:
                invalid_value = exclusive_minimum
            elif minimum is not None:
                invalid_value = minimum - 1
            if invalid_value is not None:
                obj = generate_valid_object(schema)
                obj[field_name] = invalid_value
                test_cases.append({
                    "category": constants.BOUNDARY_NUMERIC,
                    "field": field_name,
                    "expected_status": 422,
                    "description": f"Value at/below minimum boundary for field '{field_name}'",
                    "data": obj,
                })

        #boundary numeric - maximum
        if field_type in ("integer", "number"):
            maximum = field_schema.get("maximum")
            exclusive_maximum = field_schema.get("exclusiveMaximum")

            invalid_value = None
            if exclusive_maximum is not None:
                invalid_value = exclusive_maximum
            elif maximum is not None:
                invalid_value = maximum + 1
            if invalid_value is not None:
                obj = generate_valid_object(schema)
                obj[field_name] = invalid_value
                test_cases.append({
                    "category": constants.BOUNDARY_NUMERIC,
                    "field": field_name,
                    "expected_status": 422,
                    "description": f"Value at/above maximum for field '{field_name}'",
                    "data": obj,
                })

        #boundary string - minLength
        if field_type == "string" and field_schema.get("minLength") is not None:
            obj = generate_valid_object(schema)
            obj[field_name] = "x" * (field_schema["minLength"] - 1)
            test_cases.append({
                "category": constants.BOUNDARY_STRING,
                "field": field_name,
                "expected_status": 422,
                "description": f"Value below minLength for field '{field_name}'",
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

        #invalid pattern (regex)
        if field_type == "string" and field_schema.get("pattern"):
            obj = generate_valid_object(schema)
            obj[field_name] = "###DOES_NOT_MATCH_PATTERN###"
            test_cases.append({
                "category": constants.INVALID_PATTERN,
                "field": field_name,
                "expected_status": 422,
                "description": f"Value does not match required pattern for field '{field_name}'",
                "data": obj,
            })
        #invalid array item type - ok length, wrong type
        if field_type == "array" and field_schema.get("items"):
            obj = generate_valid_object(schema)
            items_schema = field_schema["items"]
            obj[field_name] = [_invalid_type_value(items_schema)]
            test_cases.append({
                "category": constants.INVALID_ARRAY_ITEM_TYPE,
                "field": field_name,
                "expected_status": 422,
                "description": f"Array with ok length but wrong type element for field '{field_name}'",
                "data": obj,
            })
            
        #array boundary - <minItems or >maxItems
        if field_type == "array":
            
            min_items = field_schema.get("minItems")
            max_items = field_schema.get("maxItems")
            items_schema = field_schema.get("items", {})

            if min_items is not None and min_items > 0:
                obj = generate_valid_object(schema)
                items_schema = field_schema["items"]
                obj[field_name] = [generate_valid_value(items_schema) for _ in range(min_items-1)]
                test_cases.append({
                    "category": constants.ARRAY_BOUNDARY,
                    "field": field_name,
                    "expected_status": 422,
                    "description": f"Array below minItems for field '{field_name}'",
                    "data": obj,
                })

            if max_items is not None:
                obj = generate_valid_object(schema)
                items_schema = field_schema["items"]
                obj[field_name] = [generate_valid_value(items_schema) for _ in range(max_items + 1)]
                test_cases.append({
                    "category": constants.ARRAY_BOUNDARY,
                    "field": field_name,
                    "expected_status": 422,
                    "description": f"Array above minItems for field '{field_name}'",
                    "data": obj,
                })

            #duplicate_array_items - uniqueItems
            if field_type == "array" and field_schema.get("uniqueItems"):
                obj = generate_valid_object(schema)
                items_schema = field_schema.get("items", {})
                duplicate_value = generate_valid_value(items_schema)
                obj[field_name] = [duplicate_value, duplicate_value]
                test_cases.append({
                    "category": constants.DUPLICATE_ARRAY_ITEMS,
                    "field": field_name,
                    "expected_status": 422,
                    "description": f"Array with duplicate items for field '{field_name}'",
                    "data": obj,
                })

        if field_type == "object" and field_schema.get("properties"):
            nested_properties = field_schema["properties"]
            for nested_field_name, nested_field_schema in nested_properties.items():
                obj = generate_valid_object(schema)
                nested_obj = generate_valid_object(field_schema)
                nested_obj[nested_field_name] = _invalid_type_value(nested_field_schema)
                obj[field_name] = nested_obj
                test_cases.append({
                    "category": constants.NESTED_TYPE_MISMATCH,
                    "field": f"{field_name}.{nested_field_name}",
                    "expected_status": 422,
                    "description": f"Invalid type for nested field '{field_name}.{nested_field_name}'",
                    "data": obj,
                })
                break #only first nested field            

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
    skipped = []

    has_min = any(p.get("type") in ("integer", "number") and (p.get("minimum") is not None or p.get("exclusiveMinimum") is not None) for p in properties.values())
    has_max = any(p.get("type") in ("integer", "number") and (p.get("maximum") is not None or p.get("exclusiveMaximum") is not None) for p in properties.values())

    if not has_min and not has_max:
        skipped.append({
            "category": constants.BOUNDARY_NUMERIC,
            "reason": "No numeric field has 'minimum'/'exclusiveMinimum' or 'maximum'/'exclusiveMaximum' in the schema",
        })

    has_minLength = any(p.get("type")=="string" and p.get("minLength") is not None for p in properties.values())
    has_maxLength = any(p.get("type")=="string" and p.get("maxLength") is not None for p in properties.values())
    if not has_minLength and not has_maxLength :
        skipped.append({
            "category": constants.BOUNDARY_STRING,
            "reason": "No string field has 'minLength' or 'maxLength' in the schema",
        })

    has_numeric_without_minimum = any(p.get("type") in ("integer", "number") and p.get("minimum") is None and  p.get("exclusiveMinimum") is None for p in properties.values())
    if not has_numeric_without_minimum:
        skipped.append({
            "category": constants.NEGATIVE_VALUE,
            "reason": "All numeric fields already have 'minnimum'/'eclusiveMinimum' decalred or no numeric fields exist in the schema",
        })    
    
    if not any("enum" in p for p in properties.values()):
        skipped.append({
            "category": constants.INVALID_ENUM,
            "reason": "No field has enum in the schema",
        })

    if not any(p.get("type") == "boolean" for p in properties.values()):
        skipped.append({
            "category": constants.INVALID_BOOLEAN,
            "reason": "No boolean field in the schema"
        })

    has_pattern = any(p.get("type") == "string" and p.get("pattern") for p in properties.values())
    if not has_pattern:
        skipped.append({
            "category": constants.INVALID_PATTERN,
            "reason": "No string field has 'pattern' in the schema"
        })

    has_array_items_type = any(p.get("type")=="array" and p.get("items", {}).get("type") is not None for p in properties.values())
    if not has_array_items_type:
        skipped.append({
            "category": constants.INVALID_ARRAY_ITEM_TYPE,
            "reason": "No array field has 'items' with decalred type in the schema"
        })

    has_array_bounds = any(p.get("type")=="array" and (p.get("minItems") is not None or p.get("maxItems") is not None) for p in properties.values())
    if not has_array_bounds:
        skipped.append({
            "category": constants.ARRAY_BOUNDARY,
            "reason": "No array field has 'minItems' or 'maxItems' in the schema"
        })
    has_unique_items = any(p.get("type") == "array" and p.get("uniqueItems") is True for p in properties.values())
    if not has_unique_items:
        skipped.append({
            "category": constants.DUPLICATE_ARRAY_ITEMS,
            "reason": "No array field has 'uniqueItems' in the schema"
        })

    has_nested_object = any(p.get("type") == "object" and p.get("properties") for p in properties.values())
    if not has_nested_object:
        skipped.append({
            "category": constants.NESTED_TYPE_MISMATCH,
            "reason": "No nested object field with 'properties' in the schema"
        }) 

    return skipped

                
if __name__ == "__main__":
    # print(generate_valid_value({"type":"string"}))
    # print(generate_valid_value({"type":"integer"}))
    # print(generate_invalid_value({"type":"number"}))

    sample_schema = {
        "properties": {
            "field_1": {"type": "string", "maxLength": 5},
            "field_2": {"type": "number", "minimum": 0},
            "field_3": {"type": "boolean"},
        },
        "required": ["field_1"],
    }

    print("Valid object:", generate_valid_object(sample_schema))
    print("\nGenerated invalid test cases:")
    for case in generate_invalid_objects(sample_schema):
        print(f"[{case['category']}] {case['description']}")