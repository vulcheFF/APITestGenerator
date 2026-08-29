from PySide6.QtWidgets import QDialog, QDialogButtonBox, QCheckBox, QHBoxLayout, QPushButton, QScrollArea, QVBoxLayout, QWidget, QLineEdit



class CategorySelectionDialog(QDialog):
    def __init__(self, categories: list[str], selected_categories: list[str], parent=None):
        super().__init__(parent)

        self.setWindowTitle("Select deterministic test categories")
        self.resize(420, 500)

        self.checkboxes: dict[str, QCheckBox] = {}

        main_layout = QVBoxLayout(self)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search categories...")
        self.search_input.textChanged.connect(self.filter_categories)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        for category in categories:
            checkbox = QCheckBox(category)
            checkbox.setChecked(category in selected_categories)

            self.checkboxes[category] = checkbox
            scroll_layout.addWidget(checkbox)

        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)

        selection_buttons_layout = QHBoxLayout()

        select_all_button = QPushButton("Select all")
        clear_all_button = QPushButton("Clear all")

        select_all_button.clicked.connect(self.select_all)
        clear_all_button.clicked.connect(self.clear_all)

        selection_buttons_layout.addWidget(select_all_button)
        selection_buttons_layout.addWidget(clear_all_button)

        dialog_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)

        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)

        main_layout.addWidget(self.search_input)
        main_layout.addWidget(scroll_area)
        main_layout.addLayout(selection_buttons_layout)
        main_layout.addWidget(dialog_buttons)


    def select_all(self):
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)

    def clear_all(self):
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def get_selected_categories(self) -> list[str]:
        return [ category for category, checkbox in self.checkboxes.items() if checkbox.isChecked()]

    def filter_categories(self, text: str):
        search_text = text.strip().lower()

        for category, checkbox in self.checkboxes.items():
            checkbox.setVisible(search_text in category.lower())