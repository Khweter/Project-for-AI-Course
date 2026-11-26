import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.splash import LoadingSplash


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Project for AI")

    window = MainWindow()
    splash = LoadingSplash()
    splash.finished.connect(window.show)
    splash.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
