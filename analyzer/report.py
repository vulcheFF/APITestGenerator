SEVERITY_MAP = {
    "type_mismatch": "HIGH",
    "missing_required": "HIGH",
    "boundary_numeric": "HIGH",
    "boundary_string": "MEDIUM",
    "invalid_enum": "MEDIUM",
    "invalid_boolean": "MEDIUM",
    "nonexistent_id": "HIGH",
    "invalid_id_format": "MEDIUM",
    "negative_id": "LOW",
    "valid_id": "HIGH",
    "negative_value": "INFO" #не можем да кажем точно дали е бъг или не - флаг за ръчна проверка. 
}

def determine_severity(category: str) -> str:
    return SEVERITY_MAP.get(category, "MEDIUM")



def analyze_results(results: list[dict])-> dict:
    total = len(results)
    issues=[]

    for r in results:
        expected = r.get("expected_status")
        actual = r["status_code"]

        if expected is not None and actual != expected:
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


        # # при invalid тест има грешка, но получавваме 200 или 201 тоест има някакъв бъг
        # if r["test_type"] == "invalid" and r["status_code"] <400:
        #     issues.append({
        #         "method": r["method"],
        #         "path": r["path"],
        #         "description": r["description"],
        #         "status_code": r["status_code"],
        #         "severity": "HIGH",

        #     })

        # # при валид тест има грешка "? -> има бъг - фейк зелено
        # if r["test_type"] == "valid" and r["status_code"] >= 400:
        #     issues.append({
        #         "method": r["method"],
        #         "path": r["path"],
        #         "description": r["description"],
        #         "status_code": r["status_code"],
        #         "severity": "HIGH",

        #     })
        # if r["test_type"]=="path_param":
        #     issue = check_path_param_issue(r)
        #     if issue:
        #         issues.append(issue)

    return {
        "total_tests": total,
        "issues_found": len(issues),
        "issues": issues,

    }


# def check_path_param_issue(r: dict) -> dict | None:
#     case_id = r["case_id"]
#     status = r["status_code"]

#     if case_id == "valid_id" and status >=400:
#         severity = "HIGH"
#     elif case_id == "nonexistent_id" and status < 400:
#         severity = "HIGH"
#     elif case_id == "invalid_format" and status < 400:
#         severity = "MEDIUM"
#     elif case_id == "negative_id" and status < 400:
#         severity = "LOW"
#     else:
#         return None

#     return {
#         "method": r["method"],
#         "path": r["path"],
#         "description": r["description"],
#         "status_code": status,
#         "severity": severity,
#     }



def print_report(analysis: dict):
    print(f"Total test run:{analysis['total_tests']} ")
    print(f"Issues found:{analysis['issues_found']} ")
    print("-"*39)
    for issue in analysis["issues"]:
        print(f"[{issue['severity']}] {issue['method']} {issue['path']} {issue['category']}")
        print(f"    {issue['description']} -> expected {issue['expected_status']} got {issue['status_code']}")