from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, 
                           QLabel, QPushButton, QCalendarWidget, QComboBox,
                           QScrollArea)
from PyQt6.QtCore import pyqtSlot, QDate, Qt, pyqtSignal, QTimer
from datetime import datetime, timedelta, date
from gui.heatmap_widget import HeatmapWidget
from gui.metrics import MetricsComponent  
from gui.models import UIConstants
from engine.engine import Engine
from models.activity import ActivityCategory
import logging



class DashboardTab(QWidget):
    activity_updated = pyqtSignal()  # Add signal
    
    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine
        self.heatmap = None
        self.metrics = None  
        self._setup_ui()
        
        # Add refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.setInterval(1000)  # 1 second refresh
        self.refresh_timer.timeout.connect(self.update_current_activity)
        
        # Sync UI with engine state
        if self.engine.is_running:
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.refresh_timer.start()
            self.update_current_activity()  # Initial update
        else:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(UIConstants.SPACING * 2)
        main_layout.setContentsMargins(UIConstants.MARGIN * 2, UIConstants.MARGIN * 2,
                                     UIConstants.MARGIN * 2, UIConstants.MARGIN * 2)

        # Top Section: Controls and Current Activity
        top_section = QGroupBox("Activity Tracking")
        top_layout = QVBoxLayout()
        
        # Controls Row
        controls_layout = QHBoxLayout()
        controls = self._create_controls_group()
        controls.setFixedHeight(70)
        controls_layout.addWidget(controls)
        controls_layout.addStretch()
        
        # Current Activity Row
        activity_layout = QHBoxLayout()
        current_activity = self._create_activity_group()
        current_activity.setMinimumHeight(100)
        self.metrics = MetricsComponent(self.engine)
        self.metrics.setMinimumHeight(150)
        
        activity_layout.addWidget(current_activity, stretch=4)
        activity_layout.addWidget(self.metrics, stretch=6)
        
        top_layout.addLayout(controls_layout)
        top_layout.addLayout(activity_layout)
        top_section.setLayout(top_layout)

        # Create Heatmap Section
        heatmap_section = QGroupBox("Activity Analysis")
        heatmap_layout = QVBoxLayout()
        
        # Analysis Controls Row
        analysis_layout = QHBoxLayout()
        filter_group = self._create_filter_group()
        week_nav = self._create_week_nav_group()
        analysis_layout.addWidget(filter_group)
        analysis_layout.addWidget(week_nav)
        analysis_layout.addStretch()
        
        # Heatmap Widget
        self.heatmap = HeatmapWidget()
        self.heatmap.setMinimumHeight(300)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(self.heatmap)
        
        heatmap_layout.addLayout(analysis_layout)
        heatmap_layout.addWidget(scroll)
        heatmap_section.setLayout(heatmap_layout)

        # Add all sections to main layout
        main_layout.addWidget(top_section)
        main_layout.addWidget(heatmap_section, stretch=1)

    def _create_activity_group(self):
        group = QGroupBox("Current Activity")
        layout = QVBoxLayout()
        layout.setSpacing(UIConstants.SPACING)
        layout.setContentsMargins(UIConstants.MARGIN * 2, UIConstants.MARGIN * 2,
                                UIConstants.MARGIN * 2, UIConstants.MARGIN * 2)
        
        # Larger font for current activity
        self.current_activity_label = QLabel("None")
        self.current_activity_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        self.current_category_label = QLabel("Category: None")
        self.current_category_label.setStyleSheet("font-size: 10pt;")
        
        layout.addWidget(self.current_activity_label)
        layout.addWidget(self.current_category_label)
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def _create_controls_group(self):
        group = QGroupBox("Tracking Controls")
        layout = QHBoxLayout()
        layout.setSpacing(UIConstants.SPACING * 2)
        
        # Equal width buttons
        button_width = 120
        self.start_button = QPushButton("Start Tracking")
        self.stop_button = QPushButton("Stop Tracking")
        self.start_button.setFixedWidth(button_width)
        self.stop_button.setFixedWidth(button_width)
        
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def _create_heatmap_group(self):
        group = QGroupBox("Activity Heatmap")
        layout = QVBoxLayout()
        layout.setContentsMargins(UIConstants.MARGIN, UIConstants.MARGIN, 
                                UIConstants.MARGIN, UIConstants.MARGIN)
        
        # Create scroll area with proper sizing
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.heatmap = HeatmapWidget()
        self.heatmap.setMinimumHeight(300) # Ensure minimum height
        scroll.setWidget(self.heatmap)
        
        layout.addWidget(scroll)
        group.setLayout(layout)
        return group
        
    def _create_filter_group(self):
        group = QGroupBox("Category Filter")
        layout = QVBoxLayout()
        layout.setContentsMargins(UIConstants.MARGIN, UIConstants.MARGIN // 2,
                                UIConstants.MARGIN, UIConstants.MARGIN // 2)
        
        self.category_filter = QComboBox()
        self.category_filter.addItems([cat.value for cat in ActivityCategory])
        self.category_filter.currentIndexChanged.connect(self._update_heatmap)
        
        layout.addWidget(self.category_filter)
        group.setLayout(layout)
        group.setMaximumWidth(200)
        group.setFixedHeight(80)  # Set fixed height
        return group

    def _create_week_nav_group(self):
        group = QGroupBox("Week Selection") 
        layout = QVBoxLayout()
        layout.setContentsMargins(UIConstants.MARGIN, UIConstants.MARGIN // 2,
                                UIConstants.MARGIN, UIConstants.MARGIN // 2)
        layout.setSpacing(UIConstants.SPACING // 2)  # Reduce spacing
        
        self.week_label = QLabel()
        self.week_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        nav_layout = QHBoxLayout()
        self.prev_week_btn = QPushButton("← Previous")
        self.next_week_btn = QPushButton("Next →")
        
        self.prev_week_btn.clicked.connect(self._previous_week)
        self.next_week_btn.clicked.connect(self._next_week)
        
        nav_layout.addWidget(self.prev_week_btn)
        nav_layout.addWidget(self.next_week_btn)
        
        layout.addWidget(self.week_label)
        layout.addLayout(nav_layout)
        
        self.selected_week_start = self._get_week_start(date.today())
        self._update_week_label()
        
        group.setLayout(layout)
        group.setMaximumWidth(300)
        group.setFixedHeight(80)  # Set fixed height
        return group

    def _get_week_start(self, for_date: date) -> date:
        """Get the Monday of the week containing the given date"""
        return for_date - timedelta(days=for_date.weekday())

    def _update_week_label(self):
        week_end = self.selected_week_start + timedelta(days=6)
        self.week_label.setText(
            f"{self.selected_week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"
        )

    def _previous_week(self):
        self.selected_week_start -= timedelta(days=7)
        self._update_week_label()
        self._update_heatmap()

    def _next_week(self):
        self.selected_week_start += timedelta(days=7)
        self._update_week_label()
        self._update_heatmap()
    
    @pyqtSlot()
    def update_current_activity(self):
        if not self.engine.is_running:
            return
            
        activity = self.engine.session.current_activity
        if activity:
            self.current_activity_label.setText(
                f"Current Activity: {activity.application} - {activity.window_title}"
            )
            self.current_category_label.setText(
                f"Category: {activity.category.value if activity.category else 'Uncategorized'}"
            )
        
    @pyqtSlot()
    def start_tracking(self):
        if self.engine.is_running:
            logging.warning("Tracking already running")
            return
        self.engine.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        if self.metrics:
            self.metrics.update_metrics()
        self.refresh_timer.start()  # Start refresh timer
        
    @pyqtSlot()
    def stop_tracking(self):
        if not self.engine.is_running:
            logging.warning("Tracking not running")
            return
        self.engine.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.refresh_timer.stop()  # Stop refresh timer
        self.current_activity_label.setText("None")
        self.current_category_label.setText("Category: None")

    @pyqtSlot()
    def _update_heatmap_wrapper(self):
        """Wrapper to handle the heatmap update"""
        self._update_heatmap()

    def _update_heatmap(self):
        if not self.heatmap:
            return
            
        try:
            selected_category = ActivityCategory(self.category_filter.currentText())
            
            # Get heatmap data for selected week
            start_date = datetime.combine(self.selected_week_start, datetime.min.time())
            end_date = start_date + timedelta(days=7)
            
            heatmap_data = self.engine.get_activity_heatmap(
                start_date=start_date,
                end_date=end_date,
                category=selected_category
            )
            
            # Update heatmap widget
            self.heatmap.set_data(heatmap_data)
        except Exception as e:
            logging.error(f"Failed to update heatmap: {e}")
            self.current_activity_label.setText(f"Error updating heatmap: {str(e)}")

    def showEvent(self, a0):
        super().showEvent(a0)
        # Update heatmap and metrics when tab is shown
        self._update_heatmap_wrapper()
        if self.metrics:
            self.metrics.update_metrics()