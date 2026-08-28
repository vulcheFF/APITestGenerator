import json
from analyzer.report import is_test_passed
from storage.database import get_session, engine
from storage.models import TestRun, TestResult, Issue
from sqlmodel import Session, select

def save_run(base_url: str, results: list[dict], analysis: dict, *, seed: int| None = None, ai_enabled: bool | None = None, ai_model: str | None = None, duration_ms: int | None = None) -> int:
    with get_session() as session:
        run = TestRun(
            base_url=base_url,
            total_tests=analysis["total_tests"],
            passed_count=analysis["passed_count"],
            issues_found=analysis["issues_found"],
            seed=seed,
            ai_enabled=ai_enabled,
            ai_model=ai_model,
            duration_ms=duration_ms,

        )
        session.add(run)
        session.commit()
        session.refresh(run) 

        for r in results:
            expected = r.get("expected_status")
            
            is_passed = is_test_passed(r)
            result_row = TestResult(
                run_id=run.id,
                method=r["method"],
                path=r["path"],
                test_type=r["test_type"],
                category = r.get("category"),
                field=r.get("field"),
                expected_status= expected,
                passed = is_passed,
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
                category = issue.get("category"),
                field=issue.get("field"),
                expected_status=issue.get("expected_status"),            
                description=issue["description"],
                status_code=issue["status_code"],
                severity=issue["severity"],
            )
            session.add(issue_row)

        session.commit()
        return run.id

def get_run_summary(run_id: int):
    with Session(engine) as session:
        run = session.get(TestRun, run_id)
        all_results = session.exec(
            select(TestResult).where(TestResult.run_id == run_id)
        ).all()
        issues = session.exec(
            select(Issue).where(Issue.run_id == run_id)
        ).all()

        return {
            "run": run,
            "total": len(all_results),
            "passed":[r for r in all_results if r.passed],
            "failed":[r for r in all_results if not r.passed],
            "issues": issues,
        }