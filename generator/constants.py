#### List/GET endpoints ####
LIST_ENDPOINT = "list_endpoint"

#### Body (POST/PUT) ####
VALID_DATA = "valid_data"
TYPE_MISMATCH = "type_mismatch"
MISSING_REQUIRED = "missing_required"
NEGATIVE_VALUE = "negative_value"

#### Numeric/string boundaries ####
BOUNDARY_NUMERIC = "boundary_numeric"
BOUNDARY_STRING = "boundary_string"

#### Enum/boolean/pattern ####
INVALID_ENUM = "invalid_enum"
INVALID_BOOLEAN = "invalid_boolean"
INVALID_PATTERN = "invalid_pattern"

#### Array #####
INVALID_ARRAY_ITEM_TYPE = "invalid_array_item_type"
ARRAY_BOUNDARY = "array_boundary"
DUPLICATE_ARRAY_ITEMS = "duplicate_array_items"
EMPTY_ARRAY = "empty_array"

#### Nested object ####
NESTED_TYPE_MISMATCH = "nested_type_mismatch"
INVALID_QUERY_PARAM_VALUE = "invalid_query_param_value"
NESTED_MISSING_REQUIRED = "nested_missing_required"
INVALID_QUERY_PARAM_ENUM = "invalid_query_param_enum"

#### Query params ####
MISSING_REQUIRED_QUERY_PARAM = "missing_required_query_param"

#### Request-level ####
MALFORMED_JSON = "malformed_json"
WRONG_CONTENT_TYPE = "wrong_content_type"
METHOD_NOT_ALLOWED = "method_not_allowed"

#### Response ####
RESPONSE_SCHEMA_MISMATCH = "response_schema_mismatch"

#### Path params ####
VALID_ID = "valid_id"
NONEXISTENT_ID = "nonexistent_id"
INVALID_ID_FORMAT = "invalid_id_format"
NEGATIVE_ID = "negative_id"

####mass_assignment####
MASS_ASSIGNMENT = "mass_assignment"