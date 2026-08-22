

def check_allowed_header_present(response_headers: dict) -> bool:
    return "Allow" in response_headers or "allow" in response_headers

def check_accept_post_header_present(response_headers: dict) -> bool:
    return "Accept-Post" in response_headers or "accept-post" in response_headers