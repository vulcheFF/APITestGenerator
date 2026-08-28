import sys
import random
import time
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QAbstractItemView
from PySide6.QtCore import QObject, QThread, Signal, Slot
from analyzer.report import analyze_results
from executor.pipeline import run_all_tests
from generator import constants
from storage.database import init_db
from storage.repository import save_run

class TestWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self,base_url:str):
        super().__init__()
        self.base_url = base_url

    @Slot()
    def run(self):
        try:
            run_seed = random.SystemRandom().randint(0, 2**32 - 1)
            started_at = time.perf_counter()

            results, skipped = run_all_tests(self.base_url, category_filter=constants.DETERMINISTIC_CATEGORIES, seed=run_seed)

            duration_ms = round((time.perf_counter() - started_at)*1000)

            analysis = analyze_results(results)

            run_id = save_run(self.base_url, results, analysis, seed = run_seed, ai_enabled=False, ai_model=None, duration_ms=duration_ms,)

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

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("API Test Generator")
        self.resize(900,600)
         
        title = QLabel("API Test Generator")

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("API base URL")
        self.base_url_input.setText("http://127.0.0.1:8000")

        self.run_button = QPushButton("Run deterministic tests")
        self.run_button.clicked.connect(self.handle_run_clicked)
        
        self.status_label = QLabel("Ready!")
        self.summary_label = QLabel("No run yet!")
        

        self.thread = None
        self.worker = None

        self.issues_table = QTableWidget()
        self.issues_table.setColumnCount(7)
        self.issues_table.setHorizontalHeaderLabels([
            "Severity",
            "Method",
            "Path",
            "Category",
            "Field",
            "Expected",
            "Actual",
        ])

        self.issues_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.issues_table.setRowCount(0)


        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(self.base_url_input)
        layout.addWidget(self.run_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.issues_table)
        layout.addStretch()

        central_widget = QWidget()
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)

    def handle_run_clicked(self):
        self.issues_table.setRowCount(0)
        base_url = self.base_url_input.text().strip().rstrip("/")

        if not base_url:
            self.status_label.setText("Please enter an API base URL!")
            return

        self.run_button.setEnabled(False)
        self.status_label.setText("Running deterministic tests...")
        self.summary_label.setText("")

        self.thread = QThread()
        self.worker = TestWorker(base_url)

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.finished.connect(self.handle_run_finished)
        self.worker.failed.connect(self.handle_run_failed)

        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)

        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)

        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.cleanup_thread)

        self.thread.start()

    def handle_run_finished(self, run_data):
        analysis = run_data["analysis"]

        self.populate_issues_table(analysis["issues"])

        self.status_label.setText(f"Run #{run_data['run_id']} completed")

        self.summary_label.setText(
            f"Total: {analysis['total_tests']} | "
            f"Passed: {analysis['passed_count']} | "
            f"Issues: {analysis['issues_found']} | "
            f"Duration: {run_data['duration_ms']} ms"
        )

        self.run_button.setEnabled(True)


    def handle_run_failed(self, error_message):
        self.status_label.setText(f"Test run failed: {error_message}")

        self.summary_label.setText("")
        self.run_button.setEnabled(True)

    def cleanup_thread(self):
        self.thread = None
        self.worker = None

    def populate_issues_table(self, issues):
        self.issues_table.setRowCount(len(issues))

        for row, issue in enumerate(issues):
            values = [
                issue.get("severity"),
                issue.get("method"),
                issue.get("path"),
                issue.get("categoty"),
                issue.get("field"),
                issue.get("expected_status"),
                issue.get("status_code"),
            ]
            for column, value in enumerate(values):
                text = "" if value is None else str(value)
                self.issues_table.setItem(row, column, QTableWidgetItem(text),)

        self.issues_table.resizeColumnsToContents()

def main():
    app = QApplication(sys.argv)

    init_db()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()