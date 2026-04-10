import sys
import traceback
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QTextEdit,
    QVBoxLayout, QHBoxLayout, QProgressBar, QMessageBox,
)
from PySide6.QtCore import Qt, QThread
from ui.assign_window import AssignWindow
from app.workers import DiscoveryWorker
from app.router import get_ethernet_gateway


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configurador de Cámaras")
        self.resize(700, 450)

        self.discovery_thread = None
        self.discovery_worker = None
        self.cameras          = []
        self.assign_window    = None
        self.gateway_ip       = ""

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("CONFIGURADOR DE CÁMARAS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Formulario operación / poste
        form = QHBoxLayout()
        form.addWidget(QLabel("Operación:"))
        self.op_input = QLineEdit()
        self.op_input.setPlaceholderText("Ej. 12")
        form.addWidget(self.op_input)
        form.addSpacing(20)
        form.addWidget(QLabel("Poste:"))
        self.poste_input = QLineEdit()
        self.poste_input.setPlaceholderText("Ej. 3")
        form.addWidget(self.poste_input)
        layout.addLayout(form)

        self.search_button = QPushButton("Buscar cámaras")
        self.search_button.clicked.connect(self._on_search_clicked)
        layout.addWidget(self.search_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

    # ── Búsqueda ─────────────────────────────────────────────────────────────

    def _on_search_clicked(self):
        operacion = self.op_input.text().strip()
        poste     = self.poste_input.text().strip()

        if not operacion.isdigit():
            QMessageBox.warning(self, "Validación", "La operación debe ser numérica.")
            return
        if not poste.isdigit():
            QMessageBox.warning(self, "Validación", "El poste debe ser numérico.")
            return

        self.search_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_box.clear()
        self.cameras = []
        self._log("Inicio de búsqueda de cámaras Hikvision...")

        self.discovery_thread = QThread()
        self.discovery_worker = DiscoveryWorker()
        self.discovery_worker.moveToThread(self.discovery_thread)

        self.discovery_thread.started.connect(self.discovery_worker.run)
        self.discovery_worker.log.connect(self._log)
        self.discovery_worker.progress.connect(self.progress_bar.setValue)
        self.discovery_worker.finished.connect(self._on_discovery_finished)
        self.discovery_worker.error.connect(self._on_discovery_error)

        self.discovery_worker.finished.connect(self.discovery_thread.quit)
        self.discovery_worker.error.connect(self.discovery_thread.quit)
        self.discovery_thread.finished.connect(self.discovery_thread.deleteLater)

        self.discovery_thread.start()

    def _on_discovery_finished(self, cameras: list):
        self.cameras = cameras
        self.search_button.setEnabled(True)
        self._log("Búsqueda terminada.")

        if not cameras:
            self._log("No se encontraron cámaras Hikvision válidas.")
            return

        self._log(f"Total cámaras detectadas: {len(cameras)}")
        for cam in cameras:
            estado = "✓" if cam.osd_ok else "✗"
            self._log(
                f"  {estado} IP={cam.ip} | Modelo={cam.serial or 'N/D'} "
                f"| OSD={cam.osd_text or 'N/D'} | Esperado={cam.expected_osd}"
            )

        if not self.gateway_ip:
            try:
                self.gateway_ip = get_ethernet_gateway() or ""
            except Exception:
                self.gateway_ip = ""

        try:
            self.assign_window = AssignWindow(
                cameras,
                self.op_input.text().strip(),
                self.poste_input.text().strip(),
                gateway_ip=self.gateway_ip,
            )
            self.assign_window.show()
            self._log("Ventana de asignación abierta correctamente.")
        except Exception:
            error_message = traceback.format_exc()
            self._log("ERROR al abrir la ventana de asignación:\n" + error_message)
            QMessageBox.critical(self, "Error al abrir asignación", error_message)

    def _on_discovery_error(self, error_message: str):
        self.search_button.setEnabled(True)
        QMessageBox.critical(self, "Error en búsqueda", error_message)
        self._log(f"ERROR:\n{error_message}")

    def _log(self, message: str):
        self.log_box.append(message)
