from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt

class CardWidget(QFrame):
    def __init__(self, title: str, content: QWidget):
        super().__init__()
        
        # Set frame style and shape
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        
        # Apply stylesheet for card appearance
        self.setStyleSheet("""
            CardWidget {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #ddd;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(8)
        
        # Add title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
            }
        """)
        layout.addWidget(title_label)
        
        # Add content
        layout.addWidget(content)