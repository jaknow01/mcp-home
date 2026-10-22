"""Device secrets never reach the caller; devices are per principal; name resolution."""

import asyncio
import json

import pytest
import yaml
from jarvis_mcp_kit import Client, acting_as

from conftest import call_tools, text_of
from mcp_home import registry, tools
from mcp_home.device import SmartDevice


def _device(name="Telewizor"):
    return SmartDevice(name=name, dev_id="bfsecret123", ip="192.168.0.131", local_key="TOPSECRETKEY0000",
                       room="living_room", zones=["entertainment_zone"])


def test_describe_as_json_hides_secrets():
    di = _device().describe_as_json()
    assert set(di.keys()) == {"name", "room", "zones"}


def test_status_device_info_has_no_secrets():
    out = _device()._translate_status({"dps": {"20": True, "21": "white", "22": 40}})
    assert out["device_info"] == {"name": "Telewizor", "room": "living_room", "zones": ["entertainment_zone"]}


def test_resolve_exact_case_insensitive_and_unknown():
    reg = {"Telewizor": _device("Telewizor"), "Łóżko": _device("Łóżko")}
    found, unknown = registry.resolve(reg, ["Telewizor", "łóżko", "Ghost"])
    assert [d.name for d in found] == ["Telewizor", "Łóżko"] and unknown == ["Ghost"]
    assert registry.resolve({}, ["Telewizor"]) == ([], ["Telewizor"])


@pytest.fixture
def home(tmp_path, monkeypatch):
    devices = {"list_of_elements": [{"custom_name": "Telewizor", "params": {
        "id": "bfsecret123", "local_ip": "192.168.0.131", "local_key": "TOPSECRETKEY0000",
        "room": "living_room", "zones": ["entertainment_zone"]}}]}
    (tmp_path / "dev.json").write_text(json.dumps(devices))
    (tmp_path / "pref.json").write_text(json.dumps({"evening": "warm"}))
    (tmp_path / "home.yaml").write_text(yaml.safe_dump({"scopes": [
        {"principals": ["dom", "jarvis"], "devices_file": str(tmp_path / "dev.json"),
         "preferences_file": str(tmp_path / "pref.json")}]}))
    monkeypatch.setenv("MCP_HOME_CONFIG", str(tmp_path / "home.yaml"))
    registry.HOME._mtime = None
    registry.clear_cache()

    async def fake_status(self):
        return self._translate_status({"dps": {"20": True, "21": "white", "22": 40}})

    monkeypatch.setattr(SmartDevice, "get_status", fake_status)
    monkeypatch.setattr(tools.manager, "scan", lambda *a, **k: {})


def _as(principal):
    return acting_as(Client("c", "C", "0" * 64, frozenset({"home"})), principal)


def test_devices_are_per_principal(home):
    with _as("dom"):
        out = asyncio.run(tools.get_devices_state())
    assert out["states"][0]["device_info"]["name"] == "Telewizor"
    assert out["known_user_preferences"] == {"evening": "warm"}
    for secret in ("bfsecret123", "192.168.0.131", "TOPSECRETKEY0000"):
        assert secret not in json.dumps(out)
    with _as("stranger"):
        assert asyncio.run(tools.get_devices_state())["Error"] == "No smart home is linked to this caller."


def test_over_mcp_with_household(home, app, keys):
    (out,) = call_tools(app, keys["jarvis"], [("get_devices_state", {})], on_behalf_of="dom")
    assert "Telewizor" in text_of(out) and "TOPSECRETKEY0000" not in text_of(out)
