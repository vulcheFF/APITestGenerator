import random
import time

from PySide6.QtCore import QObject, Signal, Slot

from executor.pipeline import run_all_tests
from analyzer.report import analyze_results
from storage.repository import save_run

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