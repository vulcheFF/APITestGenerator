import string
import random
import exrex
from generator import constants
from ai.constraint_mining import mine_implicit_constraint, mine_cross_field_constraint

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


def generate_mass_assignment_case(schema: dict) -> dict | None:
    if schema.get("additionalProperties") is not False:
        return None

    obj = generate_valid_object(schema)
    obj["injected_extra_field"] = "unexpected_value"
    return {
        "category": constants.MASS_ASSIGNMENT,
        "field": "injected_extra_field",
        "expected_status": 422,
        "description": "Extra undeclared field injected (additionalProperties: false declared)",
        "data": obj,
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

    if schema.get("type") == "array":
        items_schema = schema.get("items", {})
        test_cases = []

        #wrong root type
        test_cases.append({
            "category": constants.TYPE_MISMATCH,
            "field": None,
            "expected_status": 422,
            "description": f"Invalid root: expected array",
            "data": _invalid_type_value(schema),
        })

        #wrong item type
        if items_schema:
            test_cases.append({
                "category": constants.INVALID_ARRAY_ITEM_TYPE,
                "field": None,
                "expected_status": 422,
                "description": f"Root array with invalid item type",
                "data": [_invalid_type_value(items_schema)],
            })

        #min items
        min_items = schema.get("minItems")
        if min_items is not None and min_items > 0:
            test_cases.append({
                "category": constants.ARRAY_BOUNDARY,
                "field": None,
                "expected_status": 422,
                "description": f"Root array below minItems",
                "data": [generate_valid_value(items_schema) for _ in range(min_items - 1)],
            })

        #max items
        
        if max_items is not None:
            test_cases.append({
                "category": constants.ARRAY_BOUNDARY,
                "field": None,
                "expected_status": 422,
                "description": f"Root array above maxItems",
                "data": [generate_valid_value(items_schema) for _ in range(max_items + 1)],
            })

        #unique items
        if schema.get("uniqueItems") is True and items_schema:
            duplicate_value = generate_valid_value(items_schema)
            test_cases.append({
                "category": constants.DUPLICATE_ARRAY_ITEMS,
                "field": None,
                "expected_status": 422,
                "description": f"Root array with duplicate items",
                "data": [duplicate_value, duplicate_value],
            })

        return test_cases


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
                obj[field_name] = [generate_valid_value(items_schema) for _ in range(max_items + 1)]
                test_cases.append({
                    "category": constants.ARRAY_BOUNDARY,
                    "field": field_name,
                    "expected_status": 422,
                    "description": f"Array above maxItems for field '{field_name}'",
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
            if field_type == "array" and field_schema.get("minItems") is None:
                obj = generate_valid_object(schema)
                obj[field_name] = []
                test_cases.append({
                    "category": constants.EMPTY_ARRAY,
                    "field": field_name,
                    "expected_status": 422,
                    "description": f"Empty array for field '{field_name}' (no minItems declared)",
                    "data": obj,
                })

        if field_type == "object" and field_schema.get("properties"):
            nested_properties = field_schema["properties"]
            nested_required = field_schema.get("required", [])

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

            for nested_required_field in nested_required:
                obj = generate_valid_object(schema)
                nested_obj = generate_valid_object(field_schema)
                del nested_obj[nested_required_field]
                obj[field_name] = nested_obj
                test_cases.append({
                    "category": constants.NESTED_MISSING_REQUIRED,
                    "field": f"{field_name}.{nested_required_field}",
                    "expected_status": 422,
                    "description": f"Missing required nested field '{field_name}.{nested_required_field}'",
                    "data": obj,
                })
                break

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

from concurrent.futures import ThreadPoolExecutor

def generate_ai_constraint_cases(schema: dict, put_id_sync: dict | None = None, ai_model: str | None = None) -> list[dict]:

    properties = schema.get("properties", {})
    test_cases = []

    field_names = set(properties.keys())

    field_items = []

    for field_name, field_schema in properties.items():
        description = str(field_schema.get("description") or "").lower()

        mentions_other_field = any(other_name != field_name and other_name.lower() in description for other_name in field_names)

        if mentions_other_field:
            continue

        field_items.append((field_name, field_schema))


    with ThreadPoolExecutor(max_workers=4) as executor:
        ai_results = list(executor.map(lambda item: (item[0], mine_implicit_constraint(item[0], item[1], ai_model=ai_model)), field_items))


    
    #ai_result = mine_implicit_constraint(field_name, field_schema)
    for field_name, ai_result in ai_results:
        if ai_result is None:
            continue

        #Invalid case
        invalid_obj = generate_valid_object(schema)
        if put_id_sync:
            invalid_obj[put_id_sync["field"]] = put_id_sync["value"]
        invalid_obj[field_name] = ai_result["suggested_invalid_example"]

        test_cases.append({
            "category": constants.AI_IMPLICIT_CONSTRAINT_VIOLATION,
            "field": field_name,
            "expected_status": 422,
            "description": (
                f"AI-detected implicit constraint for field '{field_name}:'"
                f"{ai_result['constraint_description']} "
                f"(heuristic, not formally declared in schema)"
                ),
            "data": invalid_obj,
        })

        #Valid case
        valid_obj = generate_valid_object(schema)
        if put_id_sync:
            valid_obj[put_id_sync["field"]] = put_id_sync["value"]
        valid_obj[field_name] = ai_result["suggested_valid_example"]
        test_cases.append({
            "category": constants.AI_IMPLICIT_CONSTRAINT_VALID,
            "field": field_name,
            "expected_status": 200,
            "description": (
                f"AI-suggested valid example for field '{field_name}:' "
                f"satisfying implicit constraint: {ai_result['constraint_description']} "
                ),
            "data": valid_obj,
        })

    return test_cases


def generate_cross_field_case(schema: dict, ai_model: str | None = None) -> dict | None:
    ai_result = mine_cross_field_constraint(schema, ai_model = ai_model)
    if ai_result is None:
        return None

    obj = generate_valid_object(schema)
    obj[ai_result["field_a"]] = ai_result["invalid_value_a"]
    obj[ai_result["field_b"]] = ai_result["invalid_value_b"]

    return {
        "category": constants.AI_CROSS_FIELD_VIOLATION,
        "field": f"{ai_result['field_a']}+{ai_result['field_b']}",
        "expected_status": 422,
        "description": (
            f"AI-detected cross-field constraint: {ai_result['constraint_description']} "
            f"(heuristic, not formally declared in schema)"
        ),
        "data": obj,

    }

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
            "reason": "All numeric fields already have 'minnimum'/'exclusiveMinimum' decalred or no numeric fields exist in the schema",
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

    has_array_items_type = (schema.get("type")=="array" and schema.get("items", {}).get("type") is not None) or any(p.get("type")=="array" and p.get("items", {}).get("type") is not None for p in properties.values())
    if not has_array_items_type:
        skipped.append({
            "category": constants.INVALID_ARRAY_ITEM_TYPE,
            "reason": "No array field has 'items' with decalred type in the schema"
        })

    has_array_bounds = (schema.get("type") == "array" and (schema.get("minItems") is not None or schema.get("maxItems") is not None)) or any(p.get("type")=="array" and (p.get("minItems") is not None or p.get("maxItems") is not None) for p in properties.values())
    if not has_array_bounds:
        skipped.append({
            "category": constants.ARRAY_BOUNDARY,
            "reason": "No array field has 'minItems' or 'maxItems' in the schema"
        })

    has_unique_items = (schema.get("type") == "array" and schema.get("uniqueItems") is True) or any(p.get("type") == "array" and p.get("uniqueItems") is True for p in properties.values())
    if not has_unique_items:
        skipped.append({
            "category": constants.DUPLICATE_ARRAY_ITEMS,
            "reason": "No array field has 'uniqueItems' in the schema"
        })
    has_array_without_minitems =(schema.get("type") == "array" and schema.get("minItems") is None) or  any(p.get("type") == "array" and p.get("minItems") is None for p in properties.values())
    if not has_array_without_minitems:
        skipped.append({
            "category": constants.EMPTY_ARRAY,
            "reason": "All array fields already have 'minItems' declared, or no array fields exist"
        })

    has_nested_object = any(p.get("type") == "object" and p.get("properties") for p in properties.values())
    if not has_nested_object:
        skipped.append({
            "category": constants.NESTED_TYPE_MISMATCH,
            "reason": "No nested object field with 'properties' in the schema"
        }) 

    has_nested_required = any(p.get("type")=="object" and p.get("properties") and p.get("required") for p in properties.values())
    if not has_nested_required:
        skipped.append({
            "category": constants.NESTED_MISSING_REQUIRED,
            "reason": "No nested object field has its own 'required' properties declared"
        })

    if schema.get("additionalProperties") is not False:
        skipped.append({
            "category": constants.MASS_ASSIGNMENT,
            "reason": "Schema does not declare 'additionalProperties': false"
        })

    return skipped




def get_skipped_query_categories(query_params: list[dict]) -> list[dict]:
    skipped = []
    required_params = [p for p in query_params if p["required"]]

    if not required_params:
        skipped.append({
            "category": constants.MISSING_REQUIRED_QUERY_PARAM,
            "reason": "No required query paramters declared"
        })
        skipped.append({
            "category": constants.INVALID_QUERY_PARAM_VALUE,
            "reason": "No required query paramters declared"
        })
        skipped.append({
            "category": constants.INVALID_QUERY_PARAM_ENUM,
            "reason": "No required query paramters declared"
        })
        return skipped

    has_non_string_type = any((p["schema"].get("items",{}) if p["schema"].get("type") == "array" else p["schema"].get("type")) not in ("string",None) for p in required_params)
    if not has_non_string_type:
        skipped.append({
            "category": constants.INVALID_QUERY_PARAM_VALUE,
            "reason": "All required quiry param are string-type - no missmatch possible"
        })

    has_query_enum = any("enum" in (p["schema"].get("items",{}) if p["schema"].get("type") == "array" else p["schema"]) for p in required_params)
    if not has_query_enum:
        skipped.append({
            "category": constants.INVALID_QUERY_PARAM_ENUM,
            "reason": "No required query param(or its array items) has 'enum' declared"
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