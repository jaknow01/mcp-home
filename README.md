# mcp-home

Smart lighting control (Tuya devices, local network) as an
[MCP](https://modelcontextprotocol.io) server. It must run **inside the home network** — on a
Raspberry Pi, not in a cloud/cluster — because it talks to the bulbs over the LAN.

| Tool | |
|---|---|
| `get_devices_state` | connect, wake the bulbs, return every device's state + saved preferences |
| `get_one_device_status` | one device's state |
| `turn_on_devices` / `turn_off_devices` | by device name |
| `change_lighting_mode` | white / colour |
| `change_color` | RGB (colour mode) |
| `change_light_temperature` | 0–1000 (white mode) |
| `whoami` | which client and principal your key acts as |

Devices are referred to **by name only**; IP addresses, device ids and local keys stay on the
server. **Devices are per principal** — a household group id forwarded by a trusted client
such as Jarvis (`X-On-Behalf-Of: dom`). A caller with no home configured gets nothing.

Part of the Jarvis tool servers; built on
[jarvis-mcp-kit](https://github.com/jaknow01/jarvis-mcp-kit) (API keys, rate limits, logs).

## Run on the Pi

```bash
mkdir -p config data
cp config/clients.example.yaml config/clients.yaml   # Jarvis's trusted key (jarvis-mcp-keys new jarvis --servers home --trusted)
cp config/home.example.yaml config/home.yaml         # devices_file: /data/smart_devices.json
cp <jarvis>/data/smart_device_data/*.json data/
docker compose -f deploy/docker-compose.yml up -d    # host networking for Tuya UDP discovery
curl localhost:8010/health
```

The image is multi-arch (amd64 + arm64).

## Reaching it from k3s (WireGuard, least privilege)

The Pi does **not** join the cluster. The cluster gets one narrow WireGuard tunnel to the home
router and can reach only the Pi's MCP port:

```
k3s: jarvis ──(NetworkPolicy: only jarvis)──► home-gateway pod ═ WireGuard ═► home router ─► Pi:8010
```

1. **Router (WireGuard server):** add a peer `k3s` with its own key pair and tunnel address
   (e.g. `10.8.0.50/32`).
2. **Router firewall:** allow traffic from that peer **only** to `<pi-lan-ip>:8010/tcp`, drop
   everything else from it. For example:
   - OpenWrt (`/etc/config/firewall`): a zone for the WireGuard interface with
     `option input REJECT`, `option forward REJECT`, plus a rule `src wg / src_ip 10.8.0.50 /
     dest lan / dest_ip <pi-lan-ip> / dest_port 8010 / proto tcp / target ACCEPT`.
   - MikroTik: `/ip firewall filter add chain=forward src-address=10.8.0.50 dst-address=<pi-lan-ip> protocol=tcp dst-port=8010 action=accept`
     followed by `... src-address=10.8.0.50 action=drop` (and the same drop in `chain=input`).
3. **Cluster:** create the `home-gateway-wg` Secret (see the header of
   `deploy/k3s-home-gateway.yaml`, with `AllowedIPs = <pi-lan-ip>/32`), set the Pi's address in
   the forwarder, and apply the manifest. Jarvis then uses `http://mcp-home.jarvis.svc/mcp/home`.
4. **Check:** Jarvis can list devices; a pod in another namespace cannot connect to
   `mcp-home.jarvis`; from the tunnel, nothing but `<pi-lan-ip>:8010` answers; a request without
   a key gets 401.

If the home connection is down, only the lighting tools fail; everything else keeps working.
