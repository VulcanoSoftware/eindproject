# MultiDisk FileBalancer
<img width="1024" height="1024" alt="logo" src="https://github.com/user-attachments/assets/2afd73b5-bb1e-4d3d-ba74-299926c4a423" />
A software-defined storage orchestration tool that distributes files across multiple disks while exposing them as a **single unified filesystem**.

Inspired by RAID 0 — but safer, more flexible, and fully software-based.

📚 **Full documentation:** [https://docs.mdfb.vulcanocraft.com/](https://docs.mdfb.vulcanocraft.com/)

📚 **Showcase website:** [https://mdfb.vulcanocraft.com/](https://mdfb.vulcanocraft.com/)

---

## ⚠️ Platform Requirements

- **Linux only** — Windows and macOS are not supported.
- **WSL is not supported** — run the program inside a native Linux VM (e.g. Debian in VirtualBox).
- Root/sudo privileges are required for FUSE mounting and NFS.
- See the [Virtualisation Guide](https://docs.mdfb.vulcanocraft.com/virtualisation) for a step-by-step VM setup.

---

## 🚀 Overview

MultiDisk FileBalancer is designed for:

- Automated backup storage systems
- Multi-disk setups without RAID
- Servers handling large file inflow
- Users who want **scalable storage without losing everything on a single disk failure**

Unlike RAID 0, each file is stored entirely on one disk.

👉 If a disk fails, only the files on that disk are affected — not the entire storage pool.

---

## 🔥 Core Features

### 📦 Smart File Distribution

- Monitors one or more input folders (`src_folders`)
- Moves files after a configurable minimum age
- Supports multiple **backup strategies** (see below)
- Verifies sufficient free space before moving each file

#### Backup Strategies

Configured via `settings.backup_strategy`:

| Strategy | Description |
|---|---|
| `round_robin` | Cycles through disks in order (default) |
| `most_free_space` | Always picks the disk with the most free bytes |
| `least_used_pct` | Picks the disk with the lowest used percentage |
| `path_hash` | Deterministically assigns files to a disk based on their path hash |

#### RAID Simulation Modes

Configured via `settings.raid_simulation` — controls how files are replicated or distributed:

| Mode | Description |
|---|---|
| `none` / `raid0` | No replication — one copy per disk (default) |
| `raid1` / `mirror_2` | Mirror to 2 disks |
| `mirror_all` / `raid1_all` | Mirror to all disks |
| `raid5` | RAID 5 simulation |
| `raid6` | RAID 6 simulation |
| `raid10` | RAID 10 simulation |

---

### 🧠 Advanced Cleanup System (Space Hunter)

- Automatically frees disk space when a threshold is reached
- Targets the oldest eligible files first
- Supports:
  - Recursive scanning
  - Folder exclusions (global and per-disk)
  - File lock detection
  - File stability checks (prevents deleting actively written files)
- Actions: `delete` or `move` to another location
- Safety features:
  - Dry-run mode (global and per-disk)
  - Configurable maximum actions per cycle (global and per-disk)
  - Minimum file age enforcement (global and per-disk)
  - Global fallback cleanup when all configured disks are under pressure

---

### 🔁 Reverse RAID (Optional)

- Moves files **back from storage disks to a central source folder**
- Useful for:
  - Reprocessing workflows
  - Archival pipelines
  - Migration and data consolidation

---

### 🧩 Virtual Filesystem (FUSE)

Combines all disks into **one virtual folder**.

- Merges directory structures across disks
- Supports nested folders
- Resolves filename collisions automatically:
  ```
  file.txt → file__a1b2c3d4.txt
  ```
- Prevents path traversal attacks
- Metadata caching for performance

The result: all files are accessible as if they were on **one single disk**, regardless of their physical location.

---

### 🌐 Built-in Network Access

#### WebDAV Server
- Mount as a network drive
- Optional authentication
- Can use the FUSE virtual mount as its root

#### SFTP Server
- Secure file access over SSH
- Full filesystem interaction
- Works with the virtual filesystem
- Optional custom host key path (`host_key_path`); auto-generated Ed25519 + RSA keys if omitted

#### NFS Server
- Network File System access via native Linux NFS
- Requires root privileges and `nfs-kernel-server` (installed automatically if missing)
- Can use the FUSE virtual mount as its root
- Always uses port `2049`; custom ports are not supported

---

### 🖥️ Web Management Panel

A built-in web UI served by Flask at `http://<host>:5000` (configurable).

- **Dashboard:** live stats — files moved, bytes transferred, last action, disk usage charts, insights
- **Config editor:** view and save `config.yml` directly from the browser
- Uptime display and service status overview
- Accessible via `/` or `/panel`
- Configured via the `webpanel` section in `config.yml`

---

### 📂 File Browser (Docker)

An optional web-based file manager powered by [filebrowser/filebrowser](https://hub.docker.com/r/filebrowser/filebrowser), served via Docker.

- Serves the FUSE virtual mount point as its root
- Docker is installed automatically if missing
- Configurable port (default `8082`), username, and password
- State (database) stored in a persistent directory
- Configured via the `filebrowser` section in `config.yml`

> Requires Docker to be available on the host.

---

### 💾 Automount (External Drives)

Automatically detects and mounts USB and other external storage devices as they are plugged in.

- Uses `pyudev` to monitor kernel `block` events
- Mounts external partitions via `udisksctl` (installed automatically if missing)
- Supports USB, SD cards, and thumb drives
- Cooldown prevents duplicate mount attempts

> Requires `pyudev` (included in `requirements.txt`) and `udisksctl`.

---

### 📊 Startup Preflight Check

At launch, the application displays:

- OS and Python version
- Root/admin privilege status
- Enabled services (FUSE, WebDAV, SFTP, NFS, FileBrowser, Web Panel)
- FUSE readiness and install strategy

---

### 🔔 Discord Notifications

- Sends logs and events to a configured Discord webhook
- Useful for server monitoring, alerts, and automation feedback

---

## ⚡ Quick Start

```bash
pip install -r requirements.txt
python multidisk_filebalancer.py
```

On some systems:

```bash
pip install -r requirements.txt --break-system-packages
sudo python multidisk_filebalancer.py
```

---

## 🧾 First Run

On first launch:

- You will be guided through an interactive setup wizard
- A `config.yml` file is generated automatically
- You will be asked for: input folder(s), disk paths, Discord webhook, Space Hunter preferences, and web panel host/port

---

## ⚙️ Configuration (Example)

```yaml
# Source folders — supports multiple input paths
src_folders:
  - /media/storage/input

# Target disks in the pool
disks:
  - name: disk1
    path: /media/storage/out1
  - name: disk2
    path: /media/storage/out2
  - name: disk3
    path: /media/storage/out3

# Last used disk (automatically tracked)
last_disk: disk1

# Discord webhook (leave empty to disable)
webhook_url: ''

settings:
  min_file_age_hours: 4
  extra_safety_space_gb: 5
  scan_interval_seconds: 120
  console_clear_interval_hours: 6
  space_check_default_min_free_gb: 40

  # Disk selection strategy: round_robin | most_free_space | least_used_pct | path_hash
  backup_strategy: round_robin

  # RAID simulation: none/raid0 | raid1/mirror_2 | mirror_all | raid5 | raid6 | raid10
  raid_simulation: none

  # Space Hunter settings
  space_hunter_min_file_age_hours: 1
  space_hunter_exclude_folders: []
  space_hunter_dry_run: false
  space_hunter_max_actions_per_cycle: 0
  space_hunter_global_fallback: false

space_hunter_disks:
  - action: delete           # 'delete' or 'move'
    min_free_gb: 40
    path: /media/storage/out1
    move_destination: null   # required when action: move

reverse_raid:
  enabled: false
  source_paths:
    - /media/storage/out1
    - /media/storage/out2
  destination_path: /media/storage/input
  min_file_age_hours: 12
  run_interval_minutes: 10

fuse_server:
  enabled: true
  mount_point: /home/user/Desktop/mount
  upload_src: /media/storage/input

webdav_server:
  enabled: true
  host: 0.0.0.0
  port: 8080
  username: admin
  password: changeme
  upload_src: /media/storage/input
  use_fuse_mount_as_root: true

sftp_server:
  enabled: true
  host: 0.0.0.0
  port: 8081
  username: raiduser
  password: changeme
  upload_src: /media/storage/input
  use_fuse_mount_as_root: true

nfs_server:
  enabled: false
  host: 0.0.0.0
  port: 2049
  permitted: '*'
  upload_src: /media/storage/input
  use_fuse_mount_as_root: true

webpanel:
  enabled: true
  host: 0.0.0.0
  port: 5000

filebrowser:
  enabled: false
  port: 8082
  state_dir: /var/lib/multidisk-filebalancer/filebrowser
  username: admin
  password: changeme123456
  credentials_initialized: false
```

---

## 🧠 How It Works

1. Load configuration
2. Perform startup preflight checks
3. Start optional services (FUSE, WebDAV, SFTP, NFS, FileBrowser, Web Panel)
4. Start automount listener (USB/external drives)
5. Enter main balancing loop:
   - Scan input folder(s)
   - Filter files by minimum age
   - Select target disk based on chosen backup strategy
   - Apply RAID simulation (replication if configured)
   - Move file safely
6. Run background systems in parallel:
   - Space Hunter cleanup
   - Reverse RAID (if enabled)
   - Discord notifications

---

## ⚠️ Important Notes

- This is **NOT real RAID** — no hardware striping or parity by default
- Each file lives entirely on one disk unless a RAID simulation mode is configured
- FUSE requires `libfuse2` and root privileges
- NFS uses native Linux NFS and requires root privileges
- The FileBrowser integration requires Docker Engine on the host
- Admin/root is required for FUSE mounting and NFS exports

---

## 🖥️ Supported Platforms

| Platform | Support |
|---|---|
| Linux (native) | ✅ Fully supported |
| Linux VM (VirtualBox/VMware) | ✅ Recommended for non-Linux users |
| WSL | ❌ Not supported |
| Windows (native) | ❌ Not supported |
| macOS (native) | ❌ Not supported |

---

## 💡 Use Cases

- Automated backup storage servers
- Media servers with multiple drives
- Low-cost NAS setups without hardware RAID
- File ingestion pipelines
- Systems where per-disk failure isolation is acceptable

---

## 📁 Project Structure

```
multidisk_filebalancer.py   # Main application
webpanel.html               # Web management panel UI
webpanel.js                 # Web panel frontend logic
webpanel.css                # Web panel styles
config.yml                  # Auto-generated on first run
requirements.txt            # Python dependencies
```

---

## 📦 Dependencies

```
pyyaml        # Configuration parsing
requests      # Discord webhooks and HTTP
asyncssh      # SFTP server
fusepy        # FUSE virtual filesystem
wsgidav       # WebDAV server
cheroot       # WSGI server for WebDAV
flask         # Web management panel
pyudev        # USB/external drive automount
```

---

## 🧩 Design Philosophy

- Keep deployment simple (single Python file + static web assets)
- Avoid RAID complexity as the default
- Maximize disk utilization
- Provide a unified filesystem view
- Be safe by default — no data striping unless explicitly configured

---

## 📌 Future Ideas

- Multiple configurable backup strategies per disk
- Graceful degraded mode when disks go missing
- Automatic disk reintegration after reconnect
- Windows and macOS support
