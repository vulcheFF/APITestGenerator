import json
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QAbstractItemView, QTextEdit, QTabWidget, QDialog, QFileDialog
from PySide6.QtCore import QThread
from generator import constants
from storage.database import init_db
from storage.repository import get_recent_runs, get_run_summary
from ai.ollama_client import MODEL as AI_MODEL
from ui.workers import TestWorker
from ui.dialogs import CategorySelectionDialog
from analyzer.run_comparison import compare_run_issues


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("API Test Generator")
        self.resize(900,600)
         #title
        title = QLabel("API Test Generator")

        #url
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("API base URL")
        self.base_url_input.setText("http://127.0.0.1:8000")


        self.selected_deterministic_categories = list(constants.DETERMINISTIC_CATEGORIES)
        self.selected_ai_categories = list(constants.AI_CATEGORIES)

        #buttons
        self.run_button = QPushButton("Run deterministic tests")
        self.run_button.clicked.connect(self.handle_run_clicked)
        self.ai_run_button = QPushButton("Run AI tests")
        self.ai_run_button.clicked.connect(self.handle_ai_run_clicked)

        self.selected_deterministic_button = QPushButton("Select deterministic test categories...")
        self.selected_deterministic_button.clicked.connect(self.handle_select_deterministic_tests)

        self.selected_ai_button = QPushButton("Select AI test categories...")
        self.selected_ai_button.clicked.connect(self.handle_select_ai_tests)

        #label
        self.status_label = QLabel("Ready!")
        self.summary_label = QLabel("No run yet!")
        self.run_type_label = QLabel("")
        self.deterministic_selection_label = QLabel(f"{len(self.selected_deterministic_categories)} categories selected")
        self.ai_selection_label = QLabel(f"{len(self.selected_ai_categories)} categories selected")

        #thread
        self.thread = None
        self.worker = None

        #run id
        self.run_a_id = None
        self.run_b_id = None

        self.current_comparison = {
            "new": [],
            "resolved": [],
            "unchanged": [],
        }

        #issue table
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
        self.issues_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.issues_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.issues_table.setAlternatingRowColors(True)
        self.issues_table.setRowCount(0)

        #issue details
        self.issues_details = QTextEdit()
        self.issues_details.setReadOnly(True)
        self.issues_details.setPlaceholderText("Select an issue to view details")
        self.issues_details.setMaximumHeight(140)
        self.issues_table.cellClicked.connect(self.handle_issue_selected)

        #issue tab
        issues_widget = QWidget()
        issues_layout = QVBoxLayout()

        issues_layout.addWidget(self.issues_table)
        issues_layout.addWidget(self.issues_details)

        issues_widget.setLayout(issues_layout)

        #passed table
        self.passed_table = QTableWidget()
        self.passed_table.setColumnCount(5)
        self.passed_table.setHorizontalHeaderLabels([
            "Method",
            "Path",
            "Category",
            "Field",
            "Status",
        ])

        self.passed_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.passed_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.passed_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.passed_table.setAlternatingRowColors(True)
        self.passed_table.setRowCount(0)

        #skipped table
        self.skipped_table = QTableWidget()
        self.skipped_table.setColumnCount(4)
        self.skipped_table.setHorizontalHeaderLabels([
            "Method",
            "Path",
            "Category",
            "Reason"
        ])
        self.skipped_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.skipped_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.skipped_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.skipped_table.setAlternatingRowColors(True)
        self.skipped_table.setRowCount(0)

        #tabs
        self.result_tabs=QTabWidget()
        self.result_tabs.addTab(
            issues_widget,
            "Issues"
        )
        self.result_tabs.addTab(
            self.passed_table,
            "Passed"
        )
        self.result_tabs.addTab(
            self.skipped_table,
            "Skipped"
        )

        #testing tab
        testing_widget = QWidget()
        testing_layout = QVBoxLayout()

        testing_layout.addWidget(self.base_url_input)
        testing_layout.addWidget(self.selected_deterministic_button)
        testing_layout.addWidget(self.deterministic_selection_label)
        testing_layout.addWidget(self.run_button)
        testing_layout.addWidget(self.selected_ai_button)
        testing_layout.addWidget(self.ai_selection_label)
        testing_layout.addWidget(self.ai_run_button)
        testing_layout.addWidget(self.status_label)
        testing_layout.addWidget(self.summary_label)
        testing_layout.addWidget(self.run_type_label)
        testing_layout.addWidget(self.result_tabs)
        testing_widget.setLayout(testing_layout)



        #history table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "Run ID",
            "Timestamp",
            "Type",
            "Base URL",
            "Total",
            "Passed",
            "Issues",
            "Duration[ms]"
        ])

        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.cellClicked.connect(self.handle_history_run_selected)
        self.history_table.cellDoubleClicked.connect(self.handle_history_run_opened)
        self.history_table.setRowCount(0)

        #history tab
        history_widget = QWidget()
        history_layout = QVBoxLayout()

        self.history_summary_label = QLabel("Select a run to view details")
        font = self.history_summary_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 1)
        self.history_summary_label.setFont(font)
        self.history_summary_label.setStyleSheet("padding: 6px;")

        self.run_a_label = QLabel("Run A: Not selected")
        self.run_b_label = QLabel("Run B: Not selected")

        self.set_run_a_button = QPushButton("Set as Run A")
        self.set_run_b_button = QPushButton("Set as Run B")
        self.compare_runs_button = QPushButton("Compare runs")

        #export button
        self.export_json_button = QPushButton("Export selected run as JSON")


        self.set_run_a_button.clicked.connect(self.handle_set_run_a)
        self.set_run_b_button.clicked.connect(self.handle_set_run_b)
        self.compare_runs_button.clicked.connect(self.handle_compare_runs)
        self.export_json_button.clicked.connect(self.handle_export_json)

        history_layout.addWidget(self.history_summary_label)

        history_layout.addWidget(self.run_a_label)
        history_layout.addWidget(self.run_b_label)
        history_layout.addWidget(self.set_run_a_button)
        history_layout.addWidget(self.set_run_b_button)
        history_layout.addWidget(self.compare_runs_button)
        history_layout.addWidget(self.export_json_button)

        history_layout.addWidget(self.history_table)
        

        history_widget.setLayout(history_layout)

        #comparison tables
        self.compare_new_table=QTableWidget()
        self.compare_resolved_table=QTableWidget()
        self.compare_unchanged_table=QTableWidget()

        comparison_tables = [
            self.compare_new_table,
            self.compare_resolved_table,
            self.compare_unchanged_table,
        ]

        for table in comparison_tables:
            table.setColumnCount(7)
            table.setHorizontalHeaderLabels([
                "Severity",
                "Method",
                "Path",
                "Category",
                "Field",
                "Expected",
                "Actual",
            ])

            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            table.setAlternatingRowColors(True)

        self.compare_new_table.cellClicked.connect(self.handle_comparison_issue_selected)
        self.compare_resolved_table.cellClicked.connect(self.handle_comparison_issue_selected)
        self.compare_unchanged_table.cellClicked.connect(self.handle_comparison_issue_selected)
        #compare tabs
        compare_widget = QWidget()
        compare_layout = QVBoxLayout()
        self.compare_header_label = QLabel("Select two runs from History and compare them.")
        header_font = self.compare_header_label.font()
        header_font.setBold(True)
        header_font.setPointSize(header_font.pointSize() + 1)
        self.compare_header_label.setFont(header_font)

        self.compare_tabs = QTabWidget()
        self.compare_tabs.addTab(self.compare_new_table, "New issues")
        self.compare_tabs.addTab(self.compare_resolved_table, "Resolved issues")
        self.compare_tabs.addTab(self.compare_unchanged_table, "Unchanged issues")

        self.compare_details = QTextEdit()
        self.compare_details.setReadOnly(True)
        self.compare_details.setPlaceholderText("Select a comparison issue to view details.")
        self.compare_details.setMaximumHeight(160)
    
        compare_layout.addWidget(self.compare_header_label)
        compare_layout.addWidget(self.compare_tabs)
        compare_layout.addWidget(self.compare_details)
        compare_widget.setLayout(compare_layout)
        #main tabs
        self.main_tabs = QTabWidget()
        self.main_tabs.addTab(testing_widget, "Testing")
        self.main_tabs.addTab(history_widget, "History")
        self.main_tabs.addTab(compare_widget, "Compare")
        
        #main layout
        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(self.main_tabs)
        #central
        central_widget = QWidget()
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)
        self.populate_history_table()


    def start_test_run(self, category_filter, ai_enabled, ai_model = None):

        base_url = self.base_url_input.text().strip().rstrip("/")
        

        if not base_url:
            self.status_label.setText("Please enter an API base URL!")
            return

        self.run_button.setEnabled(False)
        self.ai_run_button.setEnabled(False)
        self.selected_deterministic_button.setEnabled(False)
        self.selected_ai_button.setEnabled(False)

        self.current_run_is_ai = ai_enabled

        if ai_enabled:
            self.run_type_label.setText(
                "AI-assisted tests - heuristic findings, "
                "not formally declared schema constraints."
                )
            self.result_tabs.setTabText(0, "AI Issues")
            self.result_tabs.setTabText(1, "AI Passed")
        else:
            self.run_type_label.setText("Deterministic schema-driven tests.")
            self.result_tabs.setTabText(0, "Issues")
            self.result_tabs.setTabText(1, "Passed")


        #deleting info 
        self.current_issues = []
        self.issues_table.setRowCount(0)
        self.passed_table.setRowCount(0)
        self.skipped_table.setRowCount(0)
        self.summary_label.setText("")
        self.issues_details.setText("")


        #start

        self.status_label.setText("Running tests...")
        self.summary_label.setText("")

        self.thread = QThread()
        self.worker = TestWorker(base_url, category_filter=category_filter, ai_enabled=ai_enabled,ai_model=ai_model)

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



    def handle_run_clicked(self):
        if not self.selected_deterministic_categories:
            self.status_label.setText("Please select at least one deterministic test category.")
            return
        
        self.start_test_run(category_filter=self.selected_deterministic_categories, ai_enabled=False, ai_model=None)


    def handle_ai_run_clicked(self):
        if not self.selected_ai_categories:
            self.status_label.setText("Please select at least one AI test category.")
            return
        self.start_test_run(category_filter=self.selected_ai_categories, ai_enabled=True, ai_model=AI_MODEL)


    def handle_run_finished(self, run_data):
        analysis = run_data["analysis"]

        self.populate_issues_table(analysis["issues"])
        self.populate_passed_table(analysis["passed"])
        self.populate_skipped_table(run_data["skipped"])

        self.status_label.setText(f"Run #{run_data['run_id']} completed")
        self.summary_label.setText(
            f"Total: {analysis['total_tests']} | "
            f"Passed: {analysis['passed_count']} | "
            f"Issues: {analysis['issues_found']} | "
            f"Duration: {run_data['duration_ms']} ms"
        )

        self.populate_history_table()

        self.run_button.setEnabled(True)
        self.ai_run_button.setEnabled(True)
        self.selected_deterministic_button.setEnabled(True)
        self.selected_ai_button.setEnabled(True)


    def handle_run_failed(self, error_message):
        self.status_label.setText(f"Test run failed: {error_message}")

        self.summary_label.setText("")
        self.run_button.setEnabled(True)
        self.ai_run_button.setEnabled(True)
        self.selected_deterministic_button.setEnabled(True)
        self.selected_ai_button.setEnabled(True)
        

    def cleanup_thread(self):
        self.thread = None
        self.worker = None

    def populate_issues_table(self, issues):
        self.current_issues = issues
        self.issues_details.clear()
        self.issues_table.setRowCount(len(issues))

        for row, issue in enumerate(issues):
            values = [
                issue.get("severity"),
                issue.get("method"),
                issue.get("path"),
                issue.get("category"),
                issue.get("field"),
                issue.get("expected_status"),
                issue.get("status_code"),
            ]
            for column, value in enumerate(values):
                text = "" if value is None else str(value)
                self.issues_table.setItem(row, column, QTableWidgetItem(text),)

        self.issues_table.resizeColumnsToContents()

    def handle_issue_selected(self, row, column):
        if not hasattr(self, "current_issues"):
            return
        
        if row<0 or row >= len(self.current_issues):
            return

        issue = self.current_issues[row]

        details = (
            f"Severity: {issue.get('severity')}\n"
            f"Method: {issue.get('method')}\n"
            f"Path: {issue.get('path')}\n"
            f"Category: {issue.get('category')}\n"
            f"Field: {issue.get('field') or 'N/A'}\n"
            f"Expected status: {issue.get('expected_status')}\n"
            f"Actual code: {issue.get('status_code')}\n"
            f"Description: {issue.get('description', '')}"
        )

        self.issues_details.setPlainText(details)

    def populate_passed_table(self, passed):
        self.passed_table.setRowCount(len(passed))

        for row, result in enumerate(passed):
            values = [
                result.get("method"),
                result.get("path"),
                result.get("category"),
                result.get("field"),
                result.get("status_code"),
            ]

            for column, value in enumerate(values):
                text = "" if value is None else str(value)

                self.passed_table.setItem(row, column, QTableWidgetItem(text))

        self.passed_table.resizeColumnsToContents()

    def populate_skipped_table(self, skipped):
        self.skipped_table.setRowCount(len(skipped))

        for row, item in enumerate(skipped):
            values = [
                item.get("method"),
                item.get("path"),
                item.get("category"),
                item.get("reason"),
            ]

            for column, value in enumerate(values):
                text = "" if value is None else str(value)

                self.skipped_table.setItem(row, column, QTableWidgetItem(text))

        self.skipped_table.resizeColumnsToContents()

    def handle_select_deterministic_tests(self):
        dialog = CategorySelectionDialog(categories=constants.DETERMINISTIC_CATEGORIES, selected_categories=self.selected_deterministic_categories, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_deterministic_categories = (dialog.get_selected_categories())

            self.deterministic_selection_label.setText(f"{len(self.selected_deterministic_categories)} categories selected")

    def handle_select_ai_tests(self):
        dialog = CategorySelectionDialog(categories=constants.AI_CATEGORIES, selected_categories=self.selected_ai_categories, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_ai_categories = (dialog.get_selected_categories())

            self.ai_selection_label.setText(f"{len(self.selected_ai_categories)} categories selected")

    def populate_history_table(self):
        runs = get_recent_runs(limit=20)

        self.history_table.setRowCount(len(runs))

        for row, run in enumerate(runs):
            run_type = "AI" if run.ai_enabled else "Deterministic"

            values = [
                run.id,
                run.run_timestamp,
                run_type,
                run.base_url,
                run.total_tests,
                run.passed_count,
                run.issues_found,
                run.duration_ms,
            ]

            for column, value in enumerate(values):
                text = "" if value is None else str(value)

                self.history_table.setItem(row,column, QTableWidgetItem(text))

        self.history_table.resizeColumnsToContents()

    def handle_history_run_opened(self, row, column):
        run_id = self.get_selected_history_run_id()

        if run_id is None:
            return


        run_summary = get_run_summary(run_id)
        run = run_summary["run"]

        if run is None:
            return


        duration = (f"{run.duration_ms} ms" if run.duration_ms is not None else "N/A")

        historical_issues = [self.history_issue_to_dict(issue) for issue in run_summary["issues"]]
        historical_passed = [self.history_result_to_dict(result) for result in run_summary["passed"]]

        self.populate_issues_table(historical_issues)
        self.populate_passed_table(historical_passed)

        self.populate_skipped_table([])

        self.status_label.setText(f"Viewing historical run #{run.id}")

        self.summary_label.setText(
            f"Total: {run.total_tests} |"
            f"Passed: {run.passed_count} |"
            f"Issues: {run.issues_found} |"
            f"Duration: {duration}"
        )

        if run.ai_enabled:
            self.run_type_label.setText(f" Historical AI-Assited run #{run.id} - heuristic findings")
            self.result_tabs.setTabText(0, "AI Issues")
            self.result_tabs.setTabText(1, "AI Passed")
        else:
            self.run_type_label.setText(f" Historical deterministic run #{run.id}")
            self.result_tabs.setTabText(0, "Issues")
            self.result_tabs.setTabText(1, "Passed")

        self.main_tabs.setCurrentIndex(0)

    def handle_history_run_selected(self, row, column):
        run_id = self.get_selected_history_run_id()

        if run_id is None:
            return


        run_summary = get_run_summary(run_id)
        run = run_summary["run"]

        if run is None:
            return

        run_type = "AI" if run.ai_enabled else "Deterministic"

        duration = (f"{run.duration_ms} ms" if run.duration_ms is not None else "N/A")

        self.history_summary_label.setText(
            f"Run #{run.id} | "
            f"{run_type} | "
            f"Total: {run.total_tests} | "
            f"Passed: {run.passed_count} | "
            f"Issues: {run.issues_found} | "
            f"Duration: {duration}"
        )


    def history_issue_to_dict(self, issue):
        return{
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
    def history_result_to_dict(self, result):
        return {
            "method": result.method,
            "path": result.path,
            "template_path": result.template_path,
            "category": result.category,
            "field": result.field,
            "status_code": result.status_code,
            "description": result.description,
        }

    def handle_export_json(self):
        run_id = self.get_selected_history_run_id()
        if run_id is None:
            self.history_summary_label.setText("Select a history run before exporting.")
            return

        run_summary = get_run_summary(run_id)
        run = run_summary["run"]

        if run is None:
            self.history_summary_label.setText("Selected run no longer exists.")
            return

        issues = [self.history_issue_to_dict(issue) for issue in run_summary["issues"]]
        passed = [self.history_result_to_dict(result) for result in run_summary["passed"]]

        selected_categories = None

        if run.selected_categories is not None:
            try:
                selected_categories = json.loads(run.selected_categories)
            except (json.JSONDecodeError, TypeError):
                selected_categories = None

        export_data = {
            "run": {
                "id": run.id,
                "timestamp": str(run.run_timestamp),
                "base_url": run.base_url,
                "type": "AI" if run.ai_enabled else "Deterministic",
                "total_tests": run.total_tests,
                "passed_count": run.passed_count,
                "issues_found": run.issues_found,
                "seed": run.seed,
                "ai_enabled": run.ai_enabled,
                "ai_model": run.ai_model,
                "duration_ms": run.duration_ms,
                "selected_categories": selected_categories,

            },
            "issues": issues,
            "passed": passed,
        }

        file_path, _ = QFileDialog.getSaveFileName(self, "Export run as JSON", f"run_{run.id}.json", "JSON FIles(*.json)",)
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(export_data, file, indent=2, ensure_ascii=False)
        except OSError as exc:
            self.history_summary_label.setText(f"Faield to export run #{run.id}: {exc}")
            return

        self.history_summary_label.setText(f"Run #{run.id} exported successfully as JSON.")



    def get_selected_history_run_id(self):
        row = self.history_table.currentRow()

        if row < 0:
            return None

        run_id_item = self.history_table.item(row, 0)

        if run_id_item is None:
            return None

        try:
            return int(run_id_item.text())
        except ValueError:
            return None

    def handle_set_run_a(self):
        run_id = self.get_selected_history_run_id()

        if run_id is None:
            self.history_summary_label.setText("Select a history run first.")
            return

        self.run_a_id = run_id
        self.run_a_label.setText(f"Run A: #{run_id}")

    def handle_set_run_b(self):
        run_id = self.get_selected_history_run_id()

        if run_id is None:
            self.history_summary_label.setText("Select a history run first.")
            return

        self.run_b_id = run_id
        self.run_b_label.setText(f"Run B: #{run_id}")
        
    def handle_compare_runs(self):

        if self.run_a_id is None:
            self.history_summary_label.setText("Select Run A before comparing.")
            return
        if self.run_b_id is None:
            self.history_summary_label.setText("Select Run B before comparing.")
            return

        if self.run_a_id  == self.run_b_id:
            self.history_summary_label.setText("Run A and Run B must be different.")
            return
        
        run_a_type = self.get_run_type_label(self.run_a_id)
        run_b_type = self.get_run_type_label(self.run_b_id)

        if run_a_type is None or run_b_type is None:
            self.history_summary_label.setText("One of the selected runs no longer exists.")
            return

        if run_a_type != run_b_type:
            self.history_summary_label.setText("Run A and Run B must be of the same type (Deterministic or AI).")
            return
        
        run_a_categories = self.get_run_selected_categories(self.run_a_id)
        run_b_categories = self.get_run_selected_categories(self.run_b_id)

        if run_a_categories is None or run_b_categories is None:
            self.history_summary_label.setText("Cannot compare these runs because selected categories were not recorded for one or both runs.")
            return

        if run_a_categories != run_b_categories:
            self.history_summary_label.setText("Run A and Run B must use the same selected test categories.")
            return
        


        issues_a = self.get_historical_run_issues(self.run_a_id)
        issues_b = self.get_historical_run_issues(self.run_b_id)

        if issues_a is None or issues_b is None:
            self.history_summary_label.setText("One of the selected runs no longer exists.")
            return
        
        comparison = compare_run_issues(issues_a, issues_b)
        self.current_comparison = comparison
        self.compare_details.clear()
        self.compare_header_label.setText(
            f"Run A: #{self.run_a_id} ({run_a_type}) | "
            f"Run B: #{self.run_b_id} ({run_b_type})"
        )

        self.populate_comparison_table(self.compare_new_table, comparison["new"])
        self.populate_comparison_table(self.compare_resolved_table, comparison["resolved"])
        self.populate_comparison_table(self.compare_unchanged_table, comparison["unchanged"])

        self.compare_tabs.setTabText(0, f"New issues ({len(comparison['new'])})")
        self.compare_tabs.setTabText(1, f"Resolved issues ({len(comparison['resolved'])})")
        self.compare_tabs.setTabText(2, f"Unchanged issues ({len(comparison['unchanged'])})")

        self.main_tabs.setCurrentIndex(2)

        self.history_summary_label.setText(
            f"Run #{self.run_a_id} vs Run #{self.run_b_id} | "
            f"New issues: {len(comparison['new'])} | "
            f"Resolved issues: {len(comparison['resolved'])} | "
            f"Unchanged issues: {len(comparison['unchanged'])}"
        )

    def get_historical_run_issues(self, run_id):
        run_summary = get_run_summary(run_id)
        run = run_summary["run"]

        if run is None:
            return None

        return [self.history_issue_to_dict(issue) for issue in run_summary["issues"]]

    def populate_comparison_table(self, table, issues):
        table.setRowCount(len(issues))

        for row, issue in enumerate(issues):
            values = [
                issue.get("severity"),
                issue.get("method"),
                issue.get("template_path") or issue.get("path"),
                issue.get("category"),
                issue.get("field"),
                issue.get("expected_status"),
                issue.get("status_code"),
            ]
            for column, value in enumerate(values):
                text = "" if value is None else str(value)
                table.setItem(row, column, QTableWidgetItem(text))

        table.resizeColumnsToContents()    

    def get_run_type_label(self, run_id):
        run_summary = get_run_summary(run_id)
        run = run_summary["run"]

        if run is None:
            return None

        return "AI" if run.ai_enabled else "Deterministic"

    def get_run_selected_categories(self, run_id):
        run_summary = get_run_summary(run_id)
        run = run_summary["run"]

        if run is None:
            return None
        
        if run.selected_categories is None:
            return None

        try:
            return set(json.loads(run.selected_categories))
        except (json.JSONDecodeError, TypeError):
            return None

    def handle_comparison_issue_selected(self, row, column):
        table = self.sender()

        if table is self.compare_new_table:
            issues = self.current_comparison["new"]
            comparison_status = "New issue"

        elif table is self.compare_resolved_table:
            issues = self.current_comparison["resolved"]
            comparison_status = "Resolved issue"

        elif table is self.compare_unchanged_table:
            issues = self.current_comparison["unchanged"]
            comparison_status = "Unchanged issue"

        else:
            return

        if row < 0 or row >= len(issues):
            return

        issue = issues[row]
        path = issue.get("template_path") or issue.get("path")

        details = (
            f"Comparison status: {comparison_status}\n"
            f"Severity: {issue.get('severity')}\n"
            f"Method: {issue.get('method')}\n"
            f"Path: {path}\n"
            f"Category: {issue.get('category')}\n"
            f"Field: {issue.get('field') or 'N/A'}\n"
            f"Expected status: {issue.get('expected_status')}\n"
            f"Actual status: {issue.get('status_code')}\n"
            f"Description: {issue.get('description', '')}"
        )
        self.compare_details.setPlainText(details)
def main():
    app = QApplication(sys.argv)

    init_db()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()