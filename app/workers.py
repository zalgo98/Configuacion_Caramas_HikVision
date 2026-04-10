import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from app.hikvision_api import (
    get_device_info,
    get_osd_text,
    set_osd_text,
    set_device_name,
    set_time_zone_only,
    set_ntp_only,
    set_platform_access,
    set_audio_enabled_on_stream,
    set_recording_track_24x7,
    set_snapshot_capture_config,
)
from app.positions import POSITIONS
from app.naming import build_osd_from_ip, build_camera_name, build_rtsp_url

from PySide6.QtCore import QObject, Signal, Slot
from app.discovery import get_network_prefix, scan_ip_range
from app.router import get_ethernet_gateway
from app.models import CameraInfo
from app.settings import (
    SCAN_MAX_WORKERS,
    CAMERA_MAX_WORKERS, AUDIO_STREAMS, RECORD_TRACKS,
)

CAMERAS_PER_POSTE = 6


class DiscoveryWorker(QObject):
    log      = Signal(str)
    progress = Signal(int)
    finished = Signal(list)
    error    = Signal(str)

    @Slot()
    def run(self):
        try:
            self.progress.emit(5)
            self.log.emit("Detectando IP del router (gateway)...")

            gateway_ip = get_ethernet_gateway()
            if not gateway_ip:
                raise RuntimeError(
                    "No se pudo detectar la IP del router. "
                    "Comprueba que el cable Ethernet está conectado."
                )
            self.log.emit(f"Router detectado: {gateway_ip}")

            self.progress.emit(15)
            network_prefix = get_network_prefix(gateway_ip)
            gateway_last   = int(gateway_ip.split(".")[-1])
            scan_start     = gateway_last + 1
            scan_end       = gateway_last + CAMERAS_PER_POSTE

            self.log.emit(f"Red detectada: {network_prefix}.x")
            self.progress.emit(25)
            self.log.emit(
                f"Escaneando las {CAMERAS_PER_POSTE} IPs siguientes al router "
                f"({network_prefix}.{scan_start} – {network_prefix}.{scan_end})..."
            )

            found_ips = scan_ip_range(
                network_prefix,
                start=scan_start,
                end=scan_end,
                max_workers=SCAN_MAX_WORKERS,
            )

            self.log.emit(f"IPs activas encontradas: {len(found_ips)}")
            self.progress.emit(40)

            cameras = []
            total   = max(len(found_ips), 1)
            lock    = Lock()
            done    = [0]

            def query_camera(ip):
                """Consulta y actualiza OSD de una cámara. Devuelve (CameraInfo|None, [logs])."""
                lines = []

                device_info = get_device_info(ip)
                if not device_info:
                    lines.append(f" ✗ {ip}: no es Hikvision o no responde por ISAPI")
                    return None, lines

                expected_osd = build_osd_from_ip(ip)
                current_osd  = get_osd_text(ip)

                if current_osd is None:
                    lines.append(f" ⚠ {ip}: no se pudo leer OSD")
                    current_osd = ""

                osd_ok = current_osd.strip() == expected_osd.strip()

                if osd_ok:
                    lines.append(f" ✓ {ip}: OSD correcto ({current_osd})")
                else:
                    lines.append(
                        f" ⚠ {ip}: OSD distinto — actual='{current_osd}' esperado='{expected_osd}'"
                    )
                    ok, msg = set_osd_text(ip, expected_osd)
                    if ok:
                        confirmed = get_osd_text(ip)
                        current_osd = confirmed if confirmed is not None else expected_osd
                        osd_ok = current_osd.strip() == expected_osd.strip()
                        lines.append(f" ✓ {ip}: OSD actualizado → {current_osd}")
                    else:
                        lines.append(f" ✗ {ip}: error actualizando OSD → {msg}")

                camera = CameraInfo(
                    ip=ip,
                    reachable=True,
                    serial=device_info.get("serial_number", ""),
                    current_name=device_info.get("device_name", ""),
                    osd_text=current_osd,
                    expected_osd=expected_osd,
                    osd_ok=osd_ok,
                    rtsp_url=build_rtsp_url(ip),
                )
                return camera, lines

            workers = min(CAMERA_MAX_WORKERS, len(found_ips)) if found_ips else 1
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_map = {executor.submit(query_camera, ip): ip for ip in found_ips}

                for future in as_completed(future_map):
                    ip = future_map[future]
                    self.log.emit(f"Consultando {ip}...")
                    try:
                        camera, lines = future.result()
                        for line in lines:
                            self.log.emit(line)
                        if camera is not None:
                            with lock:
                                cameras.append(camera)
                    except Exception:
                        self.log.emit(f" ✗ {ip}: excepción inesperada\n{traceback.format_exc()}")

                    with lock:
                        done[0] += 1
                        self.progress.emit(min(40 + int(done[0] / total * 60), 100))

            cameras.sort(key=lambda c: list(map(int, c.ip.split("."))))

            self.progress.emit(100)
            self.log.emit(f"Cámaras Hikvision detectadas: {len(cameras)}")
            self.finished.emit(cameras)

        except Exception:
            self.error.emit(traceback.format_exc())


class FinalConfigWorker(QObject):
    log      = Signal(str)
    progress = Signal(int)
    finished = Signal()
    error    = Signal(str)

    def __init__(self, operacion: str, poste: str, assignments: dict):
        super().__init__()
        self.operacion   = operacion
        self.poste       = poste
        self.assignments = assignments

    @Slot()
    def run(self):
        try:
            total = max(len(self.assignments), 1)
            lock  = Lock()
            done  = [0]

            def configure_camera(position_key: str, ip: str) -> list[str]:
                """Aplica toda la configuración final a una cámara. Devuelve lista de logs."""
                lines    = []
                vertical = POSITIONS[position_key]["vertical"]
                final_name = build_camera_name(self.operacion, self.poste, ip, vertical)

                lines.append(f"── Configurando {ip} ──")
                lines.append(f"   Nombre final: {final_name}")

                # OSD (últimos 3 octetos de la IP)
                expected_osd = build_osd_from_ip(ip)
                current_osd  = get_osd_text(ip)
                if current_osd is None:
                    lines.append(f"   OSD:           ⚠ no se pudo leer")
                elif current_osd.strip() == expected_osd.strip():
                    lines.append(f"   OSD:           ✓ ({current_osd})")
                else:
                    ok_osd, msg_osd = set_osd_text(ip, expected_osd)
                    if ok_osd:
                        lines.append(f"   OSD:           ✓ actualizado → {expected_osd}")
                    else:
                        lines.append(f"   OSD:           ✗ → {msg_osd}")

                # Nombre del dispositivo
                ok, msg = set_device_name(ip, final_name)
                lines.append(f"   Nombre:        {'✓' if ok else '✗'}" + ("" if ok else f" → {msg}"))

                # Zona horaria y NTP (independientes del stream)
                ok, msg = set_time_zone_only(ip)
                lines.append(f"   Zona horaria:  {'✓' if ok else '✗'}" + ("" if ok else f" → {msg}"))

                ok, msg = set_ntp_only(ip)
                lines.append(f"   NTP:           {'✓' if ok else '✗'}" + ("" if ok else f" → {msg}"))

                ok, msg = set_platform_access(ip)
                lines.append(f"   Plataforma:    {'✓' if ok else '✗'}" + ("" if ok else f" → {msg}"))

                # Audio por stream
                for stream_id in AUDIO_STREAMS:
                    ok, msg = set_audio_enabled_on_stream(ip, stream_id)
                    lines.append(f"   Audio {stream_id}:   {'✓' if ok else '✗'}" + ("" if ok else f" → {msg}"))

                # Configuración de captura (snapshot)
                ok, msg = set_snapshot_capture_config(ip)
                lines.append(f"   Captura:       {'✓' if ok else '✗'}" + ("" if ok else f" → {msg}"))

                # Horarios de grabación
                for track_id in RECORD_TRACKS:
                    ok, msg = set_recording_track_24x7(ip, track_id)
                    lines.append(f"   Horario {track_id}:  {'✓' if ok else '✗'}" + ("" if ok else f" → {msg}"))

                return lines

            workers = min(CAMERA_MAX_WORKERS, len(self.assignments))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_map = {
                    executor.submit(configure_camera, pk, ip): (pk, ip)
                    for pk, ip in self.assignments.items()
                }

                for future in as_completed(future_map):
                    _, ip = future_map[future]
                    try:
                        for line in future.result():
                            self.log.emit(line)
                    except Exception:
                        self.log.emit(f"✗ ERROR en {ip}:\n{traceback.format_exc()}")

                    with lock:
                        done[0] += 1
                        self.progress.emit(int(done[0] / total * 100))

            self.log.emit("Configuración final terminada.")
            self.finished.emit()

        except Exception:
            self.error.emit(traceback.format_exc())
