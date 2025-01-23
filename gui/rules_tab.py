from typing import Dict
from PyQt6.QtCore import Qt, QTime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, 
    QFormLayout, QLineEdit, QTimeEdit, QCheckBox, QPushButton, QLabel, 
    QComboBox, QListWidget, QListWidgetItem, QFrame)
from PyQt6.QtGui import QIcon

from engine.engine import Engine
from gui.models import UIConstants
from models.activity import ActivityCategory
from models.rules import ActivityPattern


class RulesTab(QWidget):
    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(UIConstants.SPACING * 2)  # Increased spacing
        layout.addWidget(self._create_rules_group())
        layout.addStretch()
        
    def _create_rules_group(self):
        group = QGroupBox("Activity Rules")
        layout = QHBoxLayout()
        layout.setSpacing(UIConstants.SPACING * 2)

        # Left side - Category and rules list
        list_layout = QVBoxLayout()
        list_layout.setSpacing(UIConstants.SPACING)
        
        category_label = QLabel("Category:")
        category_label.setStyleSheet("font-weight: bold;")
        list_layout.addWidget(category_label)
        
        self.category_selector = QComboBox()
        self.category_selector.addItems([cat.value for cat in ActivityCategory])
        self.category_selector.currentIndexChanged.connect(self.load_category_rules)
        list_layout.addWidget(self.category_selector)
        
        rules_label = QLabel("Rules:")
        rules_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        list_layout.addWidget(rules_label)
        
        self.rules_list = QListWidget()
        self.rules_list.setAlternatingRowColors(True)
        self.rules_list.itemSelectionChanged.connect(self.rule_selected)
        list_layout.addWidget(self.rules_list)

        # Vertical separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        
        # Right side - Rule details form
        form_layout = QFormLayout()
        form_layout.setSpacing(UIConstants.SPACING)
        
        details_label = QLabel("Rule Details")
        details_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        form_layout.addRow(details_label)
        
        # Apps input with tooltip
        self.apps_input = QLineEdit()
        self.apps_input.setPlaceholderText("e.g., chrome.exe, firefox.exe")
        self.apps_input.setToolTip("Enter application executable names, separated by commas")
        form_layout.addRow("Applications:", self.apps_input)
        
        # Titles input with tooltip
        self.titles_input = QLineEdit()
        self.titles_input.setPlaceholderText("e.g., Gmail - Google Chrome")
        self.titles_input.setToolTip("Enter window title patterns, separated by commas")
        form_layout.addRow("Window Titles:", self.titles_input)
        
        # Time range group
        time_group = QGroupBox("Time Settings")
        time_layout = QVBoxLayout()
        
        range_layout = QHBoxLayout()
        self.start_time = QTimeEdit()
        self.end_time = QTimeEdit()
        range_layout.addWidget(QLabel("From:"))
        range_layout.addWidget(self.start_time)
        range_layout.addWidget(QLabel("To:"))
        range_layout.addWidget(self.end_time)
        time_layout.addLayout(range_layout)
        
        # Days group
        days_layout = QHBoxLayout()
        self.day_checks: Dict[str, QCheckBox] = {}
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            checkbox = QCheckBox(day)
            checkbox.setToolTip(f"Include {day}")
            self.day_checks[day] = checkbox
            days_layout.addWidget(checkbox)
        time_layout.addLayout(days_layout)
        time_group.setLayout(time_layout)
        form_layout.addRow(time_group)
        
        # Buttons with icons
        button_layout = QHBoxLayout()
        self.add_rule_btn = QPushButton("Add Rule")
        self.add_rule_btn.setIcon(QIcon.fromTheme("list-add"))
        self.update_rule_btn = QPushButton("Update Rule")
        self.update_rule_btn.setIcon(QIcon.fromTheme("document-save"))
        self.delete_rule_btn = QPushButton("Delete Rule")
        self.delete_rule_btn.setIcon(QIcon.fromTheme("edit-delete"))
        
        self.add_rule_btn.clicked.connect(self.add_rule)
        self.update_rule_btn.clicked.connect(self.update_rule)
        self.delete_rule_btn.clicked.connect(self.delete_rule)
        
        button_layout.addWidget(self.add_rule_btn)
        button_layout.addWidget(self.update_rule_btn)
        button_layout.addWidget(self.delete_rule_btn)
        form_layout.addRow(button_layout)

        # Layout assembly
        layout.addLayout(list_layout, stretch=1)
        layout.addWidget(separator)
        layout.addLayout(form_layout, stretch=2)
        
        # Load initial rules
        self.load_category_rules()
        
        group.setLayout(layout)
        return group

    def _clear_form(self):
        """Clear all form fields"""
        self.apps_input.clear()
        self.titles_input.clear()
        self.start_time.setTime(QTime(0, 0))
        self.end_time.setTime(QTime(0, 0))
        for checkbox in self.day_checks.values():
            checkbox.setChecked(False)

    def load_category_rules(self):
        """Load rules for selected category"""
        self.rules_list.clear()
        self._clear_form()  # Clear form when changing categories
        category = ActivityCategory(self.category_selector.currentText())
        
        if category in self.engine.classifier.rules.rules:
            rule_set = self.engine.classifier.rules.rules[category]
            for pattern in rule_set.patterns:
                item = QListWidgetItem(f"{pattern.apps[0]}... ({len(pattern.apps)} apps)")
                item.setData(Qt.ItemDataRole.UserRole, pattern)
                self.rules_list.addItem(item)
                
    def rule_selected(self):
        """Handle rule selection"""
        items = self.rules_list.selectedItems()
        if not items:
            self._clear_form()  # Clear form when no rule selected
            return
            
        pattern: ActivityPattern = items[0].data(Qt.ItemDataRole.UserRole)
        
        # Update form
        self.apps_input.setText(", ".join(pattern.apps))
        self.titles_input.setText(", ".join(pattern.titles))
        
        if pattern.time_ranges:
            start, end = pattern.time_ranges[0].split("-")
            self.start_time.setTime(QTime.fromString(start, "HH:mm"))
            self.end_time.setTime(QTime.fromString(end, "HH:mm"))
            
        for day, checkbox in self.day_checks.items():
            checkbox.setChecked(day in (pattern.days or []))
            
    def add_rule(self):
        """Add new rule"""
        category = ActivityCategory(self.category_selector.currentText())
        pattern = self._get_pattern_from_form()
        
        self.engine.classifier.add_rule(category, pattern)
        self.load_category_rules()
        
    def update_rule(self):
        """Update selected rule"""
        items = self.rules_list.selectedItems()
        if not items:
            return
            
        old_pattern: ActivityPattern = items[0].data(Qt.ItemDataRole.UserRole)
        new_pattern = self._get_pattern_from_form()
        
        category = ActivityCategory(self.category_selector.currentText())
        self.engine.classifier.modify_pattern(
            category,
            old_pattern.id,
            apps=new_pattern.apps,
            titles=new_pattern.titles,
            time_ranges=new_pattern.time_ranges,
            days=new_pattern.days
        )
        self.load_category_rules()
        
    def delete_rule(self):
        """Delete selected rule"""
        items = self.rules_list.selectedItems()
        if not items:
            return
            
        pattern: ActivityPattern = items[0].data(Qt.ItemDataRole.UserRole)
        category = ActivityCategory(self.category_selector.currentText())
        
        self.engine.classifier.remove_pattern(category, pattern.id)
        self.load_category_rules()
        
    def _get_pattern_from_form(self) -> ActivityPattern:
        """Create pattern from form data"""
        apps = [a.strip() for a in self.apps_input.text().split(",")]
        titles = [t.strip() for t in self.titles_input.text().split(",")]
        
        time_range = f"{self.start_time.time().toString('HH:mm')}-{self.end_time.time().toString('HH:mm')}"
        days = [day for day, check in self.day_checks.items() if check.isChecked()]
        
        return ActivityPattern(
            apps=apps,
            titles=titles,
            time_ranges=[time_range],
            days=days
        )
