import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QLabel, QWidget


class SystemInfoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Менеджер ресурсов")
        self.setGeometry(300, 200, 500, 300)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_tab("Информация о процессоре"), "Процессор")
        self.tabs.addTab(self.create_tab("Информация об оперативной памяти"), "Оперативная память")
        self.tabs.addTab(self.create_tab("Информация о видеокарте"), "Видеокарта")
        self.tabs.addTab(self.create_tab("Информация о диске"), "Диск")
        self.tabs.addTab(self.create_tab("Информация о сети"), "Сеть")

        self.setCentralWidget(self.tabs)

    def create_tab(self, text):
        tab = QWidget()
        vbox = QVBoxLayout()
        label = QLabel(text)
        vbox.addWidget(label)
        tab.setLayout(vbox)
        return tab


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SystemInfoApp()
    window.show()
    sys.exit(app.exec())
