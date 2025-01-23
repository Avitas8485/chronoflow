from abc import ABC, abstractmethod
import logging
from typing import Tuple



        

class BaseActivityTracker(ABC):
    @abstractmethod
    def get_active_window_info(self) -> Tuple[str, str]:
        """Get the active window title and application name."""
        pass
        
    @abstractmethod
    def get_idle_time(self) -> float:
        """Get the idle time in seconds."""
        pass
    
    

class WindowsActivityTracker(BaseActivityTracker):
    def get_active_window_info(self) -> Tuple[str, str]:
        try:
            import win32gui
            import win32process
            import psutil
            window = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(window)
            
            # Get process ID and name
            _, pid = win32process.GetWindowThreadProcessId(window)
            app_name = psutil.Process(pid).name()
            
            return app_name, window_title
        except Exception as e:
            logging.error(f"Error getting Windows window info: {e}")
            return "unknown", "unknown"
        
    def get_idle_time(self) -> float:
        try:
            import win32api
            last_input = win32api.GetLastInputInfo()
            current_tick = win32api.GetTickCount()
            idle_time = (current_tick - last_input) / 1000 # seconds
            return idle_time
        except Exception as e:
            logging.error(f"Error getting idle time: {e}")
            return 0.0
        
class LinuxActivityTracker(BaseActivityTracker):
    def __init__(self):
        import Xlib
        from Xlib import display
        from Xlib.protocol.event import FocusIn, FocusOut

        self.display = display.Display()
        self.root = self.display.screen().root
        
    def get_active_window_info(self) -> Tuple[str, str]:
        try:
            import psutil
            window = self.display.get_input_focus().focus
            window_name = window.get_wm_name()
            
            # Get process name using _NET_WM_PID
            pid = window.get_full_property(
                self.display.intern_atom('_NET_WM_PID'),
                0
            )
            
            if pid:
                process = psutil.Process(pid.value[0])
                app_name = process.name()
            else:
                app_name = "unknown"
                
            return app_name, window_name if window_name else "unknown"
        
        except Exception as e:
            logging.error(f"Error getting active window info: {e}")
            return "unknown", "unknown"
    
    def get_idle_time(self) -> float:
        try:
            # Use xprintidle if available
            import subprocess
            result = subprocess.run(['xprintidle'], capture_output=True, text=True)
            return float(result.stdout.strip()) / 1000.0  # Convert to seconds
        except Exception as e:
            logging.error(f"Error getting Linux idle time: {e}")
            return 0.0
        
        
