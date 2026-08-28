import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


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
        
        self.status_label = QLabel("Ready")


        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(self.base_url_input)
        layout.addWidget(self.run_button)
        layout.addWidget(self.status_label)
        layout.addStretch()

        central_widget = QWidget()
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)

    def handle_run_clicked(self):
        base_url = self.base_url_input.text().strip().rstrip("/")

        if not base_url:
            self.status_label.setText("Please enter an API base URL!")
            return

        self.status_label.setText(f"Deterministic run requested for: {base_url}")


def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()