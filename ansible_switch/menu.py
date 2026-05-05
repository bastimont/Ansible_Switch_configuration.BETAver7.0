#!/usr/bin/env python3
"""
menu.py — Ansible Switch Manager
Interactive CLI front-end for the ansible_switch project.
Runs on Python 3 (stdlib only — no pip installs needed).
"""

import os
import re
import sys
import subprocess
import platform
import ipaddress
import time
import threading
import json

from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
# SWITCH TOPOLOGY DEFINITIONS — Two architecture modules
# Module 1: Single VLAN (H→G)
# Module 2: Dual interconnected VLAN (VLAN 1 + VLAN 2, connected via MAIN)
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
    # ── VLAN 1 (left side, descending from .253) ──
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
    # ── VLAN 2 (right side, ascending from .41) ──
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

# Path helpers — always relative to this script's directory
BASE_DIR           = os.path.dirname(os.path.abspath(__file__))
HOST_VARS_DIR      = os.path.join(BASE_DIR, "host_vars")
PLAYBOOKS_DIR      = os.path.join(BASE_DIR, "playbooks")
CONFIG_PAGE_IP_FILE = os.path.join(BASE_DIR, "config_page_ip.txt")
MODULE_FILE        = os.path.join(BASE_DIR, "module.txt")
DEFAULT_CONFIG_IP  = "192.168.0.1"

def get_current_module() -> int:
    try:
        with open(MODULE_FILE, "r") as f:
            val = int(f.read().strip())
            return val if val in (1, 2) else 1
    except (FileNotFoundError, ValueError):
        return 1

def set_current_module(mod: int) -> None:
    if mod not in (1, 2):
        return
    with open(MODULE_FILE, "w") as f:
        f.write(str(mod) + "\n")

def get_active_switches() -> list:
    return MODULE_1_SWITCHES if get_current_module() == 1 else MODULE_2_SWITCHES

SWITCHES = get_active_switches()
SWITCH_NAMES = [s["name"] for s in get_active_switches()]
IP_KEY = "switch_ip" if get_current_module() == 1 else "switch_ip_m2"
DISCOVERY_SUBNETS = ["192.168.100.0/24", "192.168.1.0/24", "10.0.1.0/24"]


def get_config_page_ip() -> str:
    try:
        with open(CONFIG_PAGE_IP_FILE, "r", encoding="utf-8") as f:
            ip = f.read().strip()
            return ip if ip else DEFAULT_CONFIG_IP
    except FileNotFoundError:
        return DEFAULT_CONFIG_IP


def set_config_page_ip(new_ip: str) -> bool:
    if not validate_ip(new_ip):
        return False
    with open(CONFIG_PAGE_IP_FILE, "w", encoding="utf-8") as f:
        f.write(new_ip + "\n")
    return True


# ──────────────────────────────────────────────────────────────────────────────
# COLOUR HELPERS (work on Windows 10+ and all POSIX terminals)
# ──────────────────────────────────────────────────────────────────────────────
if platform.system() == "Windows":
    os.system("")   # enable ANSI escape codes on Windows console
    # Force UTF-8 output so box-drawing / Unicode chars don't crash on cp1252 terminals
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
MAGENTA= "\033[95m"
DIM    = "\033[2m"


def c(text, color):
    return f"{color}{text}{RESET}"


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences to calculate visible string length."""
    return re.sub(r'\033\[[0-9;]*m', '', text)


def ljust_ansi(text: str, width: int, fillchar: str = ' ') -> str:
    """Pads a string containing ANSI codes to a visible width."""
    visible_len = len(strip_ansi(text))
    padding = max(0, width - visible_len)
    return text + (fillchar * padding)


# ──────────────────────────────────────────────────────────────────────────────
# host_vars I/O
# ──────────────────────────────────────────────────────────────────────────────
def read_host_var(switch_name: str, key: str, default: str = "N/A") -> str:
    """Parse a single key from a switch's host_vars YAML file (no pyyaml needed)."""
    path = os.path.join(HOST_VARS_DIR, f"{switch_name}.yml")
    if not os.path.isfile(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(rf"^\s*{re.escape(key)}\s*:\s*['\"]?(.+?)['\"]?\s*$", line)
            if m:
                return m.group(1).strip()
    return default


def get_ip_key() -> str:
    return "switch_ip" if get_current_module() == 1 else "switch_ip_m2"


def write_host_vars(switch_name: str, new_ip: str) -> None:
    """Overwrite the host_vars file for switch_name with the new IP (keep other fields)."""
    path = os.path.join(HOST_VARS_DIR, f"{switch_name}.yml")
    # Read existing vars to preserve extra fields
    existing_vars = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("---") or not line:
                    continue
                m = re.match(r"^([a-zA-Z_]\w*)\s*:\s*['\"]?(.*?)['\"]?\s*$", line)
                if m:
                    existing_vars[m.group(1)] = m.group(2)

    # Update IP (module-specific key)
    existing_vars[get_ip_key()] = new_ip
    # Ensure required fields exist
    existing_vars.setdefault("switch_role", "access")
    existing_vars.setdefault("switch_description", f"{switch_name} Switch")

    content = "---\n"
    for key, val in existing_vars.items():
        content += f'{key}: "{val}"\n'

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    # Also update inventory/hosts.ini to keep it in sync
    _update_inventory_ip(switch_name, new_ip)


def _update_inventory_ip(switch_name: str, new_ip: str) -> None:
    """Update the ansible_host for a switch in inventory/hosts.ini."""
    inv_path = os.path.join(BASE_DIR, "inventory", "hosts.ini")
    if not os.path.isfile(inv_path):
        return
    with open(inv_path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = rf"^({re.escape(switch_name)}\s+ansible_host=)\S+"
    new_content = re.sub(pattern, rf"\g<1>{new_ip}", content, flags=re.MULTILINE)
    if new_content != content:
        with open(inv_path, "w", encoding="utf-8") as f:
            f.write(new_content)


def wait_for_keypress() -> str:
    """Wait for a single keypress (cross-platform). Returns lowercase char."""
    if platform.system() == "Windows":
        import msvcrt
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getch()
                if char == b"\x03":
                    raise KeyboardInterrupt
                return char.decode("utf-8", errors="replace").lower()
            time.sleep(0.1)
    else:
        import select
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    char = sys.stdin.read(1)
                    if char == "\x03":
                        raise KeyboardInterrupt
                    return char.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# ──────────────────────────────────────────────────────────────────────────────
# DISPLAY HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def clear():
    os.system("cls" if platform.system() == "Windows" else "clear")


def print_banner():
    banner = r"""
  ╔══════════════════════════════════════════════════════════════╗
  ║          A N S I B L E   S W I T C H   M A N A G E R         ║
  ║                   Fool-Proof Network Tool                    ║
  ╚══════════════════════════════════════════════════════════════╝"""
    print(c(banner, CYAN + BOLD))
    print()


def print_topology():
    """Display the switch tree with current IPs read directly from host_vars."""
    config_ip = get_config_page_ip()
    mod = get_current_module()
    switches = get_active_switches()
    ip_key = get_ip_key()
    width = 58 if mod == 1 else 72
    mod_label = "Module 1 - Single VLAN" if mod == 1 else "Module 2 - Dual VLAN"

    print(c(f"  ┌─ TOPOLOGY ({mod_label}) {'─' * (width - 38 - len(mod_label))}┐", CYAN))

    if mod == 1:
        # Module 1: standard tree display
        prev_tier = None
        for sw in switches:
            ip   = read_host_var(sw["name"], ip_key, "—")
            role = read_host_var(sw["name"], "switch_role", "access")
            tier = sw["tier"]

            if tier != prev_tier:
                tier_label = f"  │  {'[ MGMT ]' if tier == 'MGMT' else f'[ Tier {tier} ]'}"
                print(c(tier_label, YELLOW))
                prev_tier = tier

            siblings = [s for s in switches if s["tier"] == tier]
            is_last  = siblings[-1]["name"] == sw["name"]
            connector = "  │    └──" if is_last else "  │    ├──"

            name_col = f"{sw['name']:<6}"
            ip_col   = f"IP: {ip:<15}"
            role_col = c(f"[{role}]", DIM)
            print(f"{c(connector, CYAN)} {c(name_col, BOLD)}  {c(ip_col, GREEN)}  {role_col}")
    else:
        # Module 2: three sections — VLAN 1, MGMT, VLAN 2
        vlan1 = [s for s in switches if s.get("vlan") == 1]
        mgmt  = [s for s in switches if s.get("vlan") == 0]
        vlan2 = [s for s in switches if s.get("vlan") == 2]

        # VLAN 1
        print(c("  │  [ VLAN 1 ]", CYAN))
        prev_tier = None
        for sw in vlan1:
            ip   = read_host_var(sw["name"], ip_key, "—")
            role = read_host_var(sw["name"], "switch_role", "access")
            tier = sw["tier"]
            if tier != prev_tier:
                print(c(f"  │    ── Tier {tier} ──", YELLOW))
                prev_tier = tier
            siblings = [s for s in vlan1 if s["tier"] == tier]
            is_last  = siblings[-1]["name"] == sw["name"]
            connector = "  │      └──" if is_last else "  │      ├──"
            name_formatted = f"{sw['name']:<6}"
            role_col = c(f"[{role}]", DIM)
            print(f"  {c(connector, CYAN)} {c(name_formatted, BOLD)}  {c(ip, GREEN)}  {role_col}")

        # MGMT (MAIN)
        for sw in mgmt:
            ip = read_host_var(sw["name"], ip_key, "—")
            print(c("  │  [ MGMT ]", YELLOW))
            name_formatted = f"{sw['name']:<6}"
            print(f"  {c('  │    └──', CYAN)} {c(name_formatted, BOLD)}  {c(ip, GREEN)}  {c('[management]', DIM)}")

        # VLAN 2
        print(c("  │  [ VLAN 2 ]", CYAN))
        prev_tier = None
        for sw in vlan2:
            ip   = read_host_var(sw["name"], ip_key, "—")
            role = read_host_var(sw["name"], "switch_role", "access")
            tier = sw["tier"]
            if tier != prev_tier:
                print(c(f"  │    ── Tier {tier} ──", YELLOW))
                prev_tier = tier
            siblings = [s for s in vlan2 if s["tier"] == tier]
            is_last  = siblings[-1]["name"] == sw["name"]
            connector = "  │      └──" if is_last else "  │      ├──"
            name_formatted = f"{sw['name']:<6}"
            role_col = c(f"[{role}]", DIM)
            print(f"  {c(connector, CYAN)} {c(name_formatted, BOLD)}  {c(ip, GREEN)}  {role_col}")

    print(c(f"  │  {'[ CONFIG PAGE ]'}  {c(config_ip, BOLD + GREEN)}", YELLOW))
    print(c(f"  └{'─' * width}┘", CYAN))
    print()


def print_menu():
    config_ip = get_config_page_ip()
    mod = get_current_module()
    mod_desc = "Single VLAN" if mod == 1 else "Dual VLAN"
    options = [
        ("1", "Reset all IPs to defaults (refresh topology)"),
        ("2", "Assign IP to a switch"),
        ("3", "Ping a switch"),
        ("4", "Ping ALL switches"),
        ("5", "Live Network Discovery & Monitor"),
        ("6", f"ipconfig / Config Page IP ({config_ip})"),
        ("7", "Traceroute (trace path to a host)"),
        ("8", "ARP table (arp -a)"),
        ("9", "Network connections (netstat -an)"),
        ("x", f"Toggle architecture module (current: [{mod}] {mod_desc})"),
        ("0", "Exit"),
    ]
    print(c("  OPTIONS", MAGENTA + BOLD))
    for key, label in options:
        print(f"    {c(f'[{key}]', YELLOW)}  {label}")
    print()


# ──────────────────────────────────────────────────────────────────────────────
# NETWORK DISCOVERY UTILITIES
# ──────────────────────────────────────────────────────────────────────────────
def get_local_subnets():
    """Detect active local subnets and IPs using ipconfig."""
    subnets = []
    ips = []
    try:
        output = subprocess.check_output(["ipconfig"], text=True, encoding="cp850")
        for line in output.splitlines():
            if "IPv4 Address" in line or "Dirección IPv4" in line:
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m:
                    ip = m.group(1)
                    if not ip.startswith("127."):
                        ips.append(ip)
                        parts = ip.split(".")
                        subnets.append(f"{parts[0]}.{parts[1]}.{parts[2]}.0/24")
    except Exception:
        pass
    # Always include standard discovery subnets
    for ds in DISCOVERY_SUBNETS:
        if ds not in subnets:
            subnets.append(ds)
    return list(set(subnets)), list(set(ips))


def get_arp_table():
    """Parse the system ARP table using PowerShell (Windows) or arp command."""
    devices = []
    try:
        if platform.system() == "Windows":
            # Get-NetNeighbor is reliable but returns the entire cache (including ghost entries)
            # We filter for states that imply a real connection.
            # 0: Unreachable, 1: Incomplete, 2: Probe, 3: Delay, 4: Stale, 5: Reachable, 6: Permanent
            cmd = ["powershell", "Get-NetNeighbor | Select-Object IPAddress, LinkLayerAddress, State | ConvertTo-Json"]
            output = subprocess.check_output(cmd, text=True, encoding="cp850")
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
                        devices.append({"ip": ip, "mac": mac})
        else:
            output = subprocess.check_output(["arp", "-a"], text=True)
            pattern = re.compile(r"\((\d+\.\d+\.\d+\.\d+)\) at ([0-9a-fA-F:]{17})")
            for line in output.splitlines():
                m = pattern.search(line)
                if m:
                    ip, mac = m.group(1), m.group(2).upper()
                    if mac not in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"):
                        devices.append({"ip": ip, "mac": mac})
    except Exception:
        # Fallback to simple regex if PS fails
        try:
            output = subprocess.check_output(["arp", "-a"], text=True, encoding="cp850")
            pattern = re.compile(r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F-]{17})")
            for line in output.splitlines():
                m = pattern.search(line)
                if m:
                    ip, mac = m.group(1), m.group(2).replace("-", ":").upper()
                    if mac not in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"):
                        devices.append({"ip": ip, "mac": mac})
        except: pass
    return devices


def background_ping_sweep(subnets, deep=False):
    """Populate ARP table by pinging IPs in the background."""
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


# ──────────────────────────────────────────────────────────────────────────────
# INPUT HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def prompt(msg: str) -> str:
    try:
        return input(f"  {c('▶', CYAN)} {msg}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return ""


def pick_switch(prompt_text: str = "Enter switch name (or number)") -> Optional[str]:
    """Show numbered list and let user pick by name or number."""
    switches = get_active_switches()
    ip_key = get_ip_key()
    names = [s["name"] for s in switches]
    print()
    for i, sw in enumerate(switches, 1):
        ip = read_host_var(sw["name"], ip_key, "—")
        print(f"    {c(str(i), YELLOW)}.  {sw['name']:<6}  {c(ip, GREEN)}")
    print()
    choice = prompt(prompt_text)
    if not choice:
        return None
    # Numeric selection
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(switches):
            return switches[idx]["name"]
        print(c("  ✗ Invalid number.", RED))
        return None
    # Name selection
    if choice in names:
        return choice
    print(c(f"  ✗ '{choice}' is not a known switch.", RED))
    return None


def validate_ip(ip_str: str) -> bool:
    try:
        ipaddress.IPv4Address(ip_str)
        return True
    except ValueError:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# ACTIONS
# ──────────────────────────────────────────────────────────────────────────────
def action_reset_ips():
    """Restore every switch's IP to its factory default and rewrite host_vars."""
    print(c("\n  ── RESET IPs TO DEFAULTS ─────────────────────────────────────", CYAN))
    print()
    for sw in get_active_switches():
        default_ip = sw["default_ip"]
        write_host_vars(sw["name"], default_ip)
        print(f"    {c('✔', GREEN)}  {c(sw['name'], BOLD):<6}  → {c(default_ip, GREEN)}")
    print()
    print(c("  ✅  All IPs have been reset to their default values.", GREEN + BOLD))
    input("\n  Press ENTER to continue...")

def action_assign_ip():
    print(c("\n  ── ASSIGN IP ─────────────────────────────────────────────────", CYAN))
    target = pick_switch("Select switch")
    if not target:
        return

    while True:
        new_ip = prompt(f"New IP address for {c(target, BOLD)}")
        if not new_ip:
            print(c("  ✗ Cancelled.", RED))
            return
        if validate_ip(new_ip):
            break
        print(c(f"  ✗ '{new_ip}' is not a valid IPv4 address. Try again.", RED))

    write_host_vars(target, new_ip)
    print(c(f"\n  ✅  {target} → IP set to {new_ip}", GREEN + BOLD))
    print(c("      (host_vars file updated — Ansible will use this on next run)", DIM))
    input("\n  Press ENTER to continue...")


# ──────────────────────────────────────────────────────────────────────────────
# REAL PING — calls the OS ping command and streams live output
# ──────────────────────────────────────────────────────────────────────────────
def _real_ping(host: str, count: int = 4) -> dict:
    """
    Execute a real system ping against `host` and stream output to the console.
    Returns dict with 'success' (bool), 'host_unreachable' (bool), and 'output_lines'.
    Works on Windows (ping -n) and Linux/macOS (ping -c).
    """
    is_windows = platform.system() == "Windows"
    # Build the ping command identical to what CMD / bash would run
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
        print(c("  ✗ 'ping' command not found on this system.", RED))
        return {"success": False, "host_unreachable": False}

    # Stream output line by line in real time
    assert proc.stdout is not None
    host_unreachable = False
    for raw_line in proc.stdout:
        line = raw_line.rstrip()
        lower = line.lower()
        # Colour-code based on content
        if any(kw in lower for kw in ("reply from", "bytes from")):
            print(f"    {GREEN}{line}{RESET}")
        elif "destination host unreachable" in lower:
            print(f"    {YELLOW}{line}{RESET}")
            host_unreachable = True
        elif any(kw in lower for kw in ("request timed out",
                                        "100% loss", "100% packet loss",
                                        "could not find host", "unknown host",
                                        "transmit failed")):
            print(f"    {RED}{line}{RESET}")
        elif any(kw in lower for kw in ("ping statistics", "packets:", "approximate",
                                        "minimum", "round-trip", "rtt", "packet loss")):
            print(f"    {DIM}{line}{RESET}")
        else:
            print(f"    {line}")

    proc.wait()

    if proc.returncode != 0:
        # Diagnostic check: Is the host on a different subnet?
        subnets, local_ips = get_local_subnets()
        target_subnet = ".".join(host.split(".")[:-1]) + ".0/24"
        if target_subnet not in subnets:
            print(f"\n    {YELLOW}⚠  DIAGNOSTIC: Subnet Mismatch Detected!{RESET}")
            print(f"    Your PC is on subnets: {', '.join(subnets)}")
            print(f"    The target {host} is on: {target_subnet}")
            print(f"    {DIM}Reason: Windows won't route packets to different subnets without a gateway.{RESET}")
            print(f"    {CYAN}Fix: Add an IP in the {target_subnet} range to your network adapter.{RESET}")

    return {"success": proc.returncode == 0, "host_unreachable": host_unreachable}


def action_ping(target_name: Optional[str] = None, ping_all: bool = False):
    """
    Perform a REAL ping to each switch's configured IP, or any custom host/IP.
    Uses the operating system's ping command — identical to running it in CMD.
    """
    if ping_all:
        # ── Ping ALL switches using their configured IPs ───────────────────────
        print(c("\n  ── PING ALL SWITCHES ─────────────────────────────────────────", CYAN))
        results = []
        ip_key = get_ip_key()
        for sw_name in [s["name"] for s in get_active_switches()]:
            ip = read_host_var(sw_name, ip_key, "")
            if not ip or ip in ("", "N/A", "—"):
                print(c(f"\n  ⚠  {sw_name}: no IP configured — skipping.", YELLOW))
                results.append((sw_name, ip, None))
                continue

            print()
            print(c(f"  ── {sw_name} ({ip})", YELLOW + BOLD))
            print(c("  " + "─" * 58, DIM))
            result = _real_ping(ip, count=2)          # 2 packets per host to keep it snappy
            if result["success"]:
                print(c("  ✅  Reachable", GREEN + BOLD))
            elif result.get("host_unreachable"):
                print(c("  ⚠  REACHABLE (host unreachable - connection blocked)", YELLOW + BOLD))
                print(f"    {YELLOW}⚠  DIAGNOSTIC: Host {ip} is reachable but actively rejecting connections.{RESET}")
            else:
                print(c("  ✗   Unreachable", RED + BOLD))
            results.append((sw_name, ip, result["success"]))

        # Summary table
        print()
        print(c("  ── SUMMARY ───────────────────────────────────────────────────", CYAN))
        for sw_name, ip, ok in results:
            if ok is None:
                status = c("NO IP ", YELLOW)
            elif ok:
                status = c("UP    ✅", GREEN + BOLD)
            else:
                status = c("DOWN  ❌", RED + BOLD)
            name_col = ljust_ansi(c(sw_name, BOLD), 14)
            ip_col   = ljust_ansi(c(ip or '—', DIM), 18)
            print(f"    {name_col}  {ip_col}              {status}")

    else:
        # ── Single target ──────────────────────────────────────────────────────
        print(c("\n  ── PING ──────────────────────────────────────────────────────", CYAN))
        print()
        print(f"    {c('[1]', YELLOW)}  Ping a switch (uses its configured IP)")
        print(f"    {c('[2]', YELLOW)}  Ping any device / hostname / IP address")
        print()
        mode = prompt("Choose ping mode")

        if mode == "1":
            # Pick from topology
            sw_name = target_name or pick_switch("Select switch to ping")
            if not sw_name:
                return
            ip = read_host_var(sw_name, get_ip_key(), "")
            if not ip or ip in ("", "N/A", "—"):
                print(c(f"\n  ⚠  {sw_name} has no IP configured. Assign one first.", YELLOW))
                input("\n  Press ENTER to continue...")
                return
            label = f"{sw_name} ({ip})"

        elif mode == "2":
            # Free-form host
            ip = prompt("Enter hostname or IP address to ping (e.g. 8.8.8.8 or google.com)")
            if not ip:
                return
            label = ip
            sw_name = None

        else:
            print(c("  ✗ Invalid choice.", RED))
            input("\n  Press ENTER to continue...")
            return

        count_str = prompt("How many ping packets? [default: 4]")
        count = int(count_str) if count_str.isdigit() and int(count_str) > 0 else 4

        print()
        print(c(f"  Pinging {label} with {count} packet(s) ...", YELLOW))
        print(c("  " + "─" * 58, DIM))

        result = _real_ping(ip, count=count)

        print(c("  " + "─" * 58, DIM))
        if result["success"]:
            print(c(f"  ✅  {label} is reachable.", GREEN + BOLD))
        elif result.get("host_unreachable"):
            print(c(f"  ⚠  {label} is REACHABLE (host unreachable - connection blocked)", YELLOW + BOLD))
        else:
            print(c(f"  ✗   {label} is unreachable or did not respond.", RED + BOLD))

    input("\n  Press ENTER to continue...")


def action_live_monitor():
    """Live-refreshing view of connected devices."""
    subnets, _ = get_local_subnets()
    background_ping_sweep(subnets)
    refresh_locked = False
    
    try:
        while True:
            clear()
            print_banner()
            status_line = "LIVE NETWORK MONITOR" if refresh_locked else "LIVE NETWORK MONITOR"
            lock_indicator = f" {c('[PAUSED]', YELLOW + BOLD)}" if refresh_locked else f" {c('[AUTO-REFRESH ON]', DIM)}"
            print(c(f"  ── {status_line}{lock_indicator} ───────────", CYAN + BOLD))
            print(c("  (Press Ctrl+C to return to main menu)", DIM))
            print()
            
            # Get current state
            arp_devices = get_arp_table()
            known_ips = {}
            for sw_name in [s["name"] for s in get_active_switches()]:
                ip = read_host_var(sw_name, get_ip_key(), "")
                if ip and ip not in ("", "N/A", "—"):
                    known_ips[ip] = sw_name
            
            # Table Header
            header = (
                f"    {ljust_ansi(c('STATUS', BOLD), 12)} "
                f"{ljust_ansi(c('IP ADDRESS', BOLD), 18)} "
                f"{ljust_ansi(c('MAC ADDRESS', BOLD), 20)} "
                f"{c('ASSIGNED TO', BOLD)}"
            )
            print(header)
            print(f"    {c('─' * 70, DIM)}")
            
            seen_ips = set()
            
            # Show known devices first
            for ip, name in known_ips.items():
                seen_ips.add(ip)
                # Check if it's in ARP
                in_arp = any(d["ip"] == ip for d in arp_devices)
                mac = next((d["mac"] for d in arp_devices if d["ip"] == ip), "??:??:??:??:??:??")
                
                status = c("ONLINE", GREEN) if in_arp else c("OFFLINE", RED)
                print(f"    {ljust_ansi(status, 12)} {ljust_ansi(c(ip, BOLD), 18)} {ljust_ansi(c(mac, DIM), 20)} {c(name, YELLOW)}")

            # Show other discovered devices (sorted by IP)
            other_devices = [d for d in arp_devices if d["ip"] not in seen_ips]
            try:
                other_devices.sort(key=lambda x: ipaddress.IPv4Address(x["ip"]))
            except:
                pass

            for dev in other_devices:
                status = c("DISCOVERED", CYAN)
                print(f"    {ljust_ansi(status, 12)} {ljust_ansi(c(dev['ip'], BOLD), 18)} {ljust_ansi(c(dev['mac'], DIM), 20)} {c('—', DIM)}")
            print()
            refresh_label = "[R] Unlock & Refresh" if refresh_locked else "[R] Refresh"
            toggle_label = "[F] Pause Auto-Refresh" if not refresh_locked else "[F] Resume Auto-Refresh"
            print(c(f"  Options: [A] Assign  {refresh_label}  [P] Ping  {toggle_label}  [Q] Back", YELLOW))
            
            # Wait indefinitely for a keypress (blocking)
            choice = wait_for_keypress()

            if choice == "q":
                return
            elif choice == "r":
                if refresh_locked:
                    refresh_locked = False
                subnets, _ = get_local_subnets()
                background_ping_sweep(subnets)
                continue
            elif choice == "f":
                refresh_locked = not refresh_locked
                continue
            elif choice == "p":
                if not other_devices:
                    print(c("  ⚠  No discovered devices to ping.", YELLOW))
                    time.sleep(1.5)
                    continue
                print()
                print(c("  Discovered devices:", CYAN))
                for i, dev in enumerate(other_devices, 1):
                    print(f"    {c(str(i), YELLOW)}.  {dev['ip']:<15}  {c(dev['mac'], DIM)}")
                print()
                ping_choice = prompt("Enter device number to ping")
                if not ping_choice:
                    continue
                if ping_choice.isdigit():
                    idx = int(ping_choice) - 1
                    if 0 <= idx < len(other_devices):
                        target_ip = other_devices[idx]["ip"]
                        print()
                        print(c(f"  Pinging {target_ip} (2 packets)...", YELLOW))
                        print(c("  " + "─" * 58, DIM))
                        ok = _real_ping(target_ip, count=2)
                        print(c("  " + "─" * 58, DIM))
                        if ok:
                            print(c(f"  ✅  {target_ip} is reachable.", GREEN + BOLD))
                        else:
                            print(c(f"  ✗  {target_ip} is unreachable — connection with host has likely been lost.", RED + BOLD))
                        time.sleep(2)
                        continue
                    print(c("  ✗ Invalid number.", RED))
                else:
                    print(c("  ✗ Invalid input. Enter a number.", RED))
                time.sleep(1.5)
                continue
            elif choice == "a":
                # Assignment logic
                print()
                target_ip = prompt("Enter the DISCOVERED IP to assign")
                if not target_ip: continue
                
                # Verify it's in the list
                if not any(d["ip"] == target_ip for d in arp_devices):
                    print(c(f"  ✗ IP '{target_ip}' not found in discovery list.", RED))
                    time.sleep(1.5)
                    continue
                
                target_sw = pick_switch(f"Assign {target_ip} to which switch?")
                if target_sw:
                    write_host_vars(target_sw, target_ip)
                    print(c(f"\n  ✅  {target_sw} now assigned to {target_ip}", GREEN + BOLD))
                    time.sleep(2)
            else:
                # Any other key: only refresh if not locked
                if refresh_locked:
                    continue
                subnets, _ = get_local_subnets()
                background_ping_sweep(subnets)
    except KeyboardInterrupt:
        pass


def action_ipconfig_menu():
    """Show ipconfig output and allow setting config page IP."""
    print(c("\n  ── SYSTEM IPCONFIG ───────────────────────────────────────────", CYAN))
    print()
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output(["ipconfig", "/all"], text=True, encoding="cp850")
        else:
            output = subprocess.check_output(["ifconfig"], text=True)
        for line in output.splitlines():
            print(f"    {line}")
    except Exception as e:
        print(c(f"  ✗ Failed to run ipconfig: {e}", RED))
    print()

    config_ip = get_config_page_ip()
    print(c(f"  Current config page IP: {c(config_ip, BOLD + GREEN)}", CYAN))
    while True:
        new_ip = prompt("Enter new config page IP (or blank to keep current)")
        if not new_ip:
            break
        if validate_ip(new_ip):
            set_config_page_ip(new_ip)
            print(c(f"  ✅  Config page IP updated to {new_ip}", GREEN + BOLD))
            input("\n  Press ENTER to continue...")
            return
        print(c(f"  ✗ '{new_ip}' is not a valid IPv4 address.", RED))


def action_arp_table():
    """Display the system ARP table (arp -a)."""
    print(c("\n  ── ARP TABLE (arp -a) ──────────────────────────────────────", CYAN))
    print()
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output(["arp", "-a"], text=True, encoding="cp850")
        else:
            output = subprocess.check_output(["arp", "-a"], text=True)
        for line in output.splitlines():
            lower = line.lower()
            if any(kw in lower for kw in ("interface", "internet", "physical", "address", "type")):
                print(f"    {c(line, CYAN)}")
            elif re.search(r"\d+\.\d+\.\d+\.\d+", line) and re.search(r"[0-9a-fA-F]{2}-[0-9a-fA-F]{2}", line):
                print(f"    {line}")
            else:
                print(f"    {c(line, DIM)}")
    except Exception as e:
        print(c(f"  ✗ Failed to run arp -a: {e}", RED))
    print()
    input("  Press ENTER to continue...")


def action_netstat():
    """Display active network connections (netstat -an)."""
    print(c("\n  ── NETWORK CONNECTIONS (netstat -an) ─────────────────────", CYAN))
    print()
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output(["netstat", "-an"], text=True, encoding="cp850")
        else:
            output = subprocess.check_output(["netstat", "-an"], text=True)
        for line in output.splitlines():
            lower = line.lower()
            # Highlight listening ports and established connections
            if "listening" in lower or "established" in lower:
                print(f"    {c(line, GREEN)}")
            elif "time_wait" in lower or "close_wait" in lower:
                print(f"    {c(line, YELLOW)}")
            elif any(kw in lower for kw in ("proto", "local", "foreign", "state")):
                print(f"    {c(line, CYAN)}")
            else:
                print(f"    {c(line, DIM)}")
    except Exception as e:
        print(c(f"  ✗ Failed to run netstat -an: {e}", RED))
    print()
    input("  Press ENTER to continue...")




def action_traceroute():
    """Run tracert/traceroute to a user-specified target with options."""
    print(c("\n  ── TRACEROUTE ────────────────────────────────────────────────", CYAN))
    print()
    print(c("  Enter the target (IP, hostname, or domain) and optional flags.", DIM))
    print(c("  Example: 8.8.8.8  |  google.com  |  -w 2000 8.8.8.8  |  -h 15 google.com", DIM))
    print()

    hostname_re = re.compile(r"^(?=.*[a-zA-Z])[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$")

    while True:
        raw = prompt("Target and flags (blank to go back)")
        if not raw:
            return

        parts = raw.split()

        # Find the target (first token that is a valid IP or hostname)
        # Everything else is treated as flags
        target = None
        extra_args = []
        for part in parts:
            if validate_ip(part) or hostname_re.match(part):
                if target is None:
                    target = part
                else:
                    extra_args.append(part)
            else:
                extra_args.append(part)

        if target is None:
            print(c(f"  ✗ No valid IP address or hostname found in '{raw}'.", RED))
            continue

        print()
        print(c(f"  Tracing route to {c(target, BOLD + YELLOW)} ...", CYAN))
        print(c("  " + "─" * 58, DIM))

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
            if proc.stdout:
                for raw_line in proc.stdout:
                    line = raw_line.rstrip()
                    lower = line.lower()
                    if any(kw in lower for kw in ("timed out", "request timed out", "* * *", "unreachable")):
                        print(f"    {c(line, RED)}")
                    elif any(kw in lower for kw in ("trace", "traceroute", "tracing", "route")):
                        print(f"    {c(line, CYAN)}")
                    elif any(kw in lower for kw in ("ms", "millisecond")):
                        print(f"    {c(line, GREEN)}")
                    else:
                        print(f"    {line}")
            proc.wait()
            print(c("  " + "─" * 58, DIM))

            if proc.returncode != 0:
                print(c(f"  ⚠  tracert exited with code {proc.returncode}", YELLOW))

        except FileNotFoundError:
            print(c("  ✗ 'tracert'/'traceroute' command not found.", RED))
        except Exception as e:
            print(c(f"  ✗ Error: {e}", RED))

        print()


# ──────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ──────────────────────────────────────────────────────────────────────────────
def main():
    while True:
        clear()
        print_banner()
        print_topology()
        print_menu()

        choice = prompt("Choose an option")

        if choice == "1":
            action_reset_ips()

        elif choice == "2":
            action_assign_ip()

        elif choice == "3":
            action_ping()

        elif choice == "4":
            action_ping(ping_all=True)

        elif choice == "5":
            action_live_monitor()

        elif choice == "6":
            action_ipconfig_menu()

        elif choice == "7":
            action_traceroute()

        elif choice == "8":
            action_arp_table()

        elif choice == "9":
            action_netstat()

        elif choice == "x" or choice == "X":
            mod = get_current_module()
            new_mod = 2 if mod == 1 else 1
            set_current_module(new_mod)
            desc = "Single VLAN" if new_mod == 1 else "Dual VLAN"
            print(c(f"\n  ✅  Switched to Module {new_mod} ({desc}). IPs and switch list updated.", GREEN + BOLD))
            input("\n  Press ENTER to continue...")

        elif choice == "0":
            clear()
            print(c("\n  👋  Goodbye!\n", CYAN + BOLD))
            sys.exit(0)

        else:
            print(c("  ✗ Invalid option. Press ENTER and try again.", RED))
            input()


if __name__ == "__main__":
    main()
