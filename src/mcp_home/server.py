"""The `home` MCP server instance and its tool guide."""

from jarvis_mcp_kit import ToolServer

INSTRUCTIONS = (
    "Smart lighting in the caller's home (Tuya devices on the local network). Start with "
    "get_devices_state — it connects to the devices and returns every device's state plus the "
    "user's saved lighting preferences. Then act by device NAME, running independent calls in "
    "parallel.\n"
    "ROOMS AND ZONES: each device has a 'room' (e.g. living_room, bedroom) and a 'zones' list "
    "(e.g. entertainment_zone, work_zone). Membership is defined ONLY by these fields — never "
    "infer it from a device's name. Map Polish words: 'salon'/'pokój dzienny' → living_room, "
    "'sypialnia' → bedroom, 'kuchnia' → kitchen, 'łazienka' → bathroom, 'gabinet'/'biuro' → "
    "office, 'przedpokój'/'korytarz' → hallway; zones by meaning ('strefa rozrywki'/'kino' → "
    "entertainment_zone, 'strefa pracy' → work_zone, 'strefa spania' → sleep_zone).\n"
    "COMPLETENESS: for a whole room, zone or 'wszystko', (1) list and count every matching "
    "device, (2) command EVERY one of them in parallel, (3) check the number you commanded "
    "equals the count before finishing.\n"
    "UNREACHABLE DEVICES: a device with an error/unreachable state cannot be controlled — still "
    "handle the others and report exactly which devices could not be reached.\n"
    "Colour changes need 'colour' mode; temperature changes need 'white' mode."
)

server = ToolServer("home", title="Jarvis Home", instructions=INSTRUCTIONS)
