import random
import time
from PySide6.QtCore import QObject, Signal, Slot
from executor.pipeline import run_all_tests
from analyzer.report import analyze_results
from storage.repository import save_run
from analyzer.spec_overview import build_spec_overview, analyze_spec_with_ai, format_spec_overview_for_llm
from analyzer.run_analysis import analyze_run_with_ai, build_run_analysis_text
from generator.spec_parser import fetch_openapi_spec
from storage.repository import get_run_summary

class TestWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self,base_url:str, category_filter: list[str], ai_enabled: bool, ai_model: str | None = None):
        super().__init__()
        self.base_url = base_url
        self.category_filter = category_filter
        self.ai_enabled = ai_enabled
        self.ai_model = ai_model

    @Slot()
    def run(self):
        try:
            run_seed = random.SystemRandom().randint(0, 2**32 - 1)
            started_at = time.perf_counter()

            results, skipped = run_all_tests(self.base_url, category_filter=self.category_filter, seed=run_seed)

            duration_ms = round((time.perf_counter() - started_at)*1000)

            analysis = analyze_results(results)

            run_id = save_run(self.base_url, results, analysis, seed = run_seed, ai_enabled=self.ai_enabled, ai_model= self.ai_model, duration_ms=duration_ms, selected_categories=self.category_filter)

            self.finished.emit({
                "run_id": run_id,
                "seed": run_seed,
                "duration_ms": duration_ms,
                "results": results,
                "skipped": skipped,
                "analysis": analysis,
            })

        except Exception as exc:
            self.failed.emit(str(exc))

class SpecAnalysisWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url


    @Slot()
    def run(self):
        try:
            spec = fetch_openapi_spec(self.base_url)

            overview = build_spec_overview(spec)

            overview_text = format_spec_overview_for_llm(overview)

            analysis = analyze_spec_with_ai(overview_text)

            self.finished.emit(analysis)

        except Exception as exc:
            self.failed.emit(str(exc))

class RunAnalysisWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, run_id: int):
        super().__init__()
        self.run_id = run_id

    @Slot()
    def run(self):
        try:
            summary = get_run_summary(self.run_id)
            run = summary["run"]

            if run is None:
                raise ValueError(f"Run #{self.run_id} no longer exists.")

            issues = [
                {
                    "severity": issue.severity,
                    "method": issue.method,
                    "path": issue.path,
                    "template_path": issue.template_path,
                    "category": issue.category,
                    "field": issue.field,
                    "expected_status": issue.expected_status,
                    "status_code": issue.status_code,
                    "description": issue.description,
                }
                for issue in summary["issues"]
            ]

            passed= [
                {
                    "method": result.method,
                    "path": result.path,
                    "template_path": result.template_path,
                    "category": result.category,
                    "field": result.field,
                    "status_code": result.status_code,
                    "description": result.description,
                }
                for result in summary["passed"]
            ]

            run_text = build_run_analysis_text(run, issues, passed)
            analysis = analyze_run_with_ai(run_text)
            self.finished.emit(analysis)

        except Exception as exc:
            self.failed.emit(str(exc))
