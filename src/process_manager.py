"""Process discovery and safe process termination for Localhost Radar."""
from __future__ import annotations

from datetime import datetime
import logging
import os
import time
from typing import Dict, Optional

import psutil

from .models import ProcessInfo, classify_process, is_system_process

logger = logging.getLogger(__name__)


class ProcessManager:
    _process_cache: Dict[int, ProcessInfo] = {}
    _cache_timestamps: Dict[int, float] = {}
    _cache_timeout = 10.0

    @classmethod
    def get_process_info(cls, pid: int) -> Optional[ProcessInfo]:
        if not pid:
            return None
        now = time.monotonic()
        cached = cls._process_cache.get(pid)
        if cached and now - cls._cache_timestamps.get(pid, 0) < cls._cache_timeout:
            return cached

        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                try:
                    name = proc.name() or "Unknown"
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    name = "Unknown"
                try:
                    exe = proc.exe() or ""
                except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                    exe = ""
                try:
                    cmdline = " ".join(proc.cmdline())
                except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                    cmdline = ""
                try:
                    start = datetime.fromtimestamp(proc.create_time())
                except (psutil.AccessDenied, psutil.NoSuchProcess, OSError, ValueError):
                    start = None
                try:
                    username = proc.username() or "Unknown"
                except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                    username = "Unknown"

            info = ProcessInfo(
                pid=pid,
                name=name,
                executable_path=exe,
                command_line=cmdline,
                start_time=start,
                username=username,
                category=classify_process(name, cmdline),
            )
            cls._process_cache[pid] = info
            cls._cache_timestamps[pid] = now
            return info
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            cls._drop_cache(pid)
            return None
        except psutil.AccessDenied:
            info = ProcessInfo(pid=pid, username="Access denied")
            cls._process_cache[pid] = info
            cls._cache_timestamps[pid] = now
            return info
        except Exception as exc:
            logger.debug("Process lookup failed for PID %s: %s", pid, exc)
            return None

    @classmethod
    def terminate_process(cls, pid: int, force: bool = False) -> tuple[bool, str]:
        if pid == os.getpid():
            return False, "Localhost Radar cannot terminate itself."
        try:
            proc = psutil.Process(pid)
            name = proc.name() or f"PID {pid}"
            if is_system_process(name):
                return False, f"{name} is protected and will not be terminated."

            if force:
                proc.kill()
            else:
                proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                if not force:
                    return False, "Process did not exit within 3 seconds."
                return False, "Process did not exit after force kill."

            cls._drop_cache(pid)
            return True, f"{name} (PID {pid}) was terminated."
        except psutil.NoSuchProcess:
            cls._drop_cache(pid)
            return True, f"PID {pid} is no longer running."
        except psutil.AccessDenied:
            return False, "Access denied. Run Localhost Radar as Administrator for this process."
        except Exception as exc:
            logger.exception("Terminate failed for PID %s", pid)
            return False, str(exc)

    @classmethod
    def refresh_process_cache(cls) -> None:
        cls._process_cache.clear()
        cls._cache_timestamps.clear()

    @classmethod
    def _drop_cache(cls, pid: int) -> None:
        cls._process_cache.pop(pid, None)
        cls._cache_timestamps.pop(pid, None)
