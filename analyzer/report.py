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
}

def determine_severity(category: str) -> str:
    return SEVERITY_MAP.get(category, "MEDIUM")

def is_acceptable_error_status(actual_status: int, expected_status: int) -> bool:
    if actual_status == expected_status:
        return True
    if 400 <= actual_status < 500:
        return True

    return False



def analyze_results(results: list[dict])-> dict:
    total = len(results)
    issues=[]
    passed=[]

    for r in results:
        expected = r.get("expected_status")
        actual = r["status_code"]


        if r.get("error"):
            issues.append({
                "method": r["method"],
                "path": r["path"],
                "category": r.get("category"),
                "field": r.get("field"),
                "description": f"Request failed: {r['error']}",
                "expected_status": expected,
                "status_code": None,
                "severity": "HIGH",

            })
            continue
        
        if expected is None:
            passed.append({
                "method": r["method"],
                "path": r["path"],
                "category": r.get("category"),
                "field": r.get("field"),
                "description": r["description"],                
                "status_code": actual,
            })
            continue

        is_ok = (
            is_acceptable_error_status(actual,expected) if expected >=400 else actual == expected
        )

        if not is_ok:    
            issues.append({
                "method": r["method"],
                "path": r["path"],
                "category": r.get("category"),
                "field": r.get("field"),
                "description": r["description"],
                "expected_status": expected,
                "status_code": actual,
                "severity": determine_severity(r.get("category")),

            })
        else:
            conformance_errors  = r.get("schema_conformance_errors")
            if conformance_errors:
                issues.append({
                    "method": r["method"],
                    "path": r["path"],
                    "category": constants.RESPONSE_SCHEMA_MISMATCH,
                    "field": r.get("field"),
                    "description": f"{r['description']} — response body несъответства на декларираната схема: {'; '.join(conformance_errors)}",
                    "expected_status": expected,
                    "status_code": actual,
                    "severity": determine_severity(constants.RESPONSE_SCHEMA_MISMATCH),
                })
            else:
                passed.append({
                    "method": r["method"],
                    "path": r["path"],
                    "category": r.get("category"),
                    "field": r.get("field"),
                    "description": r["description"],                
                    "status_code": actual,
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
        for issue in analysis['issues']:
            print(f"[{issue['severity']}] {issue['method']} {issue['path']} {issue['category']}")
            print(f"    {issue['description']} -> expected {issue['expected_status']} got {issue['status_code']}")

    if show_passed:
        if passed_count:
            print("\nPASSED:")
            for p in analysis['passed']:
                print(f"[PASS] [{p['method']}] {p['path']} {p['category']} - {p['description']}")
          

    