from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QPainter, QColor, QPen
from datetime import datetime, timedelta
from engine.engine import Engine

class ProductivityGraph(QChartView):
    def __init__(self, engine: Engine):
        chart = QChart()
        super().__init__(chart)
        self._chart = chart
        self.engine = engine
        self.series = QLineSeries()
        
        self._setup_chart()
        
    def _setup_chart(self):
        # Configure chart
        self._chart.addSeries(self.series)
        self._chart.setTitle("Productivity Over Time")
        self._chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        # Setup axes
        self.date_axis = QDateTimeAxis()
        self.date_axis.setFormat("hh:mm")
        self.date_axis.setTitleText("Time")
        
        self.value_axis = QValueAxis()
        self.value_axis.setRange(0, 100)
        self.value_axis.setTitleText("Productivity Score")
        
        self._chart.addAxis(self.date_axis, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(self.value_axis, Qt.AlignmentFlag.AlignLeft)
        
        self.series.attachAxis(self.date_axis)
        self.series.attachAxis(self.value_axis)
        
        # Style
        self._chart.setBackgroundVisible(False)
        self.series.setPen(QPen(QColor("#2196F3"), 2))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
    def update_data(self, hours_back: int = 8):
        self.series.clear()
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)
        current = start_time
        
        # Assume engine.get_productivity_scores returns List[Tuple[datetime, float]]
        scores = self.engine.get_productivity_scores(start_time, end_time)
        
        for timestamp, score in scores:
            qt_time = QDateTime.fromSecsSinceEpoch(int(timestamp.timestamp()))
            self.series.append(qt_time.toMSecsSinceEpoch(), score)
            
        self.date_axis.setRange(
            QDateTime.fromSecsSinceEpoch(int(start_time.timestamp())),
            QDateTime.fromSecsSinceEpoch(int(end_time.timestamp()))
        )