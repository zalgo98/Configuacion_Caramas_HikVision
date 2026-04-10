import os

# ── Credenciales de dispositivos (configurar con variables de entorno) ──────
USERNAME = os.getenv("CAMERA_USERNAME", "tu_Usuario")
PASSWORD = os.getenv("CAMERA_PASSWORD", "Tu_Contraseña")

# ── Credenciales del router (configurar con variables de entorno) ───────────
ROUTER_USERNAME = os.getenv("ROUTER_USERNAME", "tu_Usuario")
ROUTER_PASSWORD = os.getenv("ROUTER_PASSWORD", "Tu_Contraseña")

# ── Escaneo de red ───────────────────────────────────────────────────────────
SCAN_START = int(os.getenv("SCAN_START", "2"))
SCAN_END = int(os.getenv("SCAN_END", "20"))
SCAN_MAX_WORKERS = int(os.getenv("SCAN_MAX_WORKERS", "20"))

# Cámaras consultadas/configuradas en paralelo
CAMERA_MAX_WORKERS = int(os.getenv("CAMERA_MAX_WORKERS", "6"))

# ── Endpoints ISAPI ──────────────────────────────────────────────────────────
DEVICE_INFO_ENDPOINT = "/ISAPI/System/deviceInfo"
OSD_ENDPOINT = "/ISAPI/System/Video/inputs/channels/1"
AUDIO_ENDPOINT = "/ISAPI/System/Video/inputs/channels/1/audio"
TIME_ENDPOINT = "/ISAPI/System/time"
NTP_ENDPOINT = "/ISAPI/System/time/ntpServers/1"
DST_ENDPOINT = "/ISAPI/System/time/localTime"
PLATFORM_ENDPOINT = "/ISAPI/System/Network/EZVIZ"
SCHEDULE_ENDPOINT = "/ISAPI/ContentMgmt/record/tracks/101"
SNAPSHOT_ENDPOINT = "/ISAPI/Snapshot/channels/1"

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "3"))

# ── Streams y tracks ─────────────────────────────────────────────────────────
AUDIO_STREAMS = ["101", "102"]
RECORD_TRACKS = ["101", "103"]

# ── Plataforma ───────────────────────────────────────────────────────────────
PLATFORM_ENABLED = os.getenv("PLATFORM_ENABLED", "true")
PLATFORM_ADDRESSING_TYPE = os.getenv("PLATFORM_ADDRESSING_TYPE", "hostname")
PLATFORM_HOST = os.getenv("PLATFORM_HOST", "tu_host_plataforma")
PLATFORM_VERIFICATION_CODE = os.getenv("PLATFORM_VERIFICATION_CODE", "TU_CODIGO_VERIFICACION")

# ── Tiempo / NTP ─────────────────────────────────────────────────────────────
TIME_ZONE_ID = os.getenv("TIME_ZONE_ID", "CST-1:00:00DST01:00:00,M3.1.0/02:00:00,M10.5.0/03:00:00")
NTP_ENABLED = os.getenv("NTP_ENABLED", "true")
NTP_HOST = os.getenv("NTP_HOST", "pool.ntp.org")
NTP_PORT = os.getenv("NTP_PORT", "123")
NTP_INTERVAL = os.getenv("NTP_INTERVAL", "1440")

# ── RTSP ─────────────────────────────────────────────────────────────────────
RTSP_PORT = os.getenv("RTSP_PORT", "554")
RTSP_CHANNEL = os.getenv("RTSP_CHANNEL", "101")

# ── Configuración de captura (snapshot) ─────────────────────────────────────
SNAPSHOT_TIMING_ENABLED = os.getenv("SNAPSHOT_TIMING_ENABLED", "true")
SNAPSHOT_TIMING_SUPPORT_SCHEDULE = os.getenv("SNAPSHOT_TIMING_SUPPORT_SCHEDULE", "true")
SNAPSHOT_TIMING_CODEC = os.getenv("SNAPSHOT_TIMING_CODEC", "JPEG")
SNAPSHOT_TIMING_WIDTH = os.getenv("SNAPSHOT_TIMING_WIDTH", "2688")
SNAPSHOT_TIMING_HEIGHT = os.getenv("SNAPSHOT_TIMING_HEIGHT", "1520")
SNAPSHOT_TIMING_QUALITY = os.getenv("SNAPSHOT_TIMING_QUALITY", "80")
SNAPSHOT_TIMING_INTERVAL = os.getenv("SNAPSHOT_TIMING_INTERVAL", "3480000")

SNAPSHOT_EVENT_ENABLED = os.getenv("SNAPSHOT_EVENT_ENABLED", "true")
SNAPSHOT_EVENT_SUPPORT_SCHEDULE = os.getenv("SNAPSHOT_EVENT_SUPPORT_SCHEDULE", "false")
SNAPSHOT_EVENT_CODEC = os.getenv("SNAPSHOT_EVENT_CODEC", "JPEG")
SNAPSHOT_EVENT_WIDTH = os.getenv("SNAPSHOT_EVENT_WIDTH", "2688")
SNAPSHOT_EVENT_HEIGHT = os.getenv("SNAPSHOT_EVENT_HEIGHT", "1520")
SNAPSHOT_EVENT_QUALITY = os.getenv("SNAPSHOT_EVENT_QUALITY", "80")
SNAPSHOT_EVENT_INTERVAL = os.getenv("SNAPSHOT_EVENT_INTERVAL", "60000")
SNAPSHOT_EVENT_NUMBER = os.getenv("SNAPSHOT_EVENT_NUMBER", "1")
