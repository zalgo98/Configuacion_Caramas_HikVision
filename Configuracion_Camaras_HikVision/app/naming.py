from urllib.parse import quote
from app.settings import USERNAME, PASSWORD, RTSP_PORT, RTSP_CHANNEL




def build_osd_from_ip(ip: str) -> str:
    parts = ip.strip().split(".")
    if len(parts) != 4:
        raise ValueError(f"IP no válida: {ip}")
    return f"{parts[1]}.{parts[2]}.{parts[3]}"


def build_camera_name(operacion: str, poste: str, ip: str, vertical: bool) -> str:
    parts = ip.strip().split(".")
    if len(parts) != 4:
        raise ValueError(f"IP no válida: {ip}")

    last_octet = parts[3]
    suffix = "V" if vertical else ""
    return f"G{operacion}-P{poste}-{last_octet}{suffix}"


def build_rtsp_url(ip: str) -> str:
    user = quote(USERNAME)
    pwd = quote(PASSWORD)
    return f"rtsp://{user}:{pwd}@{ip}:{RTSP_PORT}/Streaming/Channels/{RTSP_CHANNEL}"
