from generator import constants

SEVERITY_MAP = {
    constants.LIST_ENDPOINT: "HIGH",
    constants.TYPE_MISMATCH: "HIGH",
    constants.MISSING_REQUIRED: "HIGH",
    constants.BOUNDARY_NUMERIC: "HIGH",
    constants.BOUNDARY_STRING: "MEDIUM",
    constants.INVALID_ENUM: "MEDIUM",
    constants.INVALID_BOOLEAN: "MEDIUM",
    constants.INVALID_PATTERN: "MEDIUM",
    constants.NONEXISTENT_ID: "HIGH",
    constants.INVALID_ID_FORMAT: "MEDIUM",
    constants.NEGATIVE_ID: "LOW",
    constants.VALID_ID: "HIGH",
    constants.NEGATIVE_VALUE: "INFO",  # fake pass probability - manual check
    constants.RESPONSE_SCHEMA_MISMATCH: "MEDIUM",
    constants.MISSING_REQUIRED_QUERY_PARAM: "HIGH",
    constants.VALID_DATA: "HIGH",
    constants.MALFORMED_JSON: "HIGH",
    constants.WRONG_CONTENT_TYPE: "MEDIUM",
    constants.METHOD_NOT_ALLOWED: "MEDIUM",
    constants.INVALID_ARRAY_ITEM_TYPE: "HIGH",
    constants.ARRAY_BOUNDARY: "HIGH",
    constants.DUPLICATE_ARRAY_ITEMS: "HIGH",
    constants.NESTED_TYPE_MISMATCH: "HIGH",
    constants.INVALID_QUERY_PARAM_VALUE: "MEDIUM",
    constants.NESTED_MISSING_REQUIRED: "HIGH",
    constants.INVALID_QUERY_PARAM_ENUM: "MEDIUM",
    constants.EMPTY_ARRAY: "INFO",
    constants.DELETE_IDEMPOTENCY: "HIGH",
    constants.PUT_IDEMPOTENCY: "HIGH",
    constants.AI_IMPLICIT_CONSTRAINT_VIOLATION: "MEDIUM",
    constants.AI_IMPLICIT_CONSTRAINT_VALID: "MEDIUM",
    constants.AI_CROSS_FIELD_VIOLATION: "MEDIUM",

}


#for visibility might remove it later
STATUS_COLORS = {
    "HIGH": "\033[91m",
    "MEDIUM": "\033[93m",
    "LOW": "\033[94m",
    "INFO": "\033[90m",
    "PASS": "\033[92m",
}
RESET_COLOR = "\033[0m"


def colorize_status(severity: int) -> str:
    color = STATUS_COLORS.get(severity, "")
    return f"{color}{severity}{RESET_COLOR}"

def determine_severity(category: str) -> str:
    return SEVERITY_MAP.get(category, "MEDIUM")

def is_acceptable_error_status(actual_status: int, expected_status: int) -> bool:
    if actual_status == expected_status:
        return True
    if 400 <= actual_status < 500 and 400 <= expected_status <500:
        return True

    return False

def _status_matches_expectation(actual_status, expected_status, acceptable_statuses = None) -> bool:
    if expected_status is None:
        return True
    if actual_status is None:
        return False

    if acceptable_statuses and expected_status<400 and actual_status in acceptable_statuses:
        return True
    
    return (is_acceptable_error_status(actual_status, expected_status) if expected_status >= 400 else actual_status==expected_status)



def is_test_passed(r: dict) -> bool:
    if r.get("error"):
        return False
    
    if r.get("schema_conformance_errors"):
        return False
    
    expected = r.get("expected_status")
    if expected is None:
        return True
    
    if not _status_matches_expectation(r.get("status_code"), expected, r.get("acceptable_statuses")):
        return False
    
    return True

def analyze_results(results: list[dict])-> dict:
    total = len(results)
    issues=[]
    passed=[]

    for r in results:
        expected = r.get("expected_status")
        actual = r["status_code"]


        if is_test_passed(r):
            passed.append({
                "method": r["method"],
                "path": r["path"],
                "template_path": r.get("template_path"),
                "category": r.get("category"),
                "field": r.get("field"),
                "description": r["description"],                
                "status_code": actual,
            })
            continue


        if r.get("error"):
            issues.append({
                "method": r["method"],
                "path": r["path"],
                "template_path": r.get("template_path"),
                "category": r.get("category"),
                "field": r.get("field"),
                "description": f"Request failed: {r['error']}",
                "expected_status": expected,
                "status_code": None,
                "severity": "HIGH",

            })
        elif not _status_matches_expectation(actual,expected,r.get("acceptable_statuses")):
            issues.append({
                "method": r["method"],
                "path": r["path"],
                "template_path": r.get("template_path"),
                "category": r.get("category"),
                "field": r.get("field"),
                "description": r["description"],
                "expected_status": expected,
                "status_code": actual,
                "severity": determine_severity(r.get("category")),

            })
        else:
            conformance_errors = r.get("schema_conformance_errors")  
            issues.append({
                "method": r["method"],
                "path": r["path"],
                "template_path": r.get("template_path"),
                "category": constants.RESPONSE_SCHEMA_MISMATCH,
                "field": r.get("field"),
                "description": 
                    f"{r['description']} - response body does not comply with "
                    f"the declared schema: {'; '.join(conformance_errors)}",
                "expected_status": expected,
                "status_code": actual,
                "severity": determine_severity(constants.RESPONSE_SCHEMA_MISMATCH),

            })
        
    return {
        "total_tests": total,
        "issues_found": len(issues),
        "passed_count": len(passed),
        "issues": issues,
        "passed": passed,

    }


def print_report(analysis: dict, show_passed: bool = True):
    total = analysis['total_tests']
    issues_count = analysis['issues_found']
    passed_count = analysis['passed_count']

    print(f"Total test run:{total} ")
    print(f"Passed count:{passed_count} ")
    print(f"Issues found:{issues_count} ")
    print("-"*39)

    if issues_count:
        print("\nISSUES:")
        issues_by_category = {}

        for issue in analysis['issues']:
            issues_by_category.setdefault(issue["category"], []).append(issue)

        for category, items in issues_by_category.items():
            print(f"\n === {category} ({len(items)}) ===")
            for issue in items:

                print(f"[{colorize_status(issue['severity'])}] {issue['method']} {issue['path']}") # {issue['category']}
                print(f"    {issue['description']} -> expected {issue['expected_status']} got {issue['status_code']}")

    if show_passed:
        if passed_count:
            print("\nPASSED:")
            passed_by_category = {}
            for p in analysis['passed']:
                passed_by_category.setdefault(p["category"], []).append(p)

            for category, items in passed_by_category.items():
                print(f"\n ==={category} ({len(items)}) ===")
                for p in items:
                    print(f"[{colorize_status('PASS')}] [{p['method']}] {p['path']} - {p['description']}") # {p['category']}
          

    