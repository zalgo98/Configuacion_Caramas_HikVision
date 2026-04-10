import sys
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception:
        QMessageBox.critical(None, "Error crítico", traceback.format_exc())


if __name__ == "__main__":
    main()
