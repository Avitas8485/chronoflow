from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QComboBox, QFrame)
from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QLineSeries, QDateTimeAxis, QValueAxis, QBarSeries, QBarSet
from PyQt6.QtCore import Qt, QDateTime, QTime
from PyQt6.QtGui import QPainter, QColor, QPen
from datetime import datetime, timedelta
from typing import List
import math

from engine.engine import Engine
from models.activity import Interval
from gui.models import UIConstants
from gui.widgets import CardWidget
from models.analytics import CategoryDistribution, FocusSession, ProductivityTrend, WorkPatterns

class AnalyticsTab(QWidget):
    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(UIConstants.MARGIN, UIConstants.MARGIN, 
                                UIConstants.MARGIN, UIConstants.MARGIN)
        layout.setSpacing(UIConstants.SPACING)

        # Time range selector
        range_layout = QHBoxLayout()
        range_label = QLabel("Time Range:")
        self.range_combo = QComboBox()
        self.range_combo.addItems(["Today", "Last 7 Days", "Last 30 Days"])
        self.range_combo.currentTextChanged.connect(self._update_charts)
        range_layout.addWidget(range_label)
        range_layout.addWidget(self.range_combo)
        range_layout.addStretch()
        layout.addLayout(range_layout)

        # Charts grid
        charts_layout = QHBoxLayout()
        
        # Left column
        left_column = QVBoxLayout()
        self.productivity_chart = self._create_productivity_chart()
        self.category_chart = self._create_category_chart()
        left_column.addWidget(CardWidget("Productivity Trend", self.productivity_chart))
        left_column.addWidget(CardWidget("Category Distribution", self.category_chart))
        
        # Right column
        right_column = QVBoxLayout()
        self.focus_chart = self._create_focus_chart()
        self.peak_hours_chart = self._create_peak_hours_chart()
        right_column.addWidget(CardWidget("Focus Sessions", self.focus_chart))
        right_column.addWidget(CardWidget("Peak Productivity Hours", self.peak_hours_chart))
        
        charts_layout.addLayout(left_column)
        charts_layout.addLayout(right_column)
        layout.addLayout(charts_layout)
        
        self._update_charts()

    def _create_productivity_chart(self) -> QChartView:
        chart = QChart()
        chart.setTitle("Productivity Trend")
        
        # Create and style series
        series = QLineSeries()
        pen = QPen(QColor("#2196F3"))
        pen.setWidth(3)
        series.setPen(pen)
        
        # Create axes
        date_axis = QDateTimeAxis()
        date_axis.setFormat("MMM dd")
        date_axis.setTitleText("Date")
        
        value_axis = QValueAxis()
        value_axis.setRange(0, 1)
        value_axis.setTitleText("Productivity Score")
        value_axis.setLabelFormat("%.1f")
        value_axis.setGridLineVisible(True)
        
        chart.addSeries(series)
        chart.addAxis(date_axis, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(value_axis, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(date_axis)
        series.attachAxis(value_axis)
        
        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        return view

    def _create_category_chart(self) -> QChartView:
        chart = QChart()
        chart.setTitle("Category Distribution")
        
        series = QPieSeries()
        series.setLabelsVisible(True)
        
        # Custom colors for categories
        colors = ["#2196F3", "#4CAF50", "#FFC107", "#9C27B0", "#F44336"]
        
        chart.addSeries(series)
        chart.setTheme(QChart.ChartTheme.ChartThemeLight)  # This ensures legend is created
        legend = chart.legend()
        if legend is not None:
            legend.setVisible(True)
            legend.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        return view

    def _create_focus_chart(self) -> QChartView:
        chart = QChart()
        chart.setTitle("Focus Sessions")
        series = QLineSeries()
        chart.addSeries(series)
        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        return view

    def _create_peak_hours_chart(self) -> QChartView:
        chart = QChart()
        chart.setTitle("Peak Productivity Hours")
        series = QLineSeries()
        chart.addSeries(series)
        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        return view

    def _update_charts(self):
        range_text = self.range_combo.currentText()
        now = datetime.now()
        
        if range_text == "Today":
            start_date = now.replace(hour=0, minute=0, second=0)
            interval = Interval.DAY
        elif range_text == "Last 7 Days":
            start_date = now - timedelta(days=7)
            interval = Interval.WEEK
        else:  # Last 30 Days
            start_date = now - timedelta(days=30)
            interval = Interval.MONTH

        # Update productivity trend
        trends = self.engine.get_productivity_trends(start_date, now, interval)
        self._update_productivity_chart(trends)

        # Update category distribution
        distribution = self.engine.get_category_distribution(start_date, now)
        self._update_category_chart(distribution)

        # Update focus sessions
        sessions = self.engine.get_focus_sessions()
        self._update_focus_chart(sessions)

        # Update peak hours
        patterns = self.engine.get_work_patterns()
        self._update_peak_hours_chart(patterns)

    def _parse_period(self, period: str) -> datetime:
        """Parse period string into datetime based on format"""
        try:
            if len(period) == 7:  # YYYY-MM format
                return datetime.strptime(period, "%Y-%m")
            elif len(period) == 10:  # YYYY-MM-DD format
                return datetime.strptime(period, "%Y-%m-%d")
            else:  # Full ISO format
                return datetime.fromisoformat(period)
        except ValueError:
            # Return epoch if parsing fails
            return datetime.fromtimestamp(0)

    def _update_productivity_chart(self, trends: List[ProductivityTrend]):
        series = QLineSeries()
        
        for trend in trends:
            dt = self._parse_period(trend.period)
            series.append(dt.timestamp() * 1000, trend.avg_productivity)
        
        chart = self.productivity_chart.chart()
        if not chart:
            return
            
        chart.removeAllSeries()
        chart.addSeries(series)
        
        # Configure axes
        chart.createDefaultAxes()
        x_axis = chart.axes(Qt.Orientation.Horizontal)[0]
        from PyQt6.QtCharts import QDateTimeAxis
        x_axis = QDateTimeAxis()
        x_axis.setFormat("MMM dd")  # Format date display
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(x_axis)
        
        y_axis = chart.axes(Qt.Orientation.Vertical)[0]
        y_axis.setRange(0, 1.0)  # Productivity score range 0-1
        y_axis.setTitleText("Productivity Score")

    def _update_category_chart(self, distribution: CategoryDistribution):
        series = QPieSeries()
        total_hours = sum(m.total_hours for m in distribution.categories.values())
        
        for i, (category, metrics) in enumerate(distribution.categories.items()):
            percentage = (metrics.total_hours / total_hours * 100) if total_hours > 0 else 0
            label = f"{category.value}\n{percentage:.1f}%"
            slice = series.append(label, metrics.total_hours)
            if slice is not None:
                slice.setLabelVisible(True)
        
        chart = self.category_chart.chart()
        if not chart:
            return
        chart.removeAllSeries()
        chart.addSeries(series)

    def _update_focus_chart(self, sessions: List[FocusSession]):
        series = QLineSeries()
        for session in sessions:
            series.append(session.start_time.timestamp() * 1000, session.focus_score)
        
        chart = self.focus_chart.chart()
        if not chart:
            return
        chart.removeAllSeries()
        chart.addSeries(series)
        chart.createDefaultAxes()

    def _update_peak_hours_chart(self, patterns: WorkPatterns):
        chart = self.peak_hours_chart.chart()
        if not chart:
            return
        
        series = QLineSeries()
        pen = QPen(QColor("#4CAF50"))
        pen.setWidth(3)
        series.setPen(pen)
        
        # Create 24-hour data points
        hour_data = {int(h.hour.split(":")[0]): h.productivity for h in patterns.peak_productivity_hours}
        for hour in range(24):
            series.append(hour, hour_data.get(hour, 0))
        
        chart.removeAllSeries()
        chart.addSeries(series)
        
        # Configure axes
        x_axis = QValueAxis()
        x_axis.setRange(0, 23)
        x_axis.setLabelFormat("%d:00")
        x_axis.setTickCount(12)
        x_axis.setGridLineVisible(True)
        x_axis.setTitleText("Hour of Day")
        
        y_axis = QValueAxis()
        y_axis.setRange(0, 1)
        y_axis.setTitleText("Productivity Score")
        y_axis.setLabelFormat("%.1f")
        y_axis.setGridLineVisible(True)
        
        chart.addAxis(x_axis, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(x_axis)
        series.attachAxis(y_axis)