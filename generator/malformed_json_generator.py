def generate_malformed_json_cases():
    return[
        {
            "description": "Truncated JSON (missing closing bracket)",
            "body": '{"field": "value"' 
        },
        {
            "description": "Trailing comma",
            "body": '{"field": "value",}' 
        },  
        {
            "description": "Single quotes instead of double quotes",
            "body": "{'field': 'value'}" 
        },
        {
            "description": "Unquoted object key",
            "body": '{field: "value"}' 
        }, 
        {
            "description": "Missing comma between fields",
            "body": '{"field": "value" "other": 5}' 
        },
        {
            "description": "Unescaped quote inside string value",
            "body": '{"field": "va"lue"}'
        },
        {
            "description": "Empty body",
            "body": "" 
        },                             
    ]