from __future__ import annotations

import socket
import sys
import threading
import time

from src.port_scanner import PortScanner
from src.process_manager import ProcessManager


def main() -> int:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    stop = threading.Event()

    def loop() -> None:
        server.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = server.accept()
                conn.close()
            except socket.timeout:
                pass
            except OSError:
                break

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    time.sleep(0.1)
    try:
        rows = PortScanner(ProcessManager()).scan([], collapse_duplicate_bindings=True)
        match = [r for r in rows if r.port == port]
        if not match:
            print(f"FAIL: temporary localhost listener {port} was not detected")
            return 1
        row = match[0]
        print("PASS")
        print(f"Port: {row.port}")
        print(f"Endpoint: {row.endpoint}")
        print(f"Process: {row.process_name}")
        print(f"PID: {row.pid}")
        print(f"Total listeners: {len(rows)}")
        return 0
    finally:
        stop.set()
        server.close()
        t.join(timeout=1)


if __name__ == "__main__":
    raise SystemExit(main())
