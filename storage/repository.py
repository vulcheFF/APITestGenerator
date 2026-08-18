import json
from storage.database import get_session
from storage.models import TestRun, TestResult, Issue


def save_run(base_url: str, results: list[dict], analysis: dict) -> int:
    with get_session() as session:
        run = TestRun(
            base_url=base_url,
            total_tests=analysis["total_tests"],
            issues_found=analysis["issues_found"],

        )
        session.add(run)
        session.commit()
        session.refresh(run) 

        for r in results:
            result_row = TestResult(
                run_id=run.id,
                method=r["method"],
                path=r["path"],
                test_type=r["test_type"],
                description=r["description"],
                status_code=r["status_code"],
                data_sent=json.dumps(r.get("data_sent")),
            )
            session.add(result_row)


        for issue in analysis["issues"]:
            issue_row= Issue(
                run_id=run.id,
                method=issue["method"],
                path=issue["path"],                
                description=issue["description"],
                status_code=issue["status_code"],
                severity=issue["severity"],
            )
            session.add(issue_row)

        session.commit()
        return run.id