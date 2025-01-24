from PyQt6.QtWidgets import (QWidget, QGridLayout, QLabel, 
                           QGraphicsOpacityEffect, QToolTip)
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QCursor
from models.activity import ActivityHeatmap
from datetime import datetime, date
import colorsys

class HeatmapCell(QWidget):
    def __init__(self, value: float = 0.0, max_value: float = 1.0):
        super().__init__()
        self.value = value
        self.max_value = max_value
        self.setMinimumSize(30, 30)
        self.setMouseTracking(True)
        
    def paintEvent(self, a0):
        painter = QPainter(self)
        
        # Calculate color based on value
        if self.max_value > 0:
            intensity = min(self.value / self.max_value, 1.0)
        else:
            intensity = 0.0
            
        # Create color gradient from white to dark blue
        r = int(255 * (1 - intensity))  # Decrease red from 255 to 0
        g = int(255 * (1 - intensity))  # Decrease green from 255 to 0
        b = int(255 - (intensity * 100))  # Keep more blue, decrease less
        
        color = QColor(r, g, b)
        
        # Draw rounded rectangle
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(color)
        rect = self.rect().adjusted(2, 2, -2, -2)  # Add padding
        painter.drawRoundedRect(rect, 5, 5)
        
    def enterEvent(self, event):
        hours = self.value
        if hours > 0:
            tooltip = f"{hours:.1f} hours"
            QToolTip.showText(QCursor.pos(), tooltip, self)

class HeatmapWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        
    def _setup_ui(self):
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setSpacing(2)
        
        # Add hour labels (columns)
        for hour in range(24):
            label = QLabel(f"{hour:02d}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(label, 0, hour + 1)
            
        # Add weekday labels (rows)
        self.weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for i, day in enumerate(self.weekdays):
            label = QLabel(day)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.grid_layout.addWidget(label, i + 1, 0)
            
        # Initialize empty heatmap cells
        self.cells = {}
        for row in range(7):
            for col in range(24):
                cell = HeatmapCell()
                self.cells[(row, col)] = cell
                self.grid_layout.addWidget(cell, row + 1, col + 1)
                
    def set_data(self, heatmap: ActivityHeatmap):
        if not heatmap or not heatmap.data:
            return
            
        # Find maximum value for scaling
        max_value = 0.0
        for daily_data in heatmap.data.values():
            max_value = max(max_value, max(daily_data.hours))
            
        # Reset all cells
        for cell in self.cells.values():
            cell.value = 0.0
            cell.max_value = max_value
            
        # Update cells with data
        for dt, daily_data in heatmap.data.items():
            weekday = dt.weekday()  # 0 = Monday
            for hour, value in enumerate(daily_data.hours):
                if (weekday, hour) in self.cells:
                    self.cells[(weekday, hour)].value = value
                    self.cells[(weekday, hour)].update()