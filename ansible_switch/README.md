# Ansible Switch Manager 🔧

A fool-proof, interactive CLI/web page tool for managing a network of switches using Ansible.
No real network hardware needed — runs entirely in local/dummy mode. Although it also works on detecting discovered devices in real time.
Its main objective is providing the user with a friendly framework mapping interface.

---

## 📡 Switch Topology

Module 1:
```
MAIN ── (MANAGEMENT) 
 ├── H1-B  (Tier H - Port B)
 ├── H1-A  (Tier H - Port A)
 ├── A1-B  (Tier A - Port B)
 ├── A1-A  (Tier A - Port A)
 ├── B1-B  (Tier B - Port B)
 ├── B1-A  (Tier B - Port A)
 ├── C1-B  (Tier C - Port B)
 ├── C1-A  (Tier C - Port A)
 ├── D1-B  (Tier D - Port B)
 └── D1-A  (Tier D - Port A)
└── CONFIG  (Website/config page of the only managed Switch, customizable and is directly linked within the web interface)
```
Module 2:
```
[VLAN 1]
├── H1-B  (Tier H - Port B)
├── H1-A  (Tier H - Port A)
├── A1-B  (Tier A - Port B)
├── A1-A  (Tier A - Port A)
├── B1-B  (Tier B - Port B)
├── B1-A  (Tier B - Port A)
├── C1-B  (Tier C - Port B)
├── C1-A  (Tier C - Port A)
├── D1-B  (Tier D - Port B)
├── D1-A  (Tier D - Port A)
├── E1-B  (Tier E - Port B)
├── E1-A  (Tier E - Port A)
├── F1-B  (Tier F - Port B)
├── F1-A  (Tier F - Port A)
├── G1-B  (Tier G - Port B)
└── G1-A  (Tier G - Port A)

[VLAN 2]
MAIN ── (MANAGEMENT) 
├── H2-B  (Tier H - Port B)
├── H2-A  (Tier H - Port A)
├── A2-B  (Tier A - Port B)
├── A2-A  (Tier A - Port A)
├── B2-B  (Tier B - Port B)
├── B2-A  (Tier B - Port A)
├── C2-B  (Tier C - Port B)
├── C2-A  (Tier C - Port A)
├── D2-B  (Tier D - Port B)
├── D2-A  (Tier D - Port A)
├── E2-B  (Tier E - Port B)
├── E2-A  (Tier E - Port A)
├── F2-B  (Tier F - Port B)
├── F2-A  (Tier F - Port A)
├── G2-B  (Tier G - Port B)
├── G2-A  (Tier G - Port A)
└── CONFIG  (Website/config page of the only managed Switch, customizable and is directly linked within the web interface)

```

---

## 🚀 Requirements

| Requirement | Details |
|---|---|
| Python | 3.10+ (stdlib only — no pip install needed) |
| Ansible | `pip install ansible` |
| FastAPI | `pip install -r requirements txt` (once you open the directory of your project within CLI) |
| Uvicorn | Same as above🧐 |
| Pydantic | 👆 |

Install Ansible if you haven't already:
```bash
pip install ansible
```

---

## ▶️ How to Run (CLI version)

```bash
# From the ansible_switch directory:
python menu.py
```

That's it. The interactive menu handles everything. Just make sure to open your folder within the CLI by making use of the 'cd:\..' input first.

---

## 📋 Menu Options

| Option | What it does |
|---|---|
| **1** | Refresh and display the full switch topology with current IPs |
| **2** | Assign a dummy IP address to any switch (updates `host_vars`) |
| **3** | Ping a single switch (real OS-level ping, like `cmd`) |
| **4** | Ping **all** switches at once |
| **5** | Live Network Discovery & Monitor |
| **6** | ipconfig (displays IP addresses of all network adapters) |
| **7** | Traceroute (tracks the route of a server or switch or device) |
| **8** | ARP table (shows the current connections via the arp -a command) |
| **0** | Exit |

---

## 📁 Project Structure

```
ansible_switch/
├── ansible.cfg                  # Project settings (local mode, yaml output)
├── menu.py                      # CLI Manager — Main entry point for terminal
├── config_page_ip.txt           # NEW — Stores the custom IP for the web config page
├── requirements.txt             # Core dependencies (FastAPI, Uvicorn, etc.)
├── inventory/
│   └── hosts.ini                # All 11 switches (MAIN + Tiers H, A, B, C, D)
├── group_vars/
│   └── all.yml                  # Global vars (local connection, gateway)
├── host_vars/                   # Per-switch YAML files (updated live by Menu or Web)
│   ├── MAIN.yml                 # Management switch configuration
│   ├── H1-B.yml, H1-A.yml       # Tier H configurations
│   └── A1-B.yml … D1-A.yml      # Tier A through D configurations
├── playbooks/
│   ├── show_topology.yml        # Print switch tree with current IPs
│   ├── assign_ip.yml            # Assign IP (-e "target=X new_ip=Y")
│   └── ping_check.yml           # Connectivity check for one or all
├── roles/
│   └── switch_common/           # Shared Ansible logic for all switches
├── templates/
│   └── host_vars.j2             # Template used when writing new IP configurations
└── web_app/                     # NEW — FastAPI Web Interface
    ├── app.py                   # Web backend (Replicates CLI in browser)
    ├── start.bat                # Shortcut to launch the web server
    ├── static/                  # UI assets (CSS, Images, JavaScript)
    └── templates/               # Web pages (index.html, etc.)

```

---

## 🛠️ Running Playbooks Directly

You can also run playbooks from the terminal without the menu:

```bash
# Show topology
ansible-playbook playbooks/show_topology.yml

# Assign an IP to A1-B
ansible-playbook playbooks/assign_ip.yml -e "target=A1-B new_ip=192.168.1.50"

# Ping a single switch
ansible-playbook playbooks/ping_check.yml -e "target=B1-A"

# Ping all switches
ansible-playbook playbooks/ping_check.yml
```

---

## 🖥️ Web App

- **Open the Folder from your computer (e.g.)**: `C:\Users\user\Desktop\ansible_switch_configuration.ver6-main\ansible_switch`
- **Note**: You need to have **fastapi** and **uvicorn** installed. ( `pip install -r web_app/requirements.txt` )
- **Run**: Either `start.bat` or `python -m uvicorn web_app.app:app --host 0.0.0.0 --port 8000` are valid.
- **Access (from your browser)**: `http://localhost:8000`

---

## 💡 Notes

- All switches use **local connection** — no SSH or real hardware required.
- IPs assigned via the menu are **persisted** in `host_vars/<switch>.yml` files.
- Ping results show both **Ansible module** status and **OS-level ping** output,
  matching what you'd see in `cmd`.
- Some dummy IPs (e.g. `10.0.2.2`) will correctly show as **unreachable** via OS ping,
  which is expected behaviour in a demo environment.
- Since you can directly run ipconfig within the interface's options, there's almost no need to open up another **CLI**. This covers up almost everything you could need by intentional design.
- In case you want to log off at any point randomly in the **CLI** version, all you need to do is press Ctrl + C (funny copy button), then run python menu.py again if you wish to enter again.
- Pings *can* be unreasonably slow sometimes, be patient and nothing will break.
- Sometimes it may be necessary to ping a few devices or their subnets first so they show up on the [5] Live Network Discovery & Monitor table, this isn't a design mistake as much as it is a structural technicality where detecting them would require to overflow the network which is **NOT** recommended for a local. If you already know the subnet beforehand, it should be fairly easy to make them display on the screen, or by tracing their whole network flow.
- This version for Windows has already been bugfixed and tested, a Linux run would be purely experimental yet doable at the moment.
- It's recommended to open only one interface (either web or CLI) at a time to avoid conflicts.
