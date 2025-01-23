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
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(UIConstants.SPACING * 2)
        main_layout.setContentsMargins(UIConstants.MARGIN, UIConstants.MARGIN,
                                     UIConstants.MARGIN, UIConstants.MARGIN)
        
        # Left column - Current activity and controls (1/3 width)
        left_column = QVBoxLayout()
        left_column.setSpacing(UIConstants.SPACING)
        
        # Make current activity more prominent
        current_activity = self._create_activity_group()
        current_activity.setMinimumHeight(150)
        left_column.addWidget(current_activity)
        
        # Controls below current activity
        controls = self._create_controls_group()
        controls.setMaximumHeight(100)
        left_column.addWidget(controls)
        left_column.addStretch()
        
        # Right column - Visualization and filters (2/3 width) 
        right_column = QVBoxLayout()
        right_column.setSpacing(UIConstants.SPACING)
        
        # Metrics at top
        self.metrics = MetricsComponent(self.engine)
        self.metrics.setMaximumHeight(120)
        right_column.addWidget(self.metrics)
        
        # Stats/filter group
        stats = self._create_stats_group()
        stats.setMaximumHeight(200)
        right_column.addWidget(stats)
        
        # Heatmap takes remaining space
        right_column.addWidget(self._create_heatmap_group(), stretch=1)
        
        # Set column ratios (1:2)
        main_layout.addLayout(left_column, stretch=1)
        main_layout.addLayout(right_column, stretch=2)
        
    def _create_activity_group(self):
        group = QGroupBox("Current Activity")
        layout = QVBoxLayout()
        self.current_activity_label = QLabel("None")
        self.current_category_label = QLabel("Category: None")
        layout.addWidget(self.current_activity_label)
        layout.addWidget(self.current_category_label)
        group.setLayout(layout)
        return group
    
    def _create_controls_group(self):
        group = QGroupBox("Tracking Controls")
        layout = QHBoxLayout()
        self.start_button = QPushButton("Start Tracking")
        self.stop_button = QPushButton("Stop Tracking")
        self.start_button.setMinimumWidth(UIConstants.BUTTON_MIN_WIDTH)
        self.stop_button.setMinimumWidth(UIConstants.BUTTON_MIN_WIDTH)
        self.start_button.clicked.connect(self.start_tracking)
        self.stop_button.clicked.connect(self.stop_tracking)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def _create_heatmap_group(self):
        group = QGroupBox("Activity Visualization")
        layout = QVBoxLayout()
        layout.setContentsMargins(UIConstants.MARGIN, UIConstants.MARGIN, 
                                UIConstants.MARGIN, UIConstants.MARGIN)
        
        # Create scroll area with proper sizing
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.heatmap = HeatmapWidget()
        scroll.setWidget(self.heatmap)
        
        layout.addWidget(scroll)
        group.setLayout(layout)
        return group
        
    def _create_stats_group(self):
        group = QGroupBox("Week & Category Filter") 
        layout = QHBoxLayout()
        layout.setContentsMargins(UIConstants.MARGIN, UIConstants.MARGIN,
                                UIConstants.MARGIN, UIConstants.MARGIN)
        
        # Week selection with navigation
        week_layout = QVBoxLayout()
        week_label = QLabel("Selected Week:")
        self.week_label = QLabel()
        
        week_nav = QHBoxLayout()
        self.prev_week_btn = QPushButton("← Previous")
        self.next_week_btn = QPushButton("Next →")
        self.prev_week_btn.clicked.connect(self._previous_week)
        self.next_week_btn.clicked.connect(self._next_week)
        week_nav.addWidget(self.prev_week_btn)
        week_nav.addWidget(self.next_week_btn)
        
        week_layout.addWidget(week_label)
        week_layout.addWidget(self.week_label)
        week_layout.addLayout(week_nav)
        
        # Category filter with label
        filter_layout = QVBoxLayout()
        filter_label = QLabel("Category Filter:")
        self.category_filter = QComboBox()
        self.category_filter.addItems([cat.value for cat in ActivityCategory])
        self.category_filter.currentIndexChanged.connect(self._update_heatmap)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.category_filter)
        filter_layout.addStretch()
        
        layout.addLayout(week_layout)
        layout.addLayout(filter_layout)
        group.setLayout(layout)
        
        # Initialize selected week
        self.selected_week_start = self._get_week_start(date.today())
        self._update_week_label()
        
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