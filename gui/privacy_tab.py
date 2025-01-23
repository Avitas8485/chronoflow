from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QListWidget, QLineEdit, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSlot
from gui.models import UIConstants
from engine.engine import Engine

class PrivacyTab(QWidget):
    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(UIConstants.SPACING)
        
        layout.addWidget(self._create_apps_group())
        layout.addWidget(self._create_titles_group())
        layout.addStretch()
        
    def _create_apps_group(self):
        group = QGroupBox("Excluded Applications")
        layout = QVBoxLayout()
        
        # Apps list
        self.excluded_apps_list = QListWidget()
        self.excluded_apps_list.addItems(self.engine.classifier.rules.privacy.excluded_apps)
        
        # App input
        app_input_layout = QHBoxLayout()
        self.app_pattern_input = QLineEdit()
        self.app_pattern_input.setPlaceholderText("Enter application pattern (e.g., *.exe)")
        add_app_btn = QPushButton("Add")
        remove_app_btn = QPushButton("Remove")
        
        app_input_layout.addWidget(self.app_pattern_input)
        app_input_layout.addWidget(add_app_btn)
        app_input_layout.addWidget(remove_app_btn)
        
        layout.addWidget(self.excluded_apps_list)
        layout.addLayout(app_input_layout)
        group.setLayout(layout)
        
        # Connect buttons
        add_app_btn.clicked.connect(self.add_excluded_app)
        remove_app_btn.clicked.connect(self.remove_excluded_app)
        
        return group
        
    def _create_titles_group(self):
        group = QGroupBox("Excluded Window Titles")
        layout = QVBoxLayout()
        
        # Titles list
        self.excluded_titles_list = QListWidget()
        self.excluded_titles_list.addItems(self.engine.classifier.rules.privacy.excluded_titles)
        
        # Title input
        title_input_layout = QHBoxLayout()
        self.title_pattern_input = QLineEdit()
        self.title_pattern_input.setPlaceholderText("Enter window title pattern (e.g., *private*)")
        add_title_btn = QPushButton("Add")
        remove_title_btn = QPushButton("Remove")
        
        title_input_layout.addWidget(self.title_pattern_input)
        title_input_layout.addWidget(add_title_btn)
        title_input_layout.addWidget(remove_title_btn)
        
        layout.addWidget(self.excluded_titles_list)
        layout.addLayout(title_input_layout)
        group.setLayout(layout)
        
        # Connect buttons
        add_title_btn.clicked.connect(self.add_excluded_title)
        remove_title_btn.clicked.connect(self.remove_excluded_title)
        
        return group
        
    def add_excluded_app(self):
        pattern = self.app_pattern_input.text()
        if pattern:
            self.engine.classifier.add_privacy_rule(excluded_app=pattern)
            self.excluded_apps_list.addItem(pattern)
            self.app_pattern_input.clear()
            
    def remove_excluded_app(self):
        current_item = self.excluded_apps_list.currentItem()
        if current_item:
            pattern = current_item.text()
            self.engine.classifier.rules.privacy.excluded_apps.remove(pattern)
            self.engine.classifier._save_rules()
            self.excluded_apps_list.takeItem(self.excluded_apps_list.row(current_item))
            
    def add_excluded_title(self):
        pattern = self.title_pattern_input.text()
        if pattern:
            self.engine.classifier.add_privacy_rule(excluded_title=pattern)
            self.excluded_titles_list.addItem(pattern)
            self.title_pattern_input.clear()
            
    def remove_excluded_title(self):
        current_item = self.excluded_titles_list.currentItem()
        if current_item:
            pattern = current_item.text()
            self.engine.classifier.rules.privacy.excluded_titles.remove(pattern)
            self.engine.classifier._save_rules()
            self.excluded_titles_list.takeItem(self.excluded_titles_list.row(current_item))
