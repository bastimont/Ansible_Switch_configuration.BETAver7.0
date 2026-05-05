#!/usr/bin/env python3
"""
web_app/app.py - FastAPI Web Interface for Ansible Switch Manager
Replicates all CLI functionality in a web browser.
"""

import os
import re
import sys
import json
import subprocess
import platform
import ipaddress
import threading
import time
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# ──────────────────────────────────────────────────────────────────────────────
# PATHS - resolve to the ansible_switch root (parent of web_app)
# ──────────────────────────────────────────────────────────────────────────────
WEB_APP_DIR = Path(__file__).parent.resolve()
BASE_DIR = WEB_APP_DIR.parent.resolve()
HOST_VARS_DIR = BASE_DIR / "host_vars"
INVENTORY_PATH = BASE_DIR / "inventory" / "hosts.ini"
PLAYBOOKS_DIR = BASE_DIR / "playbooks"
CONFIG_PAGE_IP_FILE = BASE_DIR / "config_page_ip.txt"
DEFAULT_CONFIG_IP = "192.168.0.1"


def get_config_page_ip() -> str:
    try:
        ip = CONFIG_PAGE_IP_FILE.read_text(encoding="utf-8").strip()
        return ip if ip else DEFAULT_CONFIG_IP
    except FileNotFoundError:
        return DEFAULT_CONFIG_IP


def set_config_page_ip(new_ip: str) -> bool:
    try:
        ipaddress.IPv4Address(new_ip)
    except ValueError:
        return False
    CONFIG_PAGE_IP_FILE.write_text(new_ip + "\n", encoding="utf-8")
    return True

# ──────────────────────────────────────────────────────────────────────────────
# SWITCH TOPOLOGY (same as menu.py) — Two architecture modules
# ──────────────────────────────────────────────────────────────────────────────
MODULE_1_SWITCHES = [
    {"name": "MAIN", "tier": "MGMT", "group": "management", "default_ip": "127.0.0.1"},
    {"name": "H1-B", "tier": "H",    "group": "tier_h",     "default_ip": "10.0.1.2"},
    {"name": "H1-A", "tier": "H",    "group": "tier_h",     "default_ip": "10.0.1.3"},
    {"name": "A1-B", "tier": "A",    "group": "tier_a",     "default_ip": "10.0.1.4"},
    {"name": "A1-A", "tier": "A",    "group": "tier_a",     "default_ip": "10.0.1.5"},
    {"name": "B1-B", "tier": "B",    "group": "tier_b",     "default_ip": "10.0.2.2"},
    {"name": "B1-A", "tier": "B",    "group": "tier_b",     "default_ip": "10.0.2.3"},
    {"name": "C1-B", "tier": "C",    "group": "tier_c",     "default_ip": "10.0.3.2"},
    {"name": "C1-A", "tier": "C",    "group": "tier_c",     "default_ip": "10.0.3.3"},
    {"name": "D1-B", "tier": "D",    "group": "tier_d",     "default_ip": "10.0.4.2"},
    {"name": "D1-A", "tier": "D",    "group": "tier_d",     "default_ip": "10.0.4.3"},
    {"name": "E1-B", "tier": "E",    "group": "tier_e",     "default_ip": "10.0.5.2"},
    {"name": "E1-A", "tier": "E",    "group": "tier_e",     "default_ip": "10.0.5.3"},
    {"name": "F1-B", "tier": "F",    "group": "tier_f",     "default_ip": "10.0.6.2"},
    {"name": "F1-A", "tier": "F",    "group": "tier_f",     "default_ip": "10.0.6.3"},
    {"name": "G1-B", "tier": "G",    "group": "tier_g",     "default_ip": "10.0.7.2"},
    {"name": "G1-A", "tier": "G",    "group": "tier_g",     "default_ip": "10.0.7.3"},
]

MODULE_2_SWITCHES = [
    {"name": "MAIN",  "tier": "MGMT",  "group": "management",  "default_ip": "127.0.0.2",    "vlan": 0},
    {"name": "H1-B",  "tier": "H",     "group": "vlan1_h",     "default_ip": "172.16.1.253", "vlan": 1},
    {"name": "H1-A",  "tier": "H",     "group": "vlan1_h",     "default_ip": "172.16.1.252", "vlan": 1},
    {"name": "A1-B",  "tier": "A",     "group": "vlan1_a",     "default_ip": "172.16.1.251", "vlan": 1},
    {"name": "A1-A",  "tier": "A",     "group": "vlan1_a",     "default_ip": "172.16.1.250", "vlan": 1},
    {"name": "B1-B",  "tier": "B",     "group": "vlan1_b",     "default_ip": "172.16.2.253", "vlan": 1},
    {"name": "B1-A",  "tier": "B",     "group": "vlan1_b",     "default_ip": "172.16.2.252", "vlan": 1},
    {"name": "C1-B",  "tier": "C",     "group": "vlan1_c",     "default_ip": "172.16.3.253", "vlan": 1},
    {"name": "C1-A",  "tier": "C",     "group": "vlan1_c",     "default_ip": "172.16.3.252", "vlan": 1},
    {"name": "D1-B",  "tier": "D",     "group": "vlan1_d",     "default_ip": "172.16.4.253", "vlan": 1},
    {"name": "D1-A",  "tier": "D",     "group": "vlan1_d",     "default_ip": "172.16.4.252", "vlan": 1},
    {"name": "E1-B",  "tier": "E",     "group": "vlan1_e",     "default_ip": "172.16.5.253", "vlan": 1},
    {"name": "E1-A",  "tier": "E",     "group": "vlan1_e",     "default_ip": "172.16.5.252", "vlan": 1},
    {"name": "F1-B",  "tier": "F",     "group": "vlan1_f",     "default_ip": "172.16.6.253", "vlan": 1},
    {"name": "F1-A",  "tier": "F",     "group": "vlan1_f",     "default_ip": "172.16.6.252", "vlan": 1},
    {"name": "G1-B",  "tier": "G",     "group": "vlan1_g",     "default_ip": "172.16.7.253", "vlan": 1},
    {"name": "G1-A",  "tier": "G",     "group": "vlan1_g",     "default_ip": "172.16.7.252", "vlan": 1},
    {"name": "H2-B",  "tier": "H",     "group": "vlan2_h",     "default_ip": "172.16.11.41", "vlan": 2},
    {"name": "H2-A",  "tier": "H",     "group": "vlan2_h",     "default_ip": "172.16.11.42", "vlan": 2},
    {"name": "A2-B",  "tier": "A",     "group": "vlan2_a",     "default_ip": "172.16.11.43", "vlan": 2},
    {"name": "A2-A",  "tier": "A",     "group": "vlan2_a",     "default_ip": "172.16.11.44", "vlan": 2},
    {"name": "B2-B",  "tier": "B",     "group": "vlan2_b",     "default_ip": "172.16.12.41", "vlan": 2},
    {"name": "B2-A",  "tier": "B",     "group": "vlan2_b",     "default_ip": "172.16.12.42", "vlan": 2},
    {"name": "C2-B",  "tier": "C",     "group": "vlan2_c",     "default_ip": "172.16.13.41", "vlan": 2},
    {"name": "C2-A",  "tier": "C",     "group": "vlan2_c",     "default_ip": "172.16.13.42", "vlan": 2},
    {"name": "D2-B",  "tier": "D",     "group": "vlan2_d",     "default_ip": "172.16.14.41", "vlan": 2},
    {"name": "D2-A",  "tier": "D",     "group": "vlan2_d",     "default_ip": "172.16.14.42", "vlan": 2},
    {"name": "E2-B",  "tier": "E",     "group": "vlan2_e",     "default_ip": "172.16.15.41", "vlan": 2},
    {"name": "E2-A",  "tier": "E",     "group": "vlan2_e",     "default_ip": "172.16.15.42", "vlan": 2},
    {"name": "F2-B",  "tier": "F",     "group": "vlan2_f",     "default_ip": "172.16.16.41", "vlan": 2},
    {"name": "F2-A",  "tier": "F",     "group": "vlan2_f",     "default_ip": "172.16.16.42", "vlan": 2},
    {"name": "G2-B",  "tier": "G",     "group": "vlan2_g",     "default_ip": "172.16.17.41", "vlan": 2},
    {"name": "G2-A",  "tier": "G",     "group": "vlan2_g",     "default_ip": "172.16.17.42", "vlan": 2},
]

MODULE_FILE = BASE_DIR / "module.txt"

def get_current_module() -> int:
    try:
        val = int(MODULE_FILE.read_text().strip())
        return val if val in (1, 2) else 1
    except (FileNotFoundError, ValueError):
        return 1

def set_current_module(mod: int) -> bool:
    if mod not in (1, 2):
        return False
    MODULE_FILE.write_text(str(mod) + "\n")
    return True

def get_active_switches() -> list:
    return MODULE_1_SWITCHES if get_current_module() == 1 else MODULE_2_SWITCHES

def get_ip_key() -> str:
    return "switch_ip" if get_current_module() == 1 else "switch_ip_m2"

SWITCHES = get_active_switches()
DISCOVERY_SUBNETS = ["192.168.100.0/24", "192.168.1.0/24", "10.0.1.0/24"]

# ──────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Ansible Switch Manager", version="1.0.0")

# Mount static files
static_dir = WEB_APP_DIR / "static"
templates_dir = WEB_APP_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ──────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODELS
# ──────────────────────────────────────────────────────────────────────────────
class AssignIPRequest(BaseModel):
    switch_name: str
    new_ip: str

class PingRequest(BaseModel):
    target: str
    count: int = 4

class PingAllRequest(BaseModel):
    count: int = 2

class DiscoverAssignRequest(BaseModel):
    discovered_ip: str
    switch_name: str

class ConfigIPRequest(BaseModel):
    new_ip: str

class TracerouteRequest(BaseModel):
    new_ip: str

# ──────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────
def read_host_var(switch_name: str, key: str, default: str = "N/A") -> str:
    path = HOST_VARS_DIR / f"{switch_name}.yml"
    if not path.is_file():
        return default
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(rf"^\s*{re.escape(key)}\s*:\s*['\"]?(.+?)['\"]?\s*$", line)
            if m:
                return m.group(1).strip()
    return default


def write_host_vars(switch_name: str, new_ip: str) -> dict:
    path = HOST_VARS_DIR / f"{switch_name}.yml"
    existing_vars = {}
    if path.is_file():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("---") or not line:
                    continue
                m = re.match(r"^([a-zA-Z_]\w*)\s*:\s*['\"]?(.*?)['\"]?\s*$", line)
                if m:
                    existing_vars[m.group(1)] = m.group(2)

    existing_vars[get_ip_key()] = new_ip
    existing_vars.setdefault("switch_role", "access")
    existing_vars.setdefault("switch_description", f"{switch_name} Switch")

    content = "---\n"
    for key, val in existing_vars.items():
        content += f'{key}: "{val}"\n'

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    _update_inventory_ip(switch_name, new_ip)
    return {"switch_name": switch_name, "switch_ip": new_ip, **existing_vars}


def _update_inventory_ip(switch_name: str, new_ip: str) -> None:
    """Update the ansible_host for a switch in inventory/hosts.ini.
    Note: Inventory may use different hostnames; this is a best-effort sync."""
    if not INVENTORY_PATH.is_file():
        return
    content = INVENTORY_PATH.read_text(encoding="utf-8")
    pattern = rf"^({re.escape(switch_name)}\s+ansible_host=)\S+"
    try:
        new_content = re.sub(pattern, lambda m: m.group(1) + new_ip, content, flags=re.MULTILINE)
        if new_content != content:
            INVENTORY_PATH.write_text(new_content, encoding="utf-8")
    except re.error:
        pass  # Inventory format may differ; skip sync


def validate_ip(ip_str: str) -> bool:
    try:
        ipaddress.IPv4Address(ip_str)
        return True
    except ValueError:
        return False


def get_topology() -> list:
    result = []
    ip_key = get_ip_key()
    for sw in get_active_switches():
        result.append({
            "name": sw["name"],
            "tier": sw["tier"],
            "group": sw["group"],
            "switch_ip": read_host_var(sw["name"], ip_key, "N/A"),
            "switch_role": read_host_var(sw["name"], "switch_role", "access"),
            "switch_description": read_host_var(sw["name"], "switch_description", "Unconfigured"),
            "default_ip": sw["default_ip"],
            "vlan": sw.get("vlan", 0),
        })
    return result


def run_ansible_playbook(playbook_name: str, extra_vars: dict = None) -> dict:
    cmd = ["ansible-playbook", str(PLAYBOOKS_DIR / playbook_name)]
    if extra_vars:
        vars_str = " ".join(f'{k}="{v}"' for k, v in extra_vars.items())
        cmd.extend(["-e", vars_str])
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR),
            timeout=60,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "stdout": "", "stderr": "Playbook timed out"}
    except FileNotFoundError:
        return {"returncode": -1, "stdout": "", "stderr": "ansible-playbook not found"}


def _real_ping(host: str, count: int = 4) -> dict:
    is_windows = platform.system() == "Windows"
    if is_windows:
        cmd = ["ping", "-n", str(count), host]
    else:
        cmd = ["ping", "-c", str(count), host]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="cp850" if is_windows else "utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return {"success": False, "host_unreachable": False, "output": "ping command not found", "lines": []}

    lines = []
    host_unreachable = False
    if proc.stdout:
        for raw_line in proc.stdout:
            line = raw_line.rstrip()
            lower = line.lower()
            line_type = "info"
            if any(kw in lower for kw in ("reply from", "bytes from")):
                line_type = "reply"
            elif "destination host unreachable" in lower:
                line_type = "unreachable"
                host_unreachable = True
            elif any(kw in lower for kw in ("request timed out",
                                            "100% loss", "100% packet loss",
                                            "could not find host", "unknown host",
                                            "transmit failed")):
                line_type = "timeout"
            elif any(kw in lower for kw in ("ping statistics", "packets:", "approximate",
                                            "minimum", "round-trip", "rtt", "packet loss")):
                line_type = "stats"
            lines.append({"text": line, "type": line_type})

    proc.wait()
    return {"success": proc.returncode == 0, "host_unreachable": host_unreachable,
            "output": "\n".join(l["text"] for l in lines), "lines": lines}


def get_local_subnets():
    subnets = []
    ips = []
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output(["ipconfig"], text=True, encoding="cp850")
            for line in output.splitlines():
                if "IPv4 Address" in line or "Direcci" in line:
                    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                    if m:
                        ip = m.group(1)
                        if not ip.startswith("127."):
                            ips.append(ip)
                            parts = ip.split(".")
                            subnets.append(f"{parts[0]}.{parts[1]}.{parts[2]}.0/24")
        else:
            output = subprocess.check_output(["ip", "-4", "addr", "show"], text=True)
            for line in output.splitlines():
                m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", line)
                if m:
                    ip = m.group(1)
                    if not ip.startswith("127."):
                        ips.append(ip)
                        parts = ip.split(".")
                        subnets.append(f"{parts[0]}.{parts[1]}.{parts[2]}.0/24")
    except Exception:
        pass
    for ds in DISCOVERY_SUBNETS:
        if ds not in subnets:
            subnets.append(ds)
    return list(set(subnets)), list(set(ips))


def background_ping_sweep(subnets, deep=False):
    """Populate ARP table by pinging IPs in the background (non-blocking)."""
    def sweep():
        for subnet in subnets:
            base = ".".join(subnet.split(".")[:-1])
            # Common offsets or full range if deep scan
            offsets = range(1, 255) if deep else [1, 2, 10, 50, 100, 253, 254]
            for i in offsets:
                target = f"{base}.{i}"
                if platform.system() == "Windows":
                    subprocess.run(["ping", "-n", "1", "-w", "50", target],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.run(["ping", "-c", "1", "-W", "1", target],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Also try broadcast ping to force ARP replies
            broadcast = f"{base}.255"
            subprocess.run(["ping", "-n", "1", "-w", "100", broadcast],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    t = threading.Thread(target=sweep, daemon=True)
    t.start()
    return t  # Return thread so caller can optionally wait


def get_arp_table() -> list:
    """Parse the system ARP table using PowerShell (Windows) or arp command."""
    devices = []
    seen_ips = set()
    try:
        if platform.system() == "Windows":
            # Get-NetNeighbor is reliable but returns the entire cache
            # 0: Unreachable, 1: Incomplete, 5: Reachable, 6: Permanent
            cmd = ["powershell", "Get-NetNeighbor | Select-Object IPAddress, LinkLayerAddress, State | ConvertTo-Json"]
            output = subprocess.check_output(cmd, text=True, encoding="cp850", timeout=10)
            if output.strip():
                data = json.loads(output)
                if isinstance(data, dict): data = [data]
                for item in data:
                    ip = item.get("IPAddress")
                    mac = (item.get("LinkLayerAddress") or "").replace("-", ":").upper()
                    state = item.get("State")
                    # Ignore unreachable/incomplete (0/1) and all-zero or broadcast MACs
                    if not ip or not mac or state in (0, 1): continue
                    if mac in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"): continue
                    # Filter out IPv6 and multicast/broadcast junk
                    if not ip.startswith("224.") and not ip.startswith("239.") and ":" not in ip:
                        if ip not in seen_ips:
                            devices.append({"ip": ip, "mac": mac})
                            seen_ips.add(ip)
        else:
            output = subprocess.check_output(["arp", "-a"], text=True, timeout=10)
            pattern = re.compile(r"\((\d+\.\d+\.\d+\.\d+)\) at ([0-9a-fA-F:]{17})")
            for line in output.splitlines():
                m = pattern.search(line)
                if m:
                    ip, mac = m.group(1), m.group(2).upper()
                    if mac not in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"):
                        if ip not in seen_ips:
                            devices.append({"ip": ip, "mac": mac})
                            seen_ips.add(ip)
    except Exception:
        # Fallback to simple regex if PS fails or other errors
        try:
            output = subprocess.check_output(["arp", "-a"], text=True, encoding="cp850", timeout=10)
            pattern = re.compile(r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-]{17})")
            for line in output.splitlines():
                m = pattern.search(line)
                if m:
                    ip, mac = m.group(1), m.group(2).replace("-", ":").upper()
                    if mac not in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"):
                        if ip not in seen_ips:
                            devices.append({"ip": ip, "mac": mac})
                            seen_ips.add(ip)
        except: pass
    return devices


# ──────────────────────────────────────────────────────────────────────────────
# ROUTES - Pages
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    template_path = templates_dir / "index.html"
    return template_path.read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# ROUTES - API
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/topology")
async def api_topology():
    return {"switches": get_topology()}


@app.get("/api/switches")
async def api_switches():
    ip_key = get_ip_key()
    return {"switches": [{"name": sw["name"], "tier": sw["tier"], "ip": read_host_var(sw["name"], ip_key, "N/A"), "role": read_host_var(sw["name"], "switch_role", "access"), "default_ip": sw["default_ip"]} for sw in get_active_switches()]}


@app.post("/api/reset-ips")
async def api_reset_ips():
    results = []
    for sw in get_active_switches():
        data = write_host_vars(sw["name"], sw["default_ip"])
        results.append(data)
    return {"success": True, "message": "All IPs reset to defaults", "results": results}


@app.post("/api/assign-ip")
async def api_assign_ip(req: AssignIPRequest):
    if req.switch_name not in [s["name"] for s in get_active_switches()]:
        raise HTTPException(status_code=400, detail=f"Unknown switch: {req.switch_name}")
    if not validate_ip(req.new_ip):
        raise HTTPException(status_code=400, detail=f"Invalid IPv4 address: {req.new_ip}")

    data = write_host_vars(req.switch_name, req.new_ip)

    playbook_result = run_ansible_playbook("assign_ip.yml", {"target": req.switch_name, "new_ip": req.new_ip})

    return {
        "success": True,
        "message": f"{req.switch_name} → IP set to {req.new_ip}",
        "data": data,
        "ansible_result": {
            "returncode": playbook_result["returncode"],
            "stderr": playbook_result["stderr"],
        }
    }


@app.post("/api/ping")
async def api_ping(req: PingRequest):
    if not req.target:
        raise HTTPException(status_code=400, detail="Target is required")
    result = _real_ping(req.target, req.count)
    return {
        "target": req.target,
        "count": req.count,
        "success": result["success"],
        "host_unreachable": result.get("host_unreachable", False),
        "lines": result["lines"],
    }


@app.post("/api/ping-all")
async def api_ping_all(req: PingAllRequest):
    results = []
    ip_key = get_ip_key()
    for sw_name in [s["name"] for s in get_active_switches()]:
        ip = read_host_var(sw_name, ip_key, "")
        if not ip or ip in ("", "N/A", "—"):
            results.append({"switch_name": sw_name, "ip": ip, "status": "no_ip", "success": None, "lines": []})
            continue
        ping_result = _real_ping(ip, req.count)
        if ping_result["success"]:
            status = "up"
        elif ping_result.get("host_unreachable"):
            status = "unreachable_but_blocked"
        else:
            status = "down"
        results.append({
            "switch_name": sw_name,
            "ip": ip,
            "status": status,
            "success": ping_result["success"],
            "host_unreachable": ping_result.get("host_unreachable", False),
            "lines": ping_result["lines"],
        })
    return {"results": results}


@app.get("/api/discovery")
def api_discovery(scan: bool = False):
    """Simplified Live Network Discovery endpoint."""
    try:
        print("DEBUG: api_discovery called")

        # Get subnets and local IPs
        subnets, local_ips = get_local_subnets()
        print(f"DEBUG: subnets={subnets}")

        # Get ARP table
        arp_devices = get_arp_table()
        print(f"DEBUG: arp_devices count={len(arp_devices)}")

        # Get active switches and IP key
        switches = get_active_switches()
        ip_key = get_ip_key()
        print(f"DEBUG: switches count={len(switches)}, ip_key={ip_key}")

        # Build known devices
        known_devices = []
        for sw in switches:
            sw_name = sw["name"]
            ip = read_host_var(sw_name, ip_key, "")
            if ip and ip not in ("", "N/A", "—"):
                # Check if online
                in_arp = False
                mac = "??:??:??:??:??:??"
                for d in arp_devices:
                    if d["ip"] == ip:
                        in_arp = True
                        mac = d["mac"]
                        break
                known_devices.append({
                    "ip": ip,
                    "mac": mac,
                    "switch_name": sw_name,
                    "status": "online" if in_arp else "offline",
                })

        # Build other devices
        known_ips = set()
        for d in known_devices:
            known_ips.add(d["ip"])

        other_devices = []
        for d in arp_devices:
            if d["ip"] not in known_ips:
                other_devices.append(d)

        print(f"DEBUG: returning known={len(known_devices)}, other={len(other_devices)}")

        return {
            "subnets": subnets,
            "local_ips": local_ips,
            "known_devices": known_devices,
            "other_devices": other_devices,
        }
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"ERROR in api_discovery: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/api/discovery/assign")
async def api_discovery_assign(req: DiscoverAssignRequest):
    if req.switch_name not in [s["name"] for s in get_active_switches()]:
        raise HTTPException(status_code=400, detail=f"Unknown switch: {req.switch_name}")
    if not validate_ip(req.discovered_ip):
        raise HTTPException(status_code=400, detail=f"Invalid IPv4 address: {req.discovered_ip}")

    data = write_host_vars(req.switch_name, req.discovered_ip)
    return {
        "success": True,
        "message": f"{req.switch_name} now assigned to {req.discovered_ip}",
        "data": data,
    }


@app.get("/api/ipconfig")
async def api_ipconfig():
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output(["ipconfig", "/all"], text=True, encoding="cp850")
        else:
            output = subprocess.check_output(["ifconfig"], text=True)
        return {"success": True, "output": output}
    except Exception as e:
        return {"success": False, "output": f"Failed: {e}"}


@app.get("/api/config-ip")
async def api_get_config_ip():
    return {"config_ip": get_config_page_ip()}


@app.post("/api/config-ip")
async def api_set_config_ip(req: ConfigIPRequest):
    if not set_config_page_ip(req.new_ip):
        raise HTTPException(status_code=400, detail=f"Invalid IPv4 address: {req.new_ip}")
    return {"success": True, "config_ip": req.new_ip}


@app.post("/api/traceroute")
async def api_traceroute(req: TracerouteRequest):
    """Run tracert/traceroute to target. req.new_ip holds the raw input string."""
    raw = req.new_ip.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Target is required")

    parts = raw.split()

    # Find the target (first token that is a valid IP or hostname)
    # Everything else is treated as flags
    target = None
    extra_args = []
    hostname_re = re.compile(r"^(?=.*[a-zA-Z])[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$")

    for part in parts:
        if validate_ip(part) or hostname_re.match(part):
            if target is None:
                target = part
            else:
                extra_args.append(part)
        else:
            extra_args.append(part)

    if target is None:
        raise HTTPException(status_code=400, detail=f"No valid IP or hostname found in '{raw}'")

    is_windows = platform.system() == "Windows"
    cmd = ["tracert" if is_windows else "traceroute"]
    cmd.extend(extra_args)
    cmd.append(target)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="cp850" if is_windows else "utf-8",
            errors="replace",
        )
        lines = []
        if proc.stdout:
            for raw_line in proc.stdout:
                line = raw_line.rstrip()
                line_type = "info"
                lower = line.lower()
                if any(kw in lower for kw in ("timed out", "request timed out", "* * *", "unreachable")):
                    line_type = "timeout"
                elif any(kw in lower for kw in ("trace", "traceroute", "tracing", "route")):
                    line_type = "header"
                elif re.search(r"\d+\s+ms", line):
                    line_type = "hop"
                lines.append({"text": line, "type": line_type})
        proc.wait()

        # Get local subnets for display
        subnets, local_ips = get_local_subnets()

        return {
            "success": True,
            "target": target,
            "lines": lines,
            "returncode": proc.returncode,
            "local_subnets": subnets,
            "local_ips": local_ips,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="tracert/traceroute command not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/netstat")
async def api_netstat():
    """Return netstat -an output."""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output(["netstat", "-an"], text=True, encoding="cp850", timeout=10)
        else:
            output = subprocess.check_output(["netstat", "-an"], text=True, timeout=10)
        lines = []
        for line in output.splitlines():
            lower = line.lower()
            line_type = "info"
            if "listening" in lower or "established" in lower:
                line_type = "connected"
            elif "time_wait" in lower or "close_wait" in lower:
                line_type = "warning"
            elif any(kw in lower for kw in ("proto", "local", "foreign", "state")):
                line_type = "header"
            lines.append({"text": line, "type": line_type})
        return {"success": True, "lines": lines}
    except Exception as e:
        return {"success": False, "output": str(e), "lines": []}


@app.get("/api/arp")
async def api_arp_table():
    """Display the system ARP table (arp -a)."""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output(["arp", "-a"], text=True, encoding="cp850")
        else:
            output = subprocess.check_output(["arp", "-a"], text=True)
        lines = []
        for raw_line in output.splitlines():
            line = raw_line.rstrip()
            lower = line.lower()
            line_type = "info"
            if any(kw in lower for kw in ("interface", "internet", "physical", "address", "type")):
                line_type = "header"
            elif re.search(r"\d+\.\d+\.\d+\.\d+", line) and re.search(r"[0-9a-fA-F]{2}-[0-9a-fA-F]{2}", line):
                line_type = "entry"
            lines.append({"text": line, "type": line_type})
        return {"success": True, "output": output, "lines": lines}
    except Exception as e:
        return {"success": False, "output": f"Failed to run arp -a: {e}", "lines": []}


@app.get("/api/module")
async def api_get_module():
    mod = get_current_module()
    return {"module": mod, "description": "Single VLAN" if mod == 1 else "Dual VLAN"}


@app.post("/api/module")
async def api_set_module():
    mod = get_current_module()
    new_mod = 2 if mod == 1 else 1
    set_current_module(new_mod)
    return {"module": new_mod, "description": "Single VLAN" if new_mod == 1 else "Dual VLAN"}


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
