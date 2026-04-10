from dataclasses import dataclass


@dataclass
class CameraInfo:
    ip: str
    reachable: bool = False
    serial: str = ""
    current_name: str = ""
    osd_text: str = ""
    expected_osd: str = ""
    osd_ok: bool = False
    rtsp_url: str = ""
