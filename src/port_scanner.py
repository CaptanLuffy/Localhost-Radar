"""Listening TCP port scanner."""
from __future__ import annotations

import logging
from typing import Iterable, List

import psutil

from .models import PortInfo, get_ghost_indicator
from .process_manager import ProcessManager

logger = logging.getLogger(__name__)


def _binding_group(address: str) -> str:
    """Collapse equivalent IPv4/IPv6 bindings for a cleaner UI."""
    if address in ("127.0.0.1", "::1", "localhost"):
        return "localhost"
    if address in ("0.0.0.0", "::"):
        return "all-interfaces"
    return address


class PortScanner:
    def __init__(self, process_manager: ProcessManager | None = None):
        self.process_manager = process_manager or ProcessManager()

    def scan(
        self,
        favorites: Iterable[int] = (),
        collapse_duplicate_bindings: bool = True,
    ) -> List[PortInfo]:
        favorite_set = {int(p) for p in favorites}
        rows: list[PortInfo] = []
        seen: set[tuple[str, int, int]] = set()

        try:
            connections = psutil.net_connections(kind="tcp")
        except (psutil.AccessDenied, PermissionError) as exc:
            raise PermissionError(
                "Listening ports could not be enumerated. Try running as Administrator."
            ) from exc

        for conn in connections:
            if conn.status != psutil.CONN_LISTEN or not conn.laddr:
                continue

            address = getattr(conn.laddr, "ip", None) or conn.laddr[0]
            port = int(getattr(conn.laddr, "port", None) or conn.laddr[1])
            pid = int(conn.pid or 0)
            if port <= 0:
                continue

            address_key = _binding_group(address) if collapse_duplicate_bindings else address
            key = (address_key, port, pid)
            if key in seen:
                continue
            seen.add(key)

            proc = self.process_manager.get_process_info(pid) if pid else None
            info = PortInfo(
                port=port,
                address=address,
                pid=pid,
                process_name=proc.name if proc else "Unknown",
                executable_path=proc.executable_path if proc else "",
                command_line=proc.command_line if proc else "",
                start_time=proc.start_time if proc else None,
                username=proc.username if proc else "Unknown",
                category=proc.category if proc else "Other",
                is_favorite=port in favorite_set,
            )
            reason = get_ghost_indicator(info)
            info.is_ghost = bool(reason)
            info.ghost_reason = reason
            rows.append(info)

        rows.sort(key=lambda x: (not x.is_favorite, x.port, x.display_address, x.pid))
        return rows
