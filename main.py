import sys
import csv
import os
from datetime import datetime
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QPushButton,
    QFileDialog, QLineEdit, QFormLayout, QMessageBox, QLabel
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap
from psutil import net_io_counters

from components import SystemMonitor
from db import SQLiteHandler


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


class SystemInfoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        SQLiteHandler.init_db()
        self.setWindowTitle("Менеджер ресурсов")
        self.setGeometry(300, 200, 900, 600)

        self.monitor = SystemMonitor()
        self.last_net = net_io_counters()
        self.logged_data = []
        self.live_mode = True
        self.hardware_info = {}

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(5000)

        self.init_ui()
        self.load_hardware_from_db()
        self.load_avatar()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.cpu_tab = SystemTab("Процессор", "Загрузка, %")
        self.mem_tab = SystemTab("Оперативная память", "Использование, %")
        self.gpu_tab = SystemTab("Видеокарта", "Загрузка, %")
        self.net_tab = SystemTab("Сеть", "Передача, КБ/с")
        self.settings_tab = self.create_settings_tab()
        self.hardware_tab = self.create_hardware_tab()
        self.profile_tab = self.create_profile_tab()

        self.tabs.addTab(self.cpu_tab, "Процессор")
        self.tabs.addTab(self.mem_tab, "ОЗУ")
        self.tabs.addTab(self.gpu_tab, "GPU")
        self.tabs.addTab(self.net_tab, "Сеть")
        self.tabs.addTab(self.settings_tab, "Настройки")
        self.tabs.addTab(self.hardware_tab, "Оборудование")
        self.tabs.addTab(self.profile_tab, "Профиль")

        self.export_button = QPushButton("Экспорт CSV")
        self.export_button.clicked.connect(self.export_csv)
        self.import_button = QPushButton("Импорт CSV")
        self.import_button.clicked.connect(self.import_csv)
        self.save_db_button = QPushButton("Сохранить в БД")
        self.save_db_button.clicked.connect(self.save_to_db)
        self.live_button = QPushButton("Live режим")
        self.live_button.clicked.connect(self.return_to_live)

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.addWidget(self.export_button)
        layout.addWidget(self.import_button)
        layout.addWidget(self.save_db_button)
        layout.addWidget(self.live_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def create_profile_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.avatar_label = QLabel()
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setFixedSize(200, 200)
        self.avatar_label.setStyleSheet("border: 2px dashed gray; border-radius: 10px;")

        self.upload_button = QPushButton("Выбрать аватарку")
        self.upload_button.clicked.connect(self.choose_avatar)

        layout.addWidget(self.avatar_label)
        layout.addWidget(self.upload_button, alignment=Qt.AlignmentFlag.AlignCenter)
        tab.setLayout(layout)
        return tab

    def choose_avatar(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выбрать изображение", "", "Изображения (*.png *.jpg *.jpeg *.bmp)"
        )
        if filename:
            self.save_avatar_path(filename)
            self.show_avatar(filename)

    def save_avatar_path(self, path):
        with open("avatar.txt", "w", encoding="utf-8") as f:
            f.write(path)

    def load_avatar(self):
        if os.path.exists("avatar.txt"):
            with open("avatar.txt", "r", encoding="utf-8") as f:
                path = f.read().strip()
            if os.path.exists(path):
                self.show_avatar(path)

    def show_avatar(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить изображение.")
            return
        scaled = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.avatar_label.setPixmap(scaled)
        self.avatar_label.setStyleSheet("border: none;")

    def save_hardware(self):
        cpu = self.cpu_name.text().strip()
        gpu = self.gpu_name.text().strip()
        ram = self.ram_size.text().strip()
        os_name = self.os_name.text().strip()
        if not (cpu and gpu and ram and os_name):
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return

        try:
            ram_value = float(ram)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Поле RAM должно быть числом!")
            return

        SQLiteHandler.insert_hardware(cpu, gpu, ram_value, os_name)

        self.hardware_info = {"cpu": cpu, "gpu": gpu, "ram": ram_value, "os": os_name}
        self.update_tab_titles()

        advice = self.analyze_hardware(self.hardware_info)

        QMessageBox.information(
            self,
            "Профиль сохранён",
            f"Данные оборудования успешно сохранены!\n\n{advice}"
        )

    def analyze_hardware(self, info):
        ram = info.get("ram", 0)
        cpu = info.get("cpu", "").lower()
        gpu = info.get("gpu", "").lower()
        os_name = info.get("os", "").lower()

        messages = []

        if ram < 8:
            messages.append("Рекомендуется увеличить объём ОЗУ — меньше 8 ГБ может быть недостаточно.")
        elif ram < 16:
            messages.append("ОЗУ на уровне нормы, но для тяжёлых задач стоит рассмотреть 16+ ГБ.")
        else:
            messages.append("Отлично! Объём ОЗУ достаточен для большинства задач.")

        if "celeron" in cpu or "pentium" in cpu:
            messages.append("Ваш процессор начального уровня — производительность может быть ограничена.")
        elif "i5" in cpu or "ryzen 5" in cpu:
            messages.append("Хороший баланс мощности и эффективности.")
        elif "i7" in cpu or "ryzen 7" in cpu:
            messages.append("Мощный процессор — подходит для игр и работы.")

        if "gtx" in gpu or "rtx" in gpu or "radeon" in gpu:
            messages.append("Современная видеокарта подходит для большинства задач.")
        elif gpu:
            messages.append("Видеокарта не определена как игровая — возможны ограничения.")
        else:
            messages.append("GPU не указана.")

        if "win" in os_name:
            messages.append("Используется Windows — большинство приложений будет совместимо.")
        elif "linux" in os_name:
            messages.append("Linux — отличная стабильность и безопасность.")
        elif "mac" in os_name:
            messages.append("macOS — надёжная система, но ограниченная совместимость.")

        return "\n".join(messages)

    def create_settings_tab(self):
        tab = QWidget()
        layout = QFormLayout()
        self.setting_name = QLineEdit()
        self.setting_value = QLineEdit()
        save_button = QPushButton("Сохранить настройку")
        save_button.clicked.connect(self.save_setting)
        layout.addRow("Название:", self.setting_name)
        layout.addRow("Значение:", self.setting_value)
        layout.addRow(save_button)
        tab.setLayout(layout)
        return tab

    def create_hardware_tab(self):
        tab = QWidget()
        layout = QFormLayout()
        self.cpu_name = QLineEdit()
        self.gpu_name = QLineEdit()
        self.ram_size = QLineEdit()
        self.os_name = QLineEdit()
        save_button = QPushButton("Сохранить оборудование")
        save_button.clicked.connect(self.save_hardware)
        layout.addRow("CPU:", self.cpu_name)
        layout.addRow("GPU:", self.gpu_name)
        layout.addRow("RAM (ГБ):", self.ram_size)
        layout.addRow("ОС:", self.os_name)
        layout.addRow(save_button)
        tab.setLayout(layout)
        return tab

    def save_setting(self):
        name = self.setting_name.text().strip()
        value = self.setting_value.text().strip()
        if not name or not value:
            QMessageBox.warning(self, "Ошибка", "Введите имя и значение настройки!")
            return
        SQLiteHandler.insert_setting(name, value)
        QMessageBox.information(self, "OK", "Настройка сохранена!")

    def load_hardware_from_db(self):
        hw_list = SQLiteHandler.fetch_hardware()
        if not hw_list:
            return
        latest = hw_list[-1]
        self.hardware_info = latest
        self.cpu_name.setText(latest["cpu"])
        self.gpu_name.setText(latest["gpu"])
        self.ram_size.setText(str(latest["ram"]))
        self.os_name.setText(latest["os"])
        self.update_tab_titles()

    def update_tab_titles(self):
        cpu_title = f"Процессор ({self.hardware_info.get('cpu', '')})" if self.hardware_info.get("cpu") else "Процессор"
        gpu_title = f"Видеокарта ({self.hardware_info.get('gpu', '')})" if self.hardware_info.get(
            "gpu") else "Видеокарта"
        self.cpu_tab.plot.ax.set_title(cpu_title)
        self.gpu_tab.plot.ax.set_title(gpu_title)
        self.tabs.setTabText(0, cpu_title)
        self.tabs.setTabText(2, gpu_title)
        self.cpu_tab.plot.canvas.draw_idle()
        self.gpu_tab.plot.canvas.draw_idle()

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
            with open(filename, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["time", "cpu", "memory", "gpu", "network_kb"])
                writer.writeheader()
                writer.writerows(self.logged_data)

    def import_csv(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Открыть CSV", "", "CSV Files (*.csv)")
        if not filename:
            return

        imported_data = []
        with open(filename, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    imported_data.append({
                        "time": row["time"],
                        "cpu": float(row["cpu"]),
                        "memory": float(row["memory"]),
                        "gpu": float(row["gpu"]),
                        "network_kb": float(row["network_kb"])
                    })
                except ValueError as e:
                    QMessageBox.warning(self, "Ошибка CSV", f"Некорректные данные в CSV: {e}")
                    return

        if not imported_data:
            QMessageBox.warning(self, "Ошибка CSV", "Файл CSV пустой или некорректный")
            return

        self.live_mode = False
        self.logged_data = imported_data

        self.cpu_tab.set_data([row["cpu"] for row in self.logged_data])
        self.mem_tab.set_data([row["memory"] for row in self.logged_data])
        self.gpu_tab.set_data([row["gpu"] for row in self.logged_data])
        self.net_tab.set_data([row["network_kb"] for row in self.logged_data])

    def save_to_db(self):
        if not self.logged_data:
            return
        for row in self.logged_data:
            SQLiteHandler.insert_usage(row)
        QMessageBox.information(self, "OK", "Данные мониторинга сохранены в БД!")

    def return_to_live(self):
        self.live_mode = True
        self.logged_data = []

        self.cpu_tab.set_data([])
        self.mem_tab.set_data([])
        self.gpu_tab.set_data([])
        self.net_tab.set_data([])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SystemInfoApp()
    window.show()
    sys.exit(app.exec())
