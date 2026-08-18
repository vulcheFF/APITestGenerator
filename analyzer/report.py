def analyze_results(results: list[dict])-> dict:
    total = len(results)
    issues=[]

    for r in results:
        # при invalid тест има грешка, но получавваме 200 или 201 тоест има някакъв бъг
        if r["test_type"] == "invalid" and r["status_code"] <400:
            issues.append({
                "method": r["method"],
                "path": r["path"],
                "description": r["description"],
                "status_code": r["status_code"],
                "severity": "HIGH",

            })

        # при валид тест има грешка "? -> има бъг - фейк зелено
        if r["test_type"] == "valid" and r["status_code"] >= 400:
            issues.append({
                "method": r["method"],
                "path": r["path"],
                "description": r["description"],
                "status_code": r["status_code"],
                "severity": "HIGH",

            })
        if r["test_type"]=="path_param":
            issue = check_path_param_issue(r)
            if issue:
                issues.append(issue)

    return {
        "total_tests": total,
        "issues_found": len(issues),
        "issues": issues,

    }


def check_path_param_issue(r: dict) -> dict | None:
    case_id = r["case_id"]
    status = r["status_code"]

    if case_id == "valid_id" and status >=400:
        severity = "HIGH"
    elif case_id == "nonexistent_id" and status < 400:
        severity = "HIGH"
    elif case_id == "invalid_format" and status < 400:
        severity = "MEDIUM"
    elif case_id == "negative_id" and status < 400:
        severity = "LOW"
    else:
        return None

    return {
        "method": r["method"],
        "path": r["path"],
        "description": r["description"],
        "status_code": status,
        "severity": severity,
    }



def print_report(analysis: dict):
    print(f"Total test run:{analysis['total_tests']} ")
    print(f"Issues found:{analysis['issues_found']} ")
    print("-"*39)
    for issue in analysis["issues"]:
        print(f"[{issue['severity']}] {issue['method']} {issue['path']}")
        print(f"    {issue['description']} -> status {issue['status_code']}")