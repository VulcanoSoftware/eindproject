# MultiDisk FileBalancer

A software-defined storage orchestration tool that distributes files across multiple disks while exposing them as a **single unified filesystem**.

Inspired by RAID 0 — but safer, more flexible, and fully software-based.

📚 **Full documentation:** [https://multidisk-filebalancer-docs.vercel.app/](https://multidisk-filebalancer-docs.vercel.app/)

---

## ⚠️ Platform Requirements

- **Linux only** — Windows and macOS are not supported.
- **WSL is not supported** — run the program inside a native Linux VM (e.g. Debian in VirtualBox).
- Root/sudo privileges are required for FUSE mounting and NFS.
- See the [Virtualisation Guide](https://multidisk-filebalancer-docs.vercel.app/virtualisation/) for a step-by-step VM setup.

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
- Monitors one or more input folders
- Moves files after a configurable minimum age
- Uses **round-robin disk selection**
- Verifies sufficient free space before moving each file

---

### 🧠 Advanced Cleanup System (Space Hunter)
- Automatically frees disk space when a threshold is reached
- Targets the oldest eligible files first
- Supports:
  - Recursive scanning
  - Folder exclusions
  - File lock detection
  - File stability checks (prevents deleting actively written files)
- Actions: delete or move to another location
- Safety features:
  - Dry-run mode
  - Configurable maximum actions per cycle
  - Minimum file age enforcement

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

#### NFS Server
- Network File System access via native Linux NFS
- Requires root privileges and `nfs-kernel-server` (installed automatically if missing)
- Can use the FUSE virtual mount as its root

---

### 📊 Startup Preflight Check
At launch, the application displays:
- OS and Python version
- Root/admin privilege status
- Enabled services (FUSE, WebDAV, SFTP, NFS)
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
- You will be guided through an interactive setup
- A `config.yml` file is generated automatically

---

## ⚙️ Configuration (Example)

```yaml
src: /media/storage/input

disks:
  - name: disk1
    path: /media/storage/out1
  - name: disk2
    path: /media/storage/out2
  - name: disk3
    path: /media/storage/out3

settings:
  min_file_age_hours: 1
  extra_safety_space_gb: 0
  scan_interval_seconds: 120
  space_check_default_min_free_gb: 3
  space_hunter_min_file_age_hours: 1
  space_hunter_dry_run: false
  space_hunter_max_actions_per_cycle: 0

space_hunter_disks:
  - action: delete
    min_free_gb: 3
    path: /media/storage/out1

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

webdav_server:
  enabled: true
  host: 0.0.0.0
  port: 8080
  username: root
  password: Password
  use_fuse_mount_as_root: true

sftp_server:
  enabled: true
  host: 0.0.0.0
  port: 8081
  username: root
  password: Password
  use_fuse_mount_as_root: true

nfs_server:
  enabled: false
  host: 0.0.0.0
  permitted: '*'
  use_fuse_mount_as_root: true

webhook_url: ''
```

---

## 🧠 How It Works

1. Load configuration
2. Perform startup preflight checks
3. Start optional services (FUSE, WebDAV, SFTP, NFS)
4. Enter main balancing loop:
   - Scan input folder(s)
   - Filter files by minimum age
   - Select target disk (round-robin, free space check)
   - Move file safely
5. Run background systems in parallel:
   - Space Hunter cleanup
   - Reverse RAID (if enabled)
   - Discord notifications

---

## ⚠️ Important Notes

- This is **NOT real RAID** — no data striping, no redundancy
- Each file lives entirely on one disk; there is no parity or replication
- FUSE requires `libfuse2` and root privileges
- NFS uses native Linux NFS and requires root privileges
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
config.yml                  # Auto-generated on first run
requirements.txt            # Python dependencies
```

---

## 🧩 Design Philosophy

- Keep deployment simple (single Python file)
- Avoid RAID complexity
- Maximize disk utilization
- Provide a unified filesystem view
- Be safe by default — no data striping

---

## 📌 Future Ideas

- Web management panel with GUI configuration
- Multiple configurable backup strategies
- Graceful degraded mode when disks go missing
- Automatic disk reintegration after reconnect
- Windows and macOS support
