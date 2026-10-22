"""Devices per principal (a household group id, or a client id), from a scopes file.

``MCP_HOME_CONFIG`` (default ``config/home.yaml``)::

    scopes:
      - principals: [dom, kuba-claude-code]
        devices_file: data/smart_devices.json      # {"list_of_elements": [...]} with local keys
        preferences_file: data/preferences.json    # optional, shown to the model

Device handles (with IP / local key / id) live only in this process; tools see device names.
Loaded devices are cached per devices file and reloaded when the file changes, so IPs healed
by a wake scan survive between calls.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from jarvis_mcp_kit import ScopedConfig, current_principal

from mcp_home.device import SmartDevice

logger = logging.getLogger(__name__)

HOME = ScopedConfig("MCP_HOME_CONFIG", "config/home.yaml")

_cache: dict[str, tuple[float, dict[str, SmartDevice]]] = {}
_lock = asyncio.Lock()


def scope() -> dict:
    return HOME.for_principal(current_principal()) or {}


async def _load(path: Path) -> dict[str, SmartDevice]:
    configs = json.loads(path.read_text(encoding="utf-8"))["list_of_elements"]
    devices: dict[str, SmartDevice] = {}
    for c in configs:
        try:
            dev = await SmartDevice.create_from_json(c)
            devices[dev.name] = dev
        except Exception as e:  # one bad entry must not hide the rest
            logger.error("Error creating device (%s)", type(e).__name__)
    return devices


async def devices(force: bool = False) -> dict[str, SmartDevice]:
    """The caller's devices by name ({} when the caller has no home configured)."""
    raw = scope().get("devices_file")
    if not raw:
        return {}
    path = Path(raw)
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        logger.error("Devices file for this principal is missing: %s", path)
        return {}
    key = str(path.resolve())
    async with _lock:
        cached = _cache.get(key)
        if force or cached is None or cached[0] != mtime:
            _cache[key] = (mtime, await _load(path))
        return _cache[key][1]


def preferences() -> dict:
    raw = scope().get("preferences_file")
    if not raw:
        return {}
    try:
        return json.loads(Path(raw).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Preferences file unreadable (%s)", type(e).__name__)
        return {}


def resolve(registry: dict[str, SmartDevice], names: list[str]) -> tuple[list[SmartDevice], list[str]]:
    """Map device names (case-insensitive) to devices. Returns (found, unknown_names)."""
    lower = {name.lower(): dev for name, dev in registry.items()}
    found, unknown = [], []
    for n in names:
        dev: Optional[SmartDevice] = registry.get(n) or lower.get((n or "").strip().lower())
        if dev is not None:
            found.append(dev)
        else:
            unknown.append(n)
    return found, unknown


def clear_cache() -> None:
    _cache.clear()
