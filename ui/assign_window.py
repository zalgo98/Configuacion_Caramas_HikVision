import os
import subprocess
import traceback

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QComboBox, QTextEdit, QMessageBox, QGroupBox, QProgressBar,
)
from PySide6.QtCore import QThread

from app.router import login_router, get_ethernet_gateway
from app.positions import POSITIONS
from app.naming import build_camera_name
from app.workers import FinalConfigWorker
from app.live_view import VideoPanel


class AssignWindow(QWidget):
    def __init__(self, cameras: list, operacion: str, poste: str, gateway_ip: str = ""):
        super().__init__()
        self.setWindowTitle("Asignación de cámaras")
        self.setMinimumSize(900, 600)

        self.cameras         = cameras
        self.operacion       = operacion
        self.poste           = poste
        self.gateway_ip      = gateway_ip        # ← IP del router para el documento
        self.position_combos = {}
        self.config_thread   = None
        self.config_worker   = None
        self.video_panels    = []
        self._last_assignments = {}

        self._build_ui()
        self._load_live_view()
        self.showMaximized()

    # ── Construcción de UI ───────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel(f"Asignación — Operación {self.operacion} / Poste {self.poste}")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(self._build_live_group())

        content = QHBoxLayout()
        content.addWidget(self._build_camera_list_group(), 1)
        content.addWidget(self._build_template_group(),    1)
        layout.addLayout(content)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setMinimumHeight(180)
        layout.addWidget(self.result_box, stretch=3)

        buttons = QHBoxLayout()
        btn_style = "min-height: 36px; font-size: 13px; padding: 4px 12px;"
        self.validate_button = QPushButton("Validar asignación")
        self.validate_button.setStyleSheet(btn_style)
        self.validate_button.clicked.connect(self.validate_assignments)
        buttons.addWidget(self.validate_button)

        self.apply_button = QPushButton("Aplicar configuración final")
        self.apply_button.setStyleSheet(btn_style)
        self.apply_button.clicked.connect(self.apply_final_configuration)
        buttons.addWidget(self.apply_button)

        self.router_button = QPushButton("Abrir router")
        self.router_button.setStyleSheet(btn_style)
        self.router_button.clicked.connect(self.open_router)
        buttons.addWidget(self.router_button)

        self.close_button = QPushButton("Cerrar")
        self.close_button.setStyleSheet(btn_style)
        self.close_button.clicked.connect(self.close)
        buttons.addWidget(self.close_button)

        layout.addWidget(self._wrap_buttons(buttons))

    def _wrap_buttons(self, buttons_layout: QHBoxLayout) -> QWidget:
        """Envuelve los botones en un widget con altura fija para que nunca queden ocultos."""
        from PySide6.QtWidgets import QWidget as _QWidget
        container = _QWidget()
        container.setFixedHeight(50)
        container.setLayout(buttons_layout)
        return container

    def _build_live_group(self):
        group  = QGroupBox("Vista en directo")
        layout = QGridLayout()
        self.video_panels = []
        for i in range(6):
            panel = VideoPanel(f"Cámara {i + 1}")
            self.video_panels.append(panel)
            layout.addWidget(panel, i // 3, i % 3)
        group.setLayout(layout)
        return group

    def _build_camera_list_group(self):
        group  = QGroupBox("Cámaras detectadas")
        layout = QVBoxLayout()
        for idx, cam in enumerate(self.cameras, start=1):
            text = (
                f"Cámara {idx}: IP={cam.ip} | "
                f"Modelo={cam.serial or 'N/D'} | "
                f"OSD={cam.osd_text or 'N/D'}"
            )
            layout.addWidget(QLabel(text))
        group.setLayout(layout)
        return group

    def _build_template_group(self):
        group  = QGroupBox("Plantilla")
        layout = QGridLayout()
        ordered = [
            "left_top", "left_mid", "left_bottom",
            "right_top", "right_mid", "right_bottom",
        ]
        for row, key in enumerate(ordered):
            info  = POSITIONS[key]
            combo = QComboBox()
            combo.addItem("", "")
            for cam in self.cameras:
                combo.addItem(cam.ip, cam.ip)
            combo.currentIndexChanged.connect(self._update_live_highlight)
            self.position_combos[key] = combo
            layout.addWidget(QLabel(info["label"]), row, 0)
            layout.addWidget(combo,                 row, 1)
        group.setLayout(layout)
        return group

    # ── Live view ────────────────────────────────────────────────────────────

    def _load_live_view(self):
        for i, cam in enumerate(self.cameras[:6]):
            self.video_panels[i].set_title(cam.ip)
            if cam.rtsp_url:
                self.video_panels[i].play(cam.rtsp_url, cam.ip)

    def _update_live_highlight(self):
        selected_ips = {
            combo.currentData()
            for combo in self.position_combos.values()
            if combo.currentData()
        }

        for panel in self.video_panels:
            if panel.ip in selected_ips:
                panel.setStyleSheet("border: 3px solid lime; background-color: black;")
            else:
                panel.setStyleSheet("border: none; background-color: black;")

        for key, combo in self.position_combos.items():
            ip = combo.currentData()
            if not ip:
                continue
            vertical   = POSITIONS[key]["vertical"]
            final_name = build_camera_name(self.operacion, self.poste, ip, vertical)
            for panel in self.video_panels:
                if panel.ip == ip:
                    panel.set_title(final_name)

    # ── Asignación ───────────────────────────────────────────────────────────

    def collect_assignments(self) -> dict | None:
        assigned   = {}
        used_ips   = []
        duplicates = []

        for key, combo in self.position_combos.items():
            ip = combo.currentData()
            if not ip:
                continue
            if ip in used_ips:
                duplicates.append(ip)
            used_ips.append(ip)
            assigned[key] = ip

        if duplicates:
            QMessageBox.warning(
                self, "Asignación inválida",
                f"Hay cámaras repetidas: {', '.join(sorted(set(duplicates)))}",
            )
            return None

        if not assigned:
            QMessageBox.information(self, "Asignación", "No has asignado ninguna cámara.")
            return None

        return assigned

    def validate_assignments(self):
        assigned = self.collect_assignments()
        if not assigned:
            return

        self.result_box.clear()
        self.result_box.append("Vista previa de asignación:\n")

        for key, ip in assigned.items():
            vertical   = POSITIONS[key]["vertical"]
            final_name = build_camera_name(self.operacion, self.poste, ip, vertical)
            self.result_box.append(f"── {POSITIONS[key]['label']}")
            self.result_box.append(f"   IP:           {ip}")
            self.result_box.append(f"   Lleva V:      {'Sí' if vertical else 'No'}")
            self.result_box.append(f"   Nombre final: {final_name}\n")

    # ── Configuración final ──────────────────────────────────────────────────

    def apply_final_configuration(self):
        assignments = self.collect_assignments()
        if not assignments:
            return

        reply = QMessageBox.question(
            self, "Confirmar",
            "Se va a aplicar la configuración final a las cámaras asignadas. ¿Continuar?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._last_assignments = assignments

        self.progress_bar.setValue(0)
        self.result_box.clear()
        self._set_buttons_enabled(False)

        self.config_thread = QThread()
        self.config_worker = FinalConfigWorker(self.operacion, self.poste, assignments)
        self.config_worker.moveToThread(self.config_thread)

        self.config_thread.started.connect(self.config_worker.run)
        self.config_worker.log.connect(self.result_box.append)
        self.config_worker.progress.connect(self.progress_bar.setValue)
        self.config_worker.finished.connect(self._on_config_finished)
        self.config_worker.error.connect(self._on_config_error)

        self.config_worker.finished.connect(self.config_thread.quit)
        self.config_worker.error.connect(self.config_thread.quit)
        self.config_thread.finished.connect(self.config_thread.deleteLater)

        self.config_thread.start()

    def _on_config_finished(self):
        self._set_buttons_enabled(True)
        QMessageBox.information(self, "Finalizado", "La configuración final ha terminado.")
        self._fill_document()

    def _fill_document(self):
        """Rellena la plantilla Word y la guarda en el Escritorio."""
        try:
            from app.hikvision_api import get_device_info
            from fill_document import fill_ip_document

            # Obtener IP del router (la que se pasó al construir la ventana,
            # o intentar detectarla de nuevo si no estaba disponible)
            ip_router = self.gateway_ip
            if not ip_router:
                try:
                    from app.router import get_ethernet_gateway
                    ip_router = get_ethernet_gateway() or ""
                except Exception:
                    ip_router = ""

            # Construir info de cada posición asignada
            assignments_info = {}
            for pos_key, ip in (self._last_assignments or {}).items():
                vertical   = POSITIONS[pos_key]["vertical"]
                final_name = build_camera_name(self.operacion, self.poste, ip, vertical)
                dev_info   = get_device_info(ip) or {}
                assignments_info[pos_key] = {
                    "ip":     ip,
                    "serial": dev_info.get("serial_number", ""),
                    "name":   final_name,
                }

            output = fill_ip_document(
                operacion=self.operacion,
                poste=self.poste,
                assignments_info=assignments_info,
                ip_router=ip_router,
            )

            QMessageBox.information(
                self, "Documento generado",
                f"El documento de asignación se ha guardado en:\n{output}",
            )
            self.result_box.append(f"\n✓ Documento guardado: {output}")

        except Exception as exc:
            self.result_box.append(f"\n✗ Error al generar el documento:\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Documento", f"No se pudo generar el documento:\n{exc}")

    def _on_config_error(self, error_message: str):
        self._set_buttons_enabled(True)
        QMessageBox.critical(self, "Error", error_message)
        self.result_box.append(f"ERROR:\n{error_message}")

    def _set_buttons_enabled(self, enabled: bool):
        self.validate_button.setEnabled(enabled)
        self.apply_button.setEnabled(enabled)

    # ── Router ───────────────────────────────────────────────────────────────

    def open_router(self):
        ok, msg = login_router()
        self.result_box.append(msg)
        if not ok:
            QMessageBox.warning(self, "Router", msg)

    # ── Cierre ───────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        for panel in self.video_panels:
            panel.stop()
        super().closeEvent(event)
