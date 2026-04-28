# MultiDisk FileBalancer

A high-performance file distribution and virtual storage system that spreads files across multiple disks, while exposing them as a **single unified filesystem**.

Inspired by RAID 0 — but safer, more flexible, and fully software-based.

---

## 🚀 Overview

MultiDisk FileBalancer is designed for:

- Automated backup storage systems  
- Multi-disk setups without RAID  
- Servers handling large file inflow  
- Users who want **scalable storage without losing everything on disk failure**

Instead of striping data like RAID 0, each file is stored entirely on one disk.

👉 If a disk fails, only the files on that disk are lost — not everything.

---

## 🔥 Core Features

### 📦 Smart File Distribution
- Monitors one or multiple input folders
- Moves files after a configurable age
- Uses **round-robin disk selection**
- Ensures sufficient free space before moving

---

### 🧠 Advanced Cleanup System (Space Hunter)
- Automatically frees disk space when needed
- Finds the **oldest eligible files**
- Supports:
  - recursive scanning
  - folder exclusions
  - file lock detection
  - file stability checks (prevents deleting active files)
- Actions:
  - delete
  - move to another location
- Safety features:
  - dry-run mode
  - max actions per cycle
  - minimum file age enforcement

---

### 🔁 Reverse RAID (Optional)
- Moves files **back from disks to a central location**
- Useful for:
  - reprocessing
  - archiving
  - migration workflows

---

### 🧩 Virtual Filesystem (FUSE)

One of the most powerful features:

👉 Combines all disks into **one virtual folder**

#### Features:
- Merges directory structures across disks
- Supports nested folders
- Resolves filename conflicts automatically:
  ```
  file.txt → file__a1b2c3d4.txt
  ```
- Prevents path traversal attacks
- Includes intelligent caching for performance

#### Result:
You can access all your files as if they are on **one single disk**, even though they are physically spread out.

---

### 🌐 Built-in Network Access

#### WebDAV Server
- Mount as network drive
- Optional authentication
- Can use FUSE mount as root

#### SFTP Server
- Secure file access over SSH
- Full filesystem interaction
- Works with the virtual filesystem

#### S3-Compatible API
- Lightweight S3-like interface
- Supports:
  - file upload (PUT)
  - file download (GET)
  - delete
  - bucket listing

---

### ⚙️ FUSE Auto Setup
- Detects your OS
- Attempts automatic installation:
  - Linux: `apt`, `dnf`, `pacman`
  - Windows: `winget` (WinFsp)
  - macOS: `brew` (macFUSE)
- Detects permission issues and guides user

---

### 📊 Startup Preflight Check
At launch, the app shows:
- OS info
- Python version
- privilege status
- enabled features
- FUSE readiness

---

### 🔔 Discord Notifications
- Sends logs and events to a webhook
- Useful for:
  - server monitoring
  - alerts
  - automation feedback

---

## ⚡ Quick Start

```bash
pip install -r requirements.txt
python multidisk_filebalancer.py
```

On some systems:

```bash
pip install -r requirements.txt --break-system-packages
```

---

## 🧾 First Run

On first launch:
- You’ll be guided through setup
- A `config.yml` file will be created automatically

---

## ⚙️ Configuration (Example)

```yaml
src_folders:
  - "D:\\Input1"
  - "D:\\Input2"

disks:
  - name: "disk1"
    path: "E:\\Storage1"
  - name: "disk2"
    path: "F:\\Storage2"

settings:
  min_file_age_hours: 4
  extra_safety_space_gb: 5
  scan_interval_seconds: 120

space_hunter_disks:
  - action: delete
    min_free_gb: 40
    path: "E:\\Storage1"

fuse_server:
  enabled: true
  mount_point: "D:\\mount"

sftp_server:
  enabled: true
  port: 2222

webdav_server:
  enabled: false

s3_server:
  enabled: true
  port: 9000
  bucket_name: "storage"
```

---

## 🧠 How It Works (Technical)

1. Load configuration  
2. Perform system preflight checks  
3. Start optional services:
   - FUSE mount
   - WebDAV
   - SFTP
   - S3 API  
4. Enter main loop:
   - scan input folders
   - filter by file age
   - distribute files across disks
   - enforce free space rules  
5. Run background systems:
   - Space Hunter cleanup
   - Reverse RAID (if enabled)

---

## ⚠️ Important Notes

- This is **NOT real RAID**
- No redundancy — each file exists on one disk only
- FUSE requires system-level support
- Admin/root privileges may be required
- Performance depends on disk speed and OS

---

## 🖥️ Supported Platforms

- Windows (WinFsp required for FUSE)
- Linux (libfuse required)
- macOS (macFUSE required)

---

## 💡 Use Cases

- Automated backup storage servers  
- Media servers with multiple drives  
- Low-cost NAS setups without RAID  
- Systems where partial failure is acceptable  

---

## 📁 Project Structure

```
multidisk_filebalancer.py   # Main application
config.yml                  # Auto-generated configuration
requirements.txt            # Dependencies
```

---

## 🧩 Key Design Philosophy

- Keep it simple to deploy  
- Avoid RAID complexity  
- Maximize disk utilization  
- Provide a unified filesystem view  
- Be safe by default (no data striping)

---

## 🏁 Summary

MultiDisk FileBalancer gives you:

✅ Multi-disk storage without RAID  
✅ Unified filesystem (via FUSE)  
✅ Built-in network protocols  
✅ Smart cleanup automation  
✅ High flexibility for server environments  

---

## 📌 Future Ideas

- Web dashboard  
- Metrics & graphs  
- Cluster / multi-node support  
- File replication mode (RAID-like redundancy)
