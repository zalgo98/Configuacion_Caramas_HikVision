import re
import requests
import xml.etree.ElementTree as ET
import subprocess
from pathlib import Path
from requests.auth import HTTPDigestAuth
from app.settings import (
    USERNAME,
    PASSWORD,
    DEVICE_INFO_ENDPOINT,
    OSD_ENDPOINT,
    REQUEST_TIMEOUT,
    TIME_ENDPOINT,
    NTP_ENDPOINT,
    PLATFORM_ENDPOINT,
    TIME_ZONE_ID,
    NTP_HOST,
    NTP_PORT,
    NTP_INTERVAL,
    PLATFORM_ENABLED,
    PLATFORM_ADDRESSING_TYPE,
    PLATFORM_HOST,
    PLATFORM_VERIFICATION_CODE,
    SNAPSHOT_ENDPOINT,
    SNAPSHOT_TIMING_ENABLED,
    SNAPSHOT_TIMING_SUPPORT_SCHEDULE,
    SNAPSHOT_TIMING_CODEC,
    SNAPSHOT_TIMING_WIDTH,
    SNAPSHOT_TIMING_HEIGHT,
    SNAPSHOT_TIMING_QUALITY,
    SNAPSHOT_TIMING_INTERVAL,
    SNAPSHOT_EVENT_ENABLED,
    SNAPSHOT_EVENT_SUPPORT_SCHEDULE,
    SNAPSHOT_EVENT_CODEC,
    SNAPSHOT_EVENT_WIDTH,
    SNAPSHOT_EVENT_HEIGHT,
    SNAPSHOT_EVENT_QUALITY,
    SNAPSHOT_EVENT_INTERVAL,
    SNAPSHOT_EVENT_NUMBER,
)

# ── Helpers HTTP ─────────────────────────────────────────────────────────────

def _auth():
    return HTTPDigestAuth(USERNAME, PASSWORD)


def _get(url: str):
    return requests.get(url, auth=_auth(), timeout=REQUEST_TIMEOUT)


def _put(url: str, data: str, content_type: str = "application/xml"):
    return requests.put(
        url,
        auth=_auth(),
        timeout=REQUEST_TIMEOUT,
        data=data.encode("utf-8"),
        headers={"Content-Type": content_type},
    )


def _get_text_xml(ip: str, endpoint: str) -> tuple[bool, str]:
    url = f"http://{ip}{endpoint}"
    try:
        r = _get(url)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text}"
        return True, r.text
    except requests.exceptions.Timeout:
        return False, "Timeout de conexión"
    except requests.exceptions.ConnectionError:
        return False, "No se pudo conectar con la cámara"
    except Exception as e:
        return False, str(e)


def _put_text_xml(ip: str, endpoint: str, xml_text: str) -> tuple[bool, str]:
    url = f"http://{ip}{endpoint}"
    try:
        r = _put(url, xml_text)
        if r.status_code not in (200, 201):
            return False, f"HTTP {r.status_code}: {r.text}"
        return True, "OK"
    except requests.exceptions.Timeout:
        return False, "Timeout al enviar configuración"
    except requests.exceptions.ConnectionError:
        return False, "No se pudo conectar con la cámara"
    except Exception as e:
        return False, str(e)


# ── Helpers XML ──────────────────────────────────────────────────────────────

def _find_text_anyns(root: ET.Element, tag_name: str) -> str | None:
    for elem in root.iter():
        if elem.tag.endswith(tag_name):
            return elem.text
    return None


def _replace_tag(xml_text: str, tag: str, value: str) -> tuple[str, int]:
    """Reemplaza el contenido de <tag> ignorando namespace. Devuelve (xml, count)."""
    pattern = rf"(<(?:\w+:)?{tag}>)(.*?)(</(?:\w+:)?{tag}>)"
    return re.subn(pattern, rf"\g<1>{value}\g<3>", xml_text, count=1, flags=re.DOTALL)


def _replace_tag_in_section(xml_text: str, section_tag: str, tag: str, value: str) -> tuple[str, int]:
    """Reemplaza <tag> dentro del primer bloque <section_tag>...</section_tag>."""
    section_pattern = rf"(<(?:\w+:)?{section_tag}>.*?</(?:\w+:)?{section_tag}>)"
    match = re.search(section_pattern, xml_text, flags=re.DOTALL)
    if not match:
        return xml_text, 0

    section_xml = match.group(1)
    new_section_xml, count = _replace_tag(section_xml, tag, value)
    if count == 0:
        return xml_text, 0

    start, end = match.span(1)
    return xml_text[:start] + new_section_xml + xml_text[end:], count


# ── API pública ──────────────────────────────────────────────────────────────

def get_device_info(ip: str) -> dict | None:
    try:
        r = _get(f"http://{ip}{DEVICE_INFO_ENDPOINT}")
        if r.status_code != 200:
            return None
        root = ET.fromstring(r.text)
        return {
            "model":         _find_text_anyns(root, "model") or "",
            "device_name":   _find_text_anyns(root, "deviceName") or "",
            "serial_number": _find_text_anyns(root, "serialNumber") or "",
        }
    except Exception:
        return None


def set_device_name(ip: str, new_name: str) -> tuple[bool, str]:
    ok, xml_text = _get_text_xml(ip, DEVICE_INFO_ENDPOINT)
    if not ok:
        return False, f"GET previo falló: {xml_text}"

    new_xml, count = _replace_tag(xml_text, "deviceName", new_name)
    if count == 0:
        return False, "No se encontró la etiqueta deviceName"
    if new_xml == xml_text:
        return True, "Nombre ya correcto"

    return _put_text_xml(ip, DEVICE_INFO_ENDPOINT, new_xml)


def get_osd_text(ip: str) -> str | None:
    try:
        r = _get(f"http://{ip}{OSD_ENDPOINT}")
        if r.status_code != 200:
            return None
        root = ET.fromstring(r.text)
        for tag in ["name", "channelName", "inputPort", "displayName", "videoInputName"]:
            value = _find_text_anyns(root, tag)
            if value:
                return value.strip()
        return ""
    except Exception:
        return None


def set_osd_text(ip: str, new_osd: str) -> tuple[bool, str]:
    ok, xml_text = _get_text_xml(ip, OSD_ENDPOINT)
    if not ok:
        return False, f"GET previo falló: {xml_text}"

    for tag in ["name", "channelName", "inputPort", "displayName", "videoInputName"]:
        new_xml, count = _replace_tag(xml_text, tag, new_osd)
        if count:
            if new_xml == xml_text:
                return True, "OSD ya correcto"
            return _put_text_xml(ip, OSD_ENDPOINT, new_xml)

    return False, "No se encontró etiqueta editable para OSD"


def set_time_zone_only(ip: str) -> tuple[bool, str]:
    ok, xml_text = _get_text_xml(ip, TIME_ENDPOINT)
    if not ok:
        return False, f"Leyendo time: {xml_text}"

    new_xml, count = _replace_tag(xml_text, "timeZone", TIME_ZONE_ID)
    if count == 0:
        return False, "No se encontró la etiqueta timeZone"
    if new_xml == xml_text:
        return True, "Zona horaria ya correcta"

    return _put_text_xml(ip, TIME_ENDPOINT, new_xml)


def set_ntp_only(ip: str) -> tuple[bool, str]:
    ok, xml_text = _get_text_xml(ip, NTP_ENDPOINT)
    if not ok:
        return False, f"Leyendo NTP: {xml_text}"

    original = xml_text
    for tag, value in [
        ("addressingFormatType", "hostname"),
        ("hostName",             NTP_HOST),
        ("portNo",               NTP_PORT),
    ]:
        xml_text, _ = _replace_tag(xml_text, tag, value)

    # synchronizeInterval o interval según modelo
    new_xml, count = _replace_tag(xml_text, "synchronizeInterval", NTP_INTERVAL)
    if count == 0:
        new_xml, _ = _replace_tag(xml_text, "interval", NTP_INTERVAL)
    xml_text = new_xml

    if xml_text == original:
        return True, "NTP ya correcto"

    return _put_text_xml(ip, NTP_ENDPOINT, xml_text)


def set_platform_access(ip: str) -> tuple[bool, str]:
    ok, xml_text = _get_text_xml(ip, PLATFORM_ENDPOINT)
    if not ok:
        return False, f"Leyendo plataforma: {xml_text}"

    original = xml_text
    missing = []
    for tag, value in [
        ("enabled",               PLATFORM_ENABLED),
        ("verificationCode",      PLATFORM_VERIFICATION_CODE),
        ("addressingFormatType",  PLATFORM_ADDRESSING_TYPE),
        ("hostName",              PLATFORM_HOST),
    ]:
        xml_text, count = _replace_tag(xml_text, tag, value)
        if count == 0:
            missing.append(tag)

    if missing:
        return False, f"Etiquetas no encontradas en plataforma: {', '.join(missing)}"
    if xml_text == original:
        return True, "Plataforma ya correcta"

    return _put_text_xml(ip, PLATFORM_ENDPOINT, xml_text)


def set_audio_enabled_on_stream(ip: str, stream_id: str) -> tuple[bool, str]:
    endpoint = f"/ISAPI/Streaming/channels/{stream_id}"
    ok, xml_text = _get_text_xml(ip, endpoint)
    if not ok:
        return False, f"GET canal {stream_id}: {xml_text}"

    try:
        if re.search(r"(?s)<Audio>\s*<enabled>true</enabled>", xml_text):
            return True, f"Audio ya activo en {stream_id}"

        new_xml = re.sub(
            r"(?s)(<Audio>\s*<enabled>)false(</enabled>)",
            r"\1true\2",
            xml_text,
            count=1,
        )
        if new_xml == xml_text:
            return False, f"No se encontró bloque de audio en canal {stream_id}"

        return _put_text_xml(ip, endpoint, new_xml)
    except Exception as e:
        return False, str(e)


def set_recording_track_24x7(ip: str, track_id: str) -> tuple[bool, str]:
    script_path = Path(__file__).resolve().parent / "configure_record_track.ps1"
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", str(script_path),
                "-Ip",       ip,
                "-User",     USERNAME,
                "-Password", PASSWORD,
                "-Track",    str(track_id),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output = (result.stdout or "").strip()
        error  = (result.stderr or "").strip()

        if result.returncode == 0:
            return True, output or f"OK horario {track_id}"
        return False, output or error or f"Error PowerShell track {track_id}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout ejecutando PowerShell para track {track_id}"
    except Exception as e:
        return False, str(e)


def set_snapshot_capture_config(ip: str) -> tuple[bool, str]:
    ok, xml_text = _get_text_xml(ip, SNAPSHOT_ENDPOINT)
    if not ok:
        return False, f"Leyendo captura: {xml_text}"

    original = xml_text

    replacements = [
        ("timingCapture", "enabled", SNAPSHOT_TIMING_ENABLED),
        ("timingCapture", "supportSchedule", SNAPSHOT_TIMING_SUPPORT_SCHEDULE),
        ("timingCapture", "pictureCodecType", SNAPSHOT_TIMING_CODEC),
        ("timingCapture", "pictureWidth", SNAPSHOT_TIMING_WIDTH),
        ("timingCapture", "pictureHeight", SNAPSHOT_TIMING_HEIGHT),
        ("timingCapture", "quality", SNAPSHOT_TIMING_QUALITY),
        ("timingCapture", "captureInterval", SNAPSHOT_TIMING_INTERVAL),
        ("eventCapture", "enabled", SNAPSHOT_EVENT_ENABLED),
        ("eventCapture", "supportSchedule", SNAPSHOT_EVENT_SUPPORT_SCHEDULE),
        ("eventCapture", "pictureCodecType", SNAPSHOT_EVENT_CODEC),
        ("eventCapture", "pictureWidth", SNAPSHOT_EVENT_WIDTH),
        ("eventCapture", "pictureHeight", SNAPSHOT_EVENT_HEIGHT),
        ("eventCapture", "quality", SNAPSHOT_EVENT_QUALITY),
        ("eventCapture", "captureInterval", SNAPSHOT_EVENT_INTERVAL),
        ("eventCapture", "captureNumber", SNAPSHOT_EVENT_NUMBER),
    ]

    missing = []
    for section_tag, tag, value in replacements:
        xml_text, count = _replace_tag_in_section(xml_text, section_tag, tag, value)
        if count == 0:
            missing.append(f"{section_tag}.{tag}")

    if missing:
        return False, "Etiquetas no encontradas en captura: " + ", ".join(missing)
    if xml_text == original:
        return True, "Captura ya correcta"

    return _put_text_xml(ip, SNAPSHOT_ENDPOINT, xml_text)
