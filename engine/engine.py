import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from queue import Queue, Empty
import time
import logging
import signal

from models.activity import ActivityCategory, ActivityHeatmap, TimeLog, ActivityMetrics, ActivityData
from tracker.activity_tracker import BaseActivityTracker
from classifier.classifier import ActivityClassifier
from storage.sqlite_storage import SQLiteActivityStorage
from storage.storage import ActivityStorage
from tracker.activity_session import ActivitySession

class Engine:
    def __init__(self, tracker: BaseActivityTracker, classifier: ActivityClassifier, 
                 storage: ActivityStorage, idle_threshold: float=300.0, sampling_interval: float=5.0):
        self.tracker = tracker
        self.classifier = classifier
        self.storage = storage
        self.idle_threshold = idle_threshold
        self.sampling_interval = sampling_interval
        self.current_activity = None
        self.activity_buffer = Queue()
        self.tracking_thread = None
        self.should_stop = threading.Event()
        self.session = ActivitySession()
        self.is_running = False

    def log_activity(self, time_log: TimeLog) -> None:
        if time_log.end_time <= time_log.start_time:
            raise ValueError("End time must be after start time")
        logging.info(f"Logging activity: {time_log}")
        self.storage.add_activity(time_log)
        
    def get_activity_heatmap(self, start_date: datetime, end_date: datetime, 
                            category: Optional[ActivityCategory] = None) -> ActivityHeatmap:
        return self.storage.get_heatmap(start_date, end_date, category)
    
    def get_activity_metrics(self, start_date: datetime, end_date: datetime, 
                           category: Optional[ActivityCategory] = None) -> ActivityMetrics:
        return self.storage.get_metrics(start_date, end_date, category)

    def _get_peak_hours(self, logs: List[TimeLog]) -> List[int]:
        hours = [0] * 24
        for log in logs:
            for i in range(log.start_time.hour, log.end_time.hour + 1):
                hours[i] += 1
        max_count = max(hours)
        return [i for i, count in enumerate(hours) if count == max_count]
    
    def detect_flow_states(self, minimum_duration: timedelta=timedelta(hours=2), 
                          category: Optional[ActivityCategory]=None) -> List[TimeLog]:
        return self.storage.get_flow_states(minimum_duration, category)

    def start(self):
        logging.info("Starting activity engine")
        
        if self.is_running:
            logging.warning("Activity tracking is already running")
            return
            
        self.should_stop.clear()
        self.is_running = True
        
        try:
            self.tracking_thread = threading.Thread(target=self._track_activity)
            self.tracking_thread.start()
        except Exception as e:
            self.is_running = False
            self.tracking_thread = None
            logging.error(f"Failed to start tracking: {e}")
            raise

    def stop(self):
        if not self.is_running:
            return

        logging.info("Stopping activity tracking")
        self.should_stop.set()
        self.is_running = False

        if self.tracking_thread:
            try:
                self.tracking_thread.join(timeout=5.0)
                if self.tracking_thread.is_alive():
                    logging.warning("Force stopping tracking thread")
            except Exception as e:
                logging.error(f"Error stopping tracking thread: {e}")
            finally:
                self.tracking_thread = None

    def _track_activity(self):
        try:
            logging.info("Activity tracking started")
            
            while not self.should_stop.is_set():
                try:
                    if not self.is_running:
                        break
                        
                    # Get current activity info
                    window_info = self.tracker.get_active_window_info()
                    idle_time = self.tracker.get_idle_time()
                    current_time = datetime.now()
                    app_name, window_title = window_info

                    # Classify activity
                    category, confidence = self.classifier.classify_activity(
                        app_name, window_title, current_time, idle_time
                    )
                    
                    # Create activity data
                    activity = ActivityData(
                        timestamp=current_time,
                        application=app_name,
                        window_title=window_title,
                        idle_time=idle_time,
                        category=category
                    )
                    
                    logging.debug(f"Current activity: {app_name} - {window_title}")
                    
                    # Update session and get time log if activity should be logged
                    time_log = self.session.update(activity)
                    
                    if time_log:
                        logging.info(f"New activity detected: {time_log.description}")
                        try:
                            if time_log.end_time <= time_log.start_time:
                                logging.error("Invalid time log: end time before start time")
                                continue
                                
                            if (time_log.end_time - time_log.start_time).total_seconds() < 1:
                                logging.error("Invalid time log: duration too short")
                                continue
                                
                            self.log_activity(time_log)
                            logging.info(f"Activity logged successfully: {time_log.description}")
                        except Exception as log_error:
                            logging.error(f"Failed to log activity: {log_error}")
                    
                    time.sleep(self.sampling_interval)
                    logging.info("Activity tracking loop")
                    print("Activity tracking loop")
                    
                except Exception as e:
                    logging.error(f"Error in activity tracking loop: {e}")
                    if not self.should_stop.is_set():
                        time.sleep(self.sampling_interval)
                    
        finally:
            self.is_running = False
            logging.info("Activity tracking stopped")

    def _process_activity(self, activity: ActivityData):
        if activity.idle_time >= self.idle_threshold:
            logging.info("Idle time detected")
            if self.current_activity:
                self._flush_current_activity()
            return
        
        if self.current_activity is None:
            self.current_activity = activity
        elif (activity.application != self.current_activity.application or
              activity.window_title != self.current_activity.window_title):
            self._flush_current_activity()
            self.current_activity = activity
            
    def _flush_current_activity(self):
        if not self.current_activity:
            return
        
        time_log = TimeLog(
            start_time=self.current_activity.timestamp,
            end_time=datetime.now(),
            category=self.current_activity.category or ActivityCategory.OTHER,
            description=f"[Auto] {self.current_activity.application}: {self.current_activity.window_title}",
            tags=["auto-tracked"]
        )
        self.activity_buffer.put(time_log)
        
        if self.activity_buffer.qsize() >= 10:
            self._process_activity_buffer()
            
    def _process_activity_buffer(self):
        while not self.activity_buffer.empty():
            try:
                time_log = self.activity_buffer.get_nowait()
                self.log_activity(time_log)
            except Empty:
                break
            except Exception as e:
                logging.error(f"Error processing activity buffer: {e}")

    def get_status(self) -> bool:
        """Returns True if engine is running"""
        return self.is_running
