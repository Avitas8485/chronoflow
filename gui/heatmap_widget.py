from PyQt6.QtWidgets import QWidget, QToolTip, QSizePolicy
from PyQt6.QtCore import Qt, QSize, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from datetime import datetime, date, timedelta
from models.activity import ActivityHeatmap, ActivityCategory
from typing import Dict, Optional, Tuple

class HeatmapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.heatmap_data: Optional[ActivityHeatmap] = None
        self.cell_size = 20
        self.padding = 5
        self.hour_labels = [f"{h:02d}:00" for h in range(24)]
        self.weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        self.setMouseTracking(True)
        
        # Add size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Color scheme (using HSL for better gradients)
        self.min_color = QColor(220, 220, 220)  # Light gray
        self.max_color = QColor(46, 204, 113)   # Green
        self.background_color = QColor(248, 248, 248)
        self.grid_color = QColor(230, 230, 230)
        
        # Font settings
        self.label_font = QFont("Segoe UI", 8)
        
    def set_data(self, heatmap: ActivityHeatmap):
        self.heatmap_data = heatmap
        # Force layout update
        self.updateGeometry()
        self.update()
        
    def sizeHint(self) -> QSize:
        label_width = 30  # Width for day labels
        width = label_width + len(self.hour_labels) * (self.cell_size + self.padding) + self.padding
        height = len(self.heatmap_data.data) * (self.cell_size + self.padding) + 40 if self.heatmap_data else 100
        return QSize(width, height)
        
    def minimumSizeHint(self) -> QSize:
        # Ensure minimum size is reasonable
        return QSize(800, 400)
        
    def _get_cell_color(self, value: float) -> QColor:
        """Calculate cell color using linear interpolation"""
        if value == 0:
            return self.min_color
            
        # Normalize value between 0 and 1
        intensity = min(value / 3600, 1.0)  # Max intensity at 1 hour
        
        # Linear interpolation between colors
        return QColor(
            int(self.min_color.red() + (self.max_color.red() - self.min_color.red()) * intensity),
            int(self.min_color.green() + (self.max_color.green() - self.min_color.green()) * intensity),
            int(self.min_color.blue() + (self.max_color.blue() - self.min_color.blue()) * intensity)
        )
        
    def _get_cell_rect(self, row: int, col: int) -> QRect:
        """Get rectangle for cell at given row and column"""
        label_width = 30
        x = label_width + col * (self.cell_size + self.padding) + self.padding
        y = row * (self.cell_size + self.padding) + 40  # Extra space for hour labels
        return QRect(x, y, self.cell_size, self.cell_size)
        
    def paintEvent(self, a0):
        if not self.heatmap_data:
            return            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set font
        painter.setFont(self.label_font)
        
        # Draw hour labels
        for i, label in enumerate(self.hour_labels):
            rect = self._get_cell_rect(0, i)
            rect.setY(10)  # Move labels up
            painter.save()
            painter.translate(rect.center())
            painter.rotate(-45)  # Rotate text
            #painter.drawText(QRect(-50, -10, 100, 20), Qt.AlignmentFlag.AlignCenter, label)
            painter.restore()
            
        # Draw weekday labels
        for row, (day, _) in enumerate(self.heatmap_data.data.items()):
            weekday = day.strftime("%a")
            rect = QRect(5, self._get_cell_rect(row, 0).y(), 25, self.cell_size)
            painter.drawText(rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, weekday)
            
        # Draw heatmap cells
        for row, (day, daily_data) in enumerate(self.heatmap_data.data.items()):
            for col, value in enumerate(daily_data.hours):
                rect = self._get_cell_rect(row, col)
                
                # Draw cell with rounded corners
                path = painter.drawRoundedRect(rect, 4, 4)
                color = self._get_cell_color(value)
                painter.fillRect(rect, color)
                
                # Draw subtle border
                painter.setPen(QPen(self.grid_color, 1))
                painter.drawRoundedRect(rect, 4, 4)
                
    def mouseMoveEvent(self, a0):
        if not self.heatmap_data:
            return
            
        # Calculate cell position from mouse coordinates
        if a0 is not None:
            col = (a0.pos().x() - self.padding) // (self.cell_size + self.padding)
            row = (a0.pos().y() - self.padding) // (self.cell_size + self.padding) - 1
        else:
            return
        
        if 0 <= col < 24 and row >= 0:
            days = list(self.heatmap_data.data.keys())
            if row < len(days):
                day = days[row]
                hours = self.heatmap_data.data[day].hours
                duration_mins = hours[col] / 60
                tooltip = f"{day}\n{self.hour_labels[col]}\nActivity: {duration_mins:.1f} minutes"
                QToolTip.showText(a0.globalPosition().toPoint(), tooltip)