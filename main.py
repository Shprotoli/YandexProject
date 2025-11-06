import sys
import csv
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime

from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QPushButton, QFileDialog
from PyQt6.QtCore import QTimer
from psutil import net_io_counters

from components import SystemMonitor


class LivePlot(QWidget):
    def __init__(self, title, ylabel, fixed_ylim=False):
        super().__init__()
        self.data = [0] * 60
        self.fixed_ylim = fixed_ylim
        self.fig = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title(title)
        if fixed_ylim:
            self.ax.set_ylim(0, 100)
        self.ax.set_ylabel(ylabel)
        self.line, = self.ax.plot(self.data, color="tab:blue")
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def update_plot(self, new_value):
        self.data = self.data[1:] + [new_value]
        self.line.set_ydata(self.data)
        if not self.fixed_ylim:
            self.ax.set_ylim(0, max(max(self.data) * 1.2, 1))
        self.canvas.draw_idle()

    def set_data(self, values):
        self.data = values[-60:] if len(values) >= 60 else [0] * (60 - len(values)) + values
        self.line.set_ydata(self.data)
        if not self.fixed_ylim:
            self.ax.set_ylim(0, max(max(self.data) * 1.2, 1))
        self.canvas.draw_idle()


class SystemTab(QWidget):
    def __init__(self, title, ylabel):
        super().__init__()
        self.plot = LivePlot(title, ylabel)
        layout = QVBoxLayout()
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def update(self, value):
        self.plot.update_plot(value)

    def set_data(self, values):
        self.plot.set_data(values)


class CSVHandler:
    @staticmethod
    def export(filename, data):
        with open(filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["time", "cpu", "memory", "gpu", "network_kb"])
            writer.writeheader()
            for row in data:
                writer.writerow(row)

    @staticmethod
    def import_file(filename):
        imported_data = []
        with open(filename, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                imported_data.append({
                    "time": row["time"],
                    "cpu": float(row["cpu"]),
                    "memory": float(row["memory"]),
                    "gpu": float(row["gpu"]),
                    "network_kb": float(row["network_kb"])
                })
        return imported_data


class SystemInfoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Менеджер ресурсов")
        self.setGeometry(300, 200, 800, 500)
        self.monitor = SystemMonitor()
        self.last_net = net_io_counters()
        self.logged_data = []
        self.live_mode = True
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(5000)
        self.init_ui()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.cpu_tab = SystemTab("Процессор", "Загрузка, %")
        self.mem_tab = SystemTab("Оперативная память", "Использование, %")
        self.gpu_tab = SystemTab("Видеокарта", "Загрузка, %")
        self.net_tab = SystemTab("Сеть", "Передача, КБ/с")

        self.tabs.addTab(self.cpu_tab, "Процессор")
        self.tabs.addTab(self.mem_tab, "Оперативная память")
        self.tabs.addTab(self.gpu_tab, "Видеокарта")
        self.tabs.addTab(self.net_tab, "Сеть")

        self.export_button = QPushButton("Экспорт CSV")
        self.export_button.clicked.connect(self.export_csv)
        self.import_button = QPushButton("Загрузить CSV")
        self.import_button.clicked.connect(self.import_csv)
        self.live_button = QPushButton("Возврат к live")
        self.live_button.clicked.connect(self.return_to_live)

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.addWidget(self.export_button)
        layout.addWidget(self.import_button)
        layout.addWidget(self.live_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def update_stats(self):
        if not self.live_mode:
            return

        usage = self.monitor.get_all_usage()
        cpu_percent = usage["cpu"]["usage_percent"]
        mem_percent = usage["memory"]["percent"]
        gpu_load = self.get_gpu_load(usage["gpu"])
        net_total = self.get_network_usage()

        self.cpu_tab.update(cpu_percent)
        self.mem_tab.update(mem_percent)
        self.gpu_tab.update(gpu_load)
        self.net_tab.update(net_total)

        self.logged_data.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cpu": cpu_percent,
            "memory": mem_percent,
            "gpu": gpu_load,
            "network_kb": net_total
        })

    def get_gpu_load(self, gpu_usage):
        if isinstance(gpu_usage, list) and gpu_usage:
            return gpu_usage[0].get("load_percent", 0)
        if isinstance(gpu_usage, dict):
            return gpu_usage.get("load_percent", 0)
        return 0

    def get_network_usage(self):
        net = net_io_counters()
        sent_kb = (net.bytes_sent - self.last_net.bytes_sent) / 1024
        recv_kb = (net.bytes_recv - self.last_net.bytes_recv) / 1024
        self.last_net = net
        return sent_kb + recv_kb

    def export_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Сохранить CSV", "", "CSV Files (*.csv)")
        if filename:
            CSVHandler.export(filename, self.logged_data)

    def import_csv(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Открыть CSV", "", "CSV Files (*.csv)")
        if not filename:
            return
        imported_data = CSVHandler.import_file(filename)
        self.live_mode = False
        self.logged_data = imported_data
        self.cpu_tab.set_data([d["cpu"] for d in imported_data])
        self.mem_tab.set_data([d["memory"] for d in imported_data])
        self.gpu_tab.set_data([d["gpu"] for d in imported_data])
        self.net_tab.set_data([d["network_kb"] for d in imported_data])

    def return_to_live(self):
        self.live_mode = True


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SystemInfoApp()
    window.show()
    sys.exit(app.exec())
