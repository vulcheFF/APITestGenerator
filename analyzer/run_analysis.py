from ai.ollama_client import query_ollama

def build_run_analysis_text(run, issues: list[dict], passed: list[dict]) -> str:
    run_type = "AI" if run.ai_enabled else "Deterministic"

    lines = [
        f"Run ID: {run.id}",
        f"Run type: {run_type}",
        f"Base URL: {run.base_url}",
        f"Total tests: {run.total_tests}",
        f"Passed: {run.passed_count}",
        f"Issues: {run.issues_found}",
        f"Duration: {run.duration_ms if run.duration_ms is not None else 'N/A'} ms",
        "",
        f"Issues:",
    ]

    if not issues:
        lines.append("- None")
    else:
        for issue in issues:
            path = issue.get("template_path") or issue.get("path")

            lines.append(
                f"- [{issue.get('severity')}] "
                f"{issue.get('method')} {path} | "
                f"category={issue.get('category')} | "
                f"field={issue.get('field') or 'N/A'} | "
                f"expected={issue.get('expected_status')} | "
                f"actual={issue.get('status_code')} | "
                f"description={issue.get('description', '')}"
            )

    lines.append("")
    lines.append("Passed results:")

    if not passed:
        lines.append("- None")
    else:
        for result in passed:
            path = result.get("template_path") or result.get("path")

            lines.append(
                f"- {result.get('method')} {path} | "
                f"category={result.get('category')} | "
                f"field={result.get('field') or 'N/A'} | "
                f"actual={result.get('status_code')} | "
                f"description={result.get('description', '')}"
                
            )

    return "\n".join(lines)

def analyze_run_with_ai(run_text: str) -> str:
    prompt = f"""
    You are analyzing the results of an automated REST API test run.

    Based only on the run summary below, provide a concise technical analysis.

    Important rules:
    - Treat deterministic schema-based findings as stronger evidence.
    - Treat heuristic findings carefully, especially findings whose descriptions
    explicitly mention possible false positives or missing formal constraints.
    - Do not claim that a heuristic finding is a confirmed API defect unless the
    provided data supports that conclusion.
    - Do not invent endpoints, fields, constraints, responses, or behavior.
    - If information is missing, say that it is not available.

    Include:
    - Overall run assessment
    - Most important issues
    - Patterns across endpoints or categories
    - Which findings may require manual verification
    - Useful next investigation steps for a tester
    - A short summary of what passed successfully

    Test run summary:

    {run_text}
    """
    response = query_ollama(prompt, timeout=60)

    if response is None:
        return("AI analysis could not be completed because Ollama is unavailable")

    return response
