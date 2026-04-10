import socket
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def get_network_prefix(local_ip: str) -> str:
    parts = local_ip.split(".")
    if len(parts) != 4:
        raise ValueError(f"IP local no válida: {local_ip}")
    return ".".join(parts[:3])


def is_port_open(ip: str, port: int = 80, timeout: float = 0.5) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((ip, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def scan_ip_range(network_prefix: str, start: int = 2, end: int = 20, max_workers: int = 20):
    ips = [f"{network_prefix}.{i}" for i in range(start, end + 1)]
    found = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(is_port_open, ip): ip for ip in ips}

        for future in as_completed(future_map):
            ip = future_map[future]
            try:
                if future.result():
                    found.append(ip)
            except Exception:
                pass

    return sorted(found, key=lambda x: list(map(int, x.split("."))))
