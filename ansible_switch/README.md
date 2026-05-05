# Ansible Switch Manager 🔧

A fool-proof, interactive CLI tool for managing a network of switches using Ansible.
No real network hardware needed — runs entirely in local/dummy mode. Although it also works on detecting discovered devices in real time.

---

## 📡 Switch Topology

```
H1-B, H1-A  (Management)
 ├── A1-B  (Tier A - Port B)
 ├── A1-A  (Tier A - Port A)
 ├── B1-B  (Tier B - Port B)
 ├── B1-A  (Tier B - Port A)
 ├── C1-B  (Tier C - Port B)
 ├── C1-A  (Tier C - Port A)
 ├── D1-B  (Tier D - Port B)
 └── D1-A  (Tier D - Port A)
```

---

## 🚀 Requirements

| Requirement | Details |
|---|---|
| Python | 3.10+ (stdlib only — no pip install needed) |
| Ansible | `pip install ansible` |

Install Ansible if you haven't already:
```bash
pip install ansible
```

---

## ▶️ How to Run

```bash
# From the ansible_switch directory:
python menu.py
```

That's it. The interactive menu handles everything. Just make sure to open your folder first within the CLI.

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
| **0** | Exit |

---

## 📁 Project Structure

```
ansible_switch/
├── ansible.cfg                  # Project settings (local mode, yaml output)
├── menu.py                      # ← START HERE — interactive front-end
├── inventory/
│   └── hosts.ini                # All 10 switches + default dummy IPs
├── group_vars/
│   └── all.yml                  # Global vars (local connection, gateway)
├── host_vars/                   # Per-switch IPs (updated live by menu)
│   ├── H1-B.yml
│   ├── H1-A.yml
│   ├── A1-B.yml  …  D1-A.yml
├── playbooks/
│   ├── show_topology.yml        # Print switch tree with IPs
│   ├── assign_ip.yml            # Assign IP (-e "target=X new_ip=Y")
│   └── ping_check.yml           # Ping one or all switches
├── roles/
│   └── switch_common/
│       ├── defaults/main.yml    # Safe default values
│       └── tasks/main.yml       # IP validation + interface-up banner
└── templates/
    └── host_vars.j2             # Template used when writing new IPs
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
- **Run**: `python -m uvicorn web_app.app:app --host 0.0.0.0 --port 8000`
- **Access (from your browser)**: `http://localhost:8000`

---

## 💡 Notes

- All switches use **local connection** — no SSH or real hardware required.
- IPs assigned via the menu are **persisted** in `host_vars/<switch>.yml` files.
- Ping results show both **Ansible module** status and **OS-level ping** output,
  matching what you'd see in `cmd`.
- Some dummy IPs (e.g. `10.0.2.2`) will correctly show as **unreachable** via OS ping,
  which is expected behaviour in a demo environment.
- Since you can directly run ipconfig within the interface's options, there's almost no need to open up another **CLI**. 
- Sometimes it may be necessary to ping some devices or their subnets first so they show up on the [5] Live Network Discovery & Monitor table, this isn't a design mistake as much as it is a structural technicality where detecting them would require to overflood the network which is not recommended for a local.
- It's recommended to open only one interface (either web or CLI) at a time to avoid conflicts.