from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QFrame, QPushButton, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal
from datetime import datetime, timedelta
from models.activity import ActivityMetrics, ActivityCategory
from engine.engine import Engine
from models.time_range import TimeRange

class MetricCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; color: #666;")
        
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
    def set_value(self, value: str):
        self.value_label.setText(value)

    def set_title(self, title: str):
        self.title_label.setText(title)

class MetricsComponent(QWidget):
    refresh_requested = pyqtSignal()
    
    def __init__(self, engine: Engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.selected_range = TimeRange.TODAY
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Add range selector
        range_layout = QHBoxLayout()
        range_label = QLabel("Time Range:")
        self.range_selector = QComboBox()
        self.range_selector.addItems([r.value for r in TimeRange])
        self.range_selector.currentIndexChanged.connect(self._on_range_changed)
        range_layout.addWidget(range_label)
        range_layout.addWidget(self.range_selector)
        range_layout.addStretch()
        
        # Metrics cards container
        metrics_layout = QHBoxLayout()
        
        self.total_time = MetricCard("Total Time Today")
        self.avg_session = MetricCard("Avg Session Length")
        self.peak_hours = MetricCard("Peak Hours")
        self.activity_count = MetricCard("Activity Count")
        
        metrics_layout.addWidget(self.total_time)
        metrics_layout.addWidget(self.avg_session)
        metrics_layout.addWidget(self.peak_hours)
        metrics_layout.addWidget(self.activity_count)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_metrics)
        
        layout.addLayout(range_layout)
        layout.addLayout(metrics_layout)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
    def _on_range_changed(self):
        self.selected_range = TimeRange(self.range_selector.currentText())
        self.update_metrics()
    
    def update_metrics(self):
        try:
            start_date, end_date = self.selected_range.get_date_range()
            metrics = self.engine.get_activity_metrics(start_date, end_date)
            
            # Update card titles with range
            self.total_time.title_label.setText(f"Total Time ({self.selected_range.value})")
            
            # Format and update values
            self.total_time.set_value(self._format_duration(metrics.total_duration))
            self.avg_session.set_value(self._format_duration(metrics.average_duration))
            self.peak_hours.set_value(self._format_peak_hours(metrics.peak_hours))
            self.activity_count.set_value(str(metrics.activity_count))
            
        except Exception as e:
            print(f"Error updating metrics: {e}")
            
    def refresh_metrics(self):
        self.update_metrics()
        self.refresh_requested.emit()
        
    @staticmethod
    def _format_duration(duration: timedelta) -> str:
        hours = duration.total_seconds() // 3600
        minutes = (duration.total_seconds() % 3600) // 60
        return f"{int(hours)}h {int(minutes)}m"
    
    @staticmethod
    def _format_peak_hours(hours: list[int]) -> str:
        if not hours:
            return "--"
        return ", ".join(f"{h:02d}:00" for h in hours)