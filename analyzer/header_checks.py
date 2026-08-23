def check_header_present(headers: dict, header_name: str) -> bool:
    return header_name in headers or header_name.lower() in headers

def check_allowed_header_present(response_headers: dict) -> bool:
    return check_header_present(response_headers, "Allow")

def check_accept_post_header_present(response_headers: dict) -> bool:
    return check_header_present(response_headers, "Accept-Post")


