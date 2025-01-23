import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QTabWidget, QSystemTrayIcon, QMenu,)
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QIcon, QAction, QCloseEvent
from typing import Optional
import sys
from tracker.activity_tracker import WindowsActivityTracker
from classifier.classifier import ActivityClassifier
from storage.sqlite_storage import SQLiteActivityStorage
from engine.engine import Engine
from gui.dashboard_tab import DashboardTab
from gui.rules_tab import RulesTab
from gui.privacy_tab import PrivacyTab
from gui.models import UIConstants

class ChronoFlowGUI(QMainWindow):
    def __init__(self):
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('chronoflow.log'),
                logging.StreamHandler()
            ]
        )
        
        super().__init__()
        self._init_core_components()
        self._setup_ui()
        self._setup_tray()

    def initialize(self):
        """Initialize storage and start engine"""
        try:
            logging.info("Starting initialization sequence...")
            if self.engine:
                # Start engine synchronously
                self.update_status()
                logging.info("Activity tracking task started successfully")
                return True
            else:
                logging.error("Engine not properly initialized")
                return False
        except Exception as e:
            logging.error(f"Failed to initialize: {e}")
            if hasattr(self, 'tray_icon'):
                self.tray_icon.showMessage(
                    "ChronoFlow Error",
                    f"Failed to initialize: {e}",
                    QSystemTrayIcon.MessageIcon.Critical,
                    3000
                )
            return False
        
    def _init_core_components(self):
        self.tracker = WindowsActivityTracker()
        self.classifier = ActivityClassifier()
        self.storage = SQLiteActivityStorage("activity.db")
        self.engine = Engine(self.tracker, self.classifier, self.storage)
        self.engine.start()
        
    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget with more generous spacing
        tabs = QTabWidget()
        layout.addWidget(tabs)
        layout.setContentsMargins(UIConstants.MARGIN, UIConstants.MARGIN, UIConstants.MARGIN, UIConstants.MARGIN)
        layout.setSpacing(UIConstants.SPACING)
        
        # Dashboard tab
        dashboard_widget = DashboardTab(self.engine)
        tabs.addTab(dashboard_widget, "Dashboard")
        
        # Rules tab
        rules_widget = RulesTab(self.engine)
        tabs.addTab(rules_widget, "Rules")
        
        # Privacy tab
        privacy_widget = PrivacyTab(self.engine)
        tabs.addTab(privacy_widget, "Privacy")
        
    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))
        
        # Create tray menu
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        status_action = QAction("Status: Stopped", self)
        status_action.setEnabled(False)
        quit_action = QAction("Exit", self)
        
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quit_application)
        
        self.status_action = status_action  # Store reference
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(status_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        
        self.tray_icon.show()

    def update_status(self):
        """Update tray icon status text"""
        if self.engine:
            status = "Running" if self.engine.get_status() else "Stopped"
            self.status_action.setText(f"Status: {status}")
        
    @pyqtSlot()
    def quit_application(self):
        try:
            self.engine.stop()
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")
        finally:
            QApplication.quit()

    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        if a0 is not None:
            a0.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "ChronoFlow",
                "Application minimized to tray. Right-click the tray icon to show or exit.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
        
def main():
    app = QApplication(sys.argv)
    
    window = ChronoFlowGUI()
    if window.initialize():
        window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
