def _issue_key(issue):
    return (
        issue.get("method"),
        issue.get("template_path") or issue.get("path"),
        issue.get("category"),
        issue.get("field"),
    )
def _sort_key(key):

    return tuple("" if part is None else str(part) for part in key)


def compare_run_issues(issues_a: list[dict], issues_b: list[dict],) -> dict:
    issues_a_by_key = {
        _issue_key(issue): issue for issue in issues_a
    }
    issues_b_by_key = {
        _issue_key(issue): issue for issue in issues_b
    }

    keys_a = set(issues_a_by_key)
    keys_b = set(issues_b_by_key)

    new_keys = keys_b - keys_a
    resolved_keys = keys_a - keys_b
    unchanged_keys = keys_a & keys_b

    return {
        "new": [issues_b_by_key[key] for key in sorted(new_keys, key=_sort_key)],
        "resolved": [issues_a_by_key[key] for key in sorted(resolved_keys, key=_sort_key)],
        "unchanged": [issues_a_by_key[key] for key in sorted(unchanged_keys, key=_sort_key)],
    }