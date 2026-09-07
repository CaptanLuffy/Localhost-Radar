"""Core data models for Localhost Radar."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Sequence

GRAY_TEXT = "#94A3B8"
GREEN_LISTENING = "#22C55E"
YELLOW_WARNING = "#F59E0B"


@dataclass(slots=True)
class ProcessInfo:
    pid: int
    name: str = "Unknown"
    executable_path: str = ""
    command_line: str = ""
    start_time: Optional[datetime] = None
    username: str = "Unknown"
    category: str = "Other"


@dataclass(slots=True)
class PortInfo:
    port: int
    address: str
    pid: int
    protocol: str = "TCP"
    status: str = "Listening"
    process_name: str = "Unknown"
    executable_path: str = ""
    command_line: str = ""
    start_time: Optional[datetime] = None
    username: str = "Unknown"
    category: str = "Other"
    is_favorite: bool = False
    is_ghost: bool = False
    ghost_reason: str = ""

    @property
    def display_address(self) -> str:
        if self.address in ("::", "0.0.0.0"):
            return "All interfaces"
        if self.address in ("::1", "127.0.0.1"):
            return "localhost"
        return self.address

    @property
    def endpoint(self) -> str:
        host = "localhost" if self.address in ("127.0.0.1", "localhost", "0.0.0.0", "::1", "::") else self.address
        return f"{host}:{self.port}"

    @property
    def browser_url(self) -> str:
        """Return a conservative browser URL only when the listener looks HTTP-like."""
        web_ports = {
            80, 81, 443, 3000, 3001, 4000, 4173, 4200, 5000, 5001,
            5173, 5174, 7000, 7001, 8000, 8001, 8080, 8081, 8088,
            8443, 8888, 9000,
        }
        text = f"{self.process_name} {self.command_line}".lower()
        looks_web = (
            self.port in web_ports
            or any(token in text for token in (
                "vite", "next", "webpack", "react", "vue", "angular", "flask",
                "django", "uvicorn", "fastapi", "streamlit", "http.server",
                "localhost", "http://", "https://"
            ))
        )
        if not looks_web:
            return ""
        host = "localhost" if self.address in ("127.0.0.1", "localhost", "0.0.0.0", "::1", "::") else self.address
        scheme = "https" if self.port in {443, 8443} else "http"
        return f"{scheme}://{host}:{self.port}"

    @property
    def display_url(self) -> str:
        # Backwards-compatible alias used by older helper code.
        return self.browser_url

    @property
    def age_text(self) -> str:
        if not self.start_time:
            return "N/A"
        delta = datetime.now() - self.start_time
        seconds = max(0, int(delta.total_seconds()))
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            return f"{seconds // 60}m"
        if seconds < 86400:
            return f"{seconds // 3600}h"
        return f"{seconds // 86400}d"


def classify_process(process_name: str, command_line: str = "") -> str:
    text = f"{process_name} {command_line}".lower()
    rules = (
        (("node", "npm", "vite", "next"), "Node.js"),
        (("python", "uvicorn", "flask", "django", "streamlit"), "Python"),
        (("postgres",), "PostgreSQL"),
        (("mysqld", "mysql"), "MySQL"),
        (("redis",), "Redis"),
        (("java", "gradle", "maven"), "Java"),
        (("dotnet",), ".NET"),
        (("docker", "com.docker"), "Docker"),
        (("php",), "PHP"),
        (("ruby",), "Ruby"),
    )
    for needles, category in rules:
        if any(needle in text for needle in needles):
            return category
    return "Other"


def is_system_process(process_name: str) -> bool:
    name = (process_name or "").lower()
    protected = {
        "system", "system idle process", "registry", "memory compression",
        "wininit.exe", "csrss.exe", "services.exe", "lsass.exe", "smss.exe",
        "svchost.exe", "winlogon.exe", "fontdrvhost.exe", "dwm.exe",
        "sihost.exe", "explorer.exe", "taskhostw.exe",
    }
    return name in protected


def is_development_process(process_name: str, category: str = "Other") -> bool:
    if category != "Other":
        return True
    name = (process_name or "").lower()
    return any(x in name for x in ("node", "python", "java", "dotnet", "php", "ruby"))


def is_favorite_port(port: int, favorites: Sequence[int]) -> bool:
    return port in favorites


def get_ghost_indicator(port_info: PortInfo) -> str:
    common_dev_ports = {
        3000, 3001, 4000, 4173, 4200, 5000, 5001, 5173, 5174,
        8000, 8001, 8080, 8081, 8888, 9000,
    }
    if (
        is_development_process(port_info.process_name, port_info.category)
        and port_info.port in common_dev_ports
        and port_info.start_time
        and datetime.now() - port_info.start_time > timedelta(hours=2)
    ):
        return "Possible leftover development server"
    return ""
