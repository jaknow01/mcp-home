"""Smart-lighting tools (Tuya, local LAN): state, on/off, mode, colour, temperature.

The model refers to devices only by their NAME; ip / local_key / dev_id stay in this process
(registry.py) and never appear in tool results.
"""

import asyncio
import logging
from typing import Annotated, List

from mcp_home import registry
from mcp_home.device import RGB, Mode
from mcp_home.server import server
from mcp_home.tuya_link import SCAN_TIMEOUT, manager

logger = logging.getLogger(__name__)


async def _wake_and_heal_ips(devices: dict) -> None:
    """One broadcast scan up front wakes cold bulbs (they often refuse direct TCP until a
    scan has seen them) and corrects drifted IPs from the scan result."""
    id_to_ip = await asyncio.to_thread(manager.scan, SCAN_TIMEOUT, "wake before status sweep")
    for dev in devices.values():
        ip = id_to_ip.get(dev.dev_id)
        if ip and ip != dev.ip:
            logger.info("%s: IP drift corrected from wake scan", dev.name)
            dev.ip = ip


def _unknown_device_error(devices: dict, name: str) -> dict:
    return {"Error": f"Unknown device '{name}'.", "available_devices": list(devices.keys())}


def _no_home() -> dict:
    return {"Error": "No smart home is linked to this caller.", "available_devices": []}


@server.tool(read_only=True, open_world=False)
async def get_devices_state():
    """
    Description:
        This tool is used to download initial neccessary data about all smart devices from a database.
        It is then used to establish connection and check their current states.
    Note:
        This tool should only be run at the beginning of agent's tool calls. This provides an initial scan
        but due to accessing of the database it has a large overhead therefore it should only be run once.
        Devices are identified by their name; use those names with the other device tools.
    """
    devices = await registry.devices(force=True)
    if not devices:
        return _no_home()
    await _wake_and_heal_ips(devices)
    states = await asyncio.gather(*(d.get_status() for d in devices.values()))
    return {"states": states, "known_user_preferences": registry.preferences()}


@server.tool(read_only=True, open_world=False)
async def get_one_device_status(device_name: str) -> dict:
    """
    Description:
    This tool is used to check the status of a given device without the unnecessary overhead
    of checking all devices in the system. It should be used as an intermediate tool between tool calls
    instead of the tool get_devices_state.

    Note:
        When agents wants to interact with multiple devices this tool should be run in parallel.

    Parameters:
    device_name : str
        The name of the device whose status should be checked (as returned by get_devices_state).

    Output:
        State of the given device
    """
    devices = await registry.devices()
    if not devices:
        return _no_home()
    found, _ = registry.resolve(devices, [device_name])
    if not found:
        return _unknown_device_error(devices, device_name)
    return await found[0].get_status()


async def _switch(device_names: List[str], on: bool) -> dict:
    devices = await registry.devices()
    if not devices:
        return _no_home()
    found, unknown = registry.resolve(devices, device_names)
    await asyncio.gather(*((dev.turn_on() if on else dev.turn_off()) for dev in found))
    result: dict = {"states": await asyncio.gather(*(dev.get_status() for dev in found))}
    if unknown:
        result["unknown_devices"] = unknown
    return result


@server.tool(read_only=False, open_world=False)
async def turn_on_devices(device_names: List[str]) -> dict:
    """
    Description:
    This tool is used to turn on all mentioned devices.

    Parameters:
    device_names : List[str]
        Names of the devices that should be turned on (as returned by get_devices_state).

    Output:
    This tool returns the new states of the affected devices (and any names it did not recognize)
    """
    return await _switch(device_names, on=True)


@server.tool(read_only=False, open_world=False)
async def turn_off_devices(device_names: List[str]) -> dict:
    """
    Description:
    This tool is used to turn off all mentioned devices.

    Parameters:
    device_names : List[str]
        Names of the devices that should be turned off (as returned by get_devices_state).

    Output:
    This tool returns the new states of the affected devices (and any names it did not recognize)
    """
    return await _switch(device_names, on=False)


@server.tool(read_only=False, open_world=False)
async def change_lighting_mode(device_name: str, new_mode: Mode) -> dict:
    """
    Description:
    This tool is used to change the lighting mode of a given smart device. Lighting mode can either
    be set to white or colour mode. When in colour mode various rgb settings can be applied to the
    device. When in white mode the lighting temperature can be adjusted.

    Parameters:
    device_name: str
        The name of the device that is to be affected by the mode change.

    new_mode: Mode
        The mode that will be applied to the chosen device
    """
    devices = await registry.devices()
    found, _ = registry.resolve(devices, [device_name])
    if not found:
        return _unknown_device_error(devices, device_name) if devices else _no_home()
    return await found[0].change_mode(new_mode)


@server.tool(read_only=False, open_world=False)
async def change_color(device_name: str, new_color: RGB) -> dict:
    """
    Description:
    This tool is used to change the colour of the given smart device.
    In order to set a new RGB value device must be in 'colour' lighting mode.

    Parameters:
    device_name: str
        The name of the device that is to be affected by the color change.
        Note: this device must be in 'colour' lighting mode in order for the change to be possible

    new_color: RGB
        The new color that the device will be set to as an RGB value.
        RGB values are integers from 0 to 255 where R = red, G = green, B = blue

    Output:
        This tool returns short information whether the attempt was successful
    """
    devices = await registry.devices()
    found, _ = registry.resolve(devices, [device_name])
    if not found:
        return _unknown_device_error(devices, device_name) if devices else _no_home()
    return await found[0].change_color(new_color)


@server.tool(read_only=False, open_world=False)
async def change_light_temperature(device_name: str, new_temp: Annotated[int, "range 0-1000"]) -> dict:
    """
    Description:
    This tool is used to change the colour temperature of the given device.
    In order to set a new color temperature the device must be in 'white' lighting mode.

    Parameters:
    device_name: str
        The name of the device that is to be affected by the lighting temperature change.
        Note: this device must be in 'white' lighting mode in order for the change to be possible

    new_temp: Annotated[int, "range 0-1000"]
        This parameter controls the temperature value where 0 is the brightest and 1000 the coldest

    Output:
        This tool returns short information whether the attempt was successful
    """
    devices = await registry.devices()
    found, _ = registry.resolve(devices, [device_name])
    if not found:
        return _unknown_device_error(devices, device_name) if devices else _no_home()
    return await found[0].change_temperature(new_temp)
