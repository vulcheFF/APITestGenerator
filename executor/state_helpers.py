import random
import re
from generator.spec_parser import find_matching_create_endpoint, get_request_body_schema
from generator.data_generator import generate_valid_object
from executor.test_runner import execute_test


def fill_path_params_with_value(path: str, value: str) -> str:
    return re.sub(r"\{[^}]+\}", value, path)



def _is_id_like_name(field_name: str) -> bool:
    #snake_case
    snake_parts = field_name.lower().split("_")
    if "id" in snake_parts:
        return True
    camel_parts = re.findall(r'[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z][a-z0-9]*|[a-z0-9]+', field_name)
    return any(part.lower() == "id" for part in camel_parts)


def find_id_like_field(schema: dict, path_param_name: str = None) -> str | None:
    properties = schema.get("properties", {})

    if path_param_name and path_param_name in properties:
        return path_param_name

    for field_name, field_schema in properties.items():
        if field_schema.get("type") != "integer":
            continue
        if _is_id_like_name(field_name):
            return field_name

    return None

def create_resource_for_put_test(base_url: str, spec: dict, endpoints: list[dict], put_endpoint: dict,) -> dict | None:
    create_endpoint = find_matching_create_endpoint(endpoints, put_endpoint["path"],)

    if create_endpoint is None:
        return None

    create_schema = get_request_body_schema(spec, create_endpoint)

    if not create_schema:
        return None

    create_data = generate_valid_object(create_schema)
    id_field = find_id_like_field(create_schema)

    if id_field:
        create_data[id_field] = random.randint(10_000_000, 99_999_999)

    create_result = execute_test(base_url, "POST", create_endpoint["path"], create_data)

    status = create_result.get("status_code")

    if status is None or not (200<= status <300):
        return None

    response_body = create_result.get("response_body")

    if(id_field and isinstance(response_body, dict) and id_field in response_body):
        created_id = response_body[id_field]
    elif id_field:
        created_id = create_data.get(id_field)
    else:
        return None

    if created_id is None:
        return None

    test_path = fill_path_params_with_value(put_endpoint["path"], str(created_id))
    resource_path = re.sub(r"/\{[^}]+\}$", "", put_endpoint["path"])
    return {
        "id": created_id,
        "id_field": id_field,
        "path": test_path,
        "resource_path": resource_path,
        "data": create_data,
    }
    
def cleanup_created_resource(base_url: str, endpoints: list[dict], resource_path: str, created_id) -> bool:

    delete_endpoint = next((ep for ep in endpoints if ep["method"] == "DELETE" and re.sub(r"/\{[^}]+\}$", "", ep["path"]) == resource_path), None)

    if delete_endpoint is None:
        return False

    cleanup_path = fill_path_params_with_value(delete_endpoint["path"], str(created_id))

    result = execute_test(base_url, "DELETE", cleanup_path, data = None)

    status = result.get("status_code")

    return status is not None and 200<= status <300