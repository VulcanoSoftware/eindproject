# MultiDisk FileBalancer

> High-performance software-defined storage orchestration platform that distributes files across multiple disks while exposing them as a single unified filesystem.

Inspired by RAID 0 — but safer, more flexible, and fully software-based.

---

# 🚀 Overview

MultiDisk FileBalancer is designed for:

- Automated backup storage systems
- Multi-disk setups without RAID
- Media & archive servers
- Large-scale file ingestion workflows
- Users who want scalable storage without losing everything on disk failure

Unlike RAID 0, each file is stored entirely on a single disk.

👉 If a disk fails, only the files on that disk are affected — not the entire storage pool.

---

# 🧠 Architecture

FileBalancer is structured into several modular layers:

- File processing pipeline
- Storage aggregation layer
- Virtual filesystem abstraction
- Multi-protocol access layer
- Monitoring & recovery systems

This modular design allows flexible scaling, safer storage expansion, and future extensibility.

---

# 🏗️ Architecture Diagram

```mermaid
flowchart TB

%% =====================================================
%% USER LAYER
%% =====================================================

subgraph L1["USER INTERFACE"]
    direction LR

    UI1[Dashboard]
    UI2[Config GUI]
    UI3[File Manager]
    UI4[Backup Selector]
    UI5[Statistics]
    UI6[Disk Health]
end

%% =====================================================
%% API LAYER
%% =====================================================

subgraph L2["API LAYER"]
    direction LR

    API1[REST API]
    API2[Authentication]
    API3[Session Manager]
    API4[Realtime Events]
end

UI1 --> API1
UI2 --> API1
UI3 --> API1
UI4 --> API1
UI5 --> API1
UI6 --> API1

API1 --> API2 --> API3 --> API4

%% =====================================================
%% CORE LAYER
%% =====================================================

subgraph L3["CORE SERVICES"]
    direction LR

    C1[Config Loader]
    C2[Scheduler]
    C3[Disk Monitor]
    C4[Recovery Engine]
    C5[Notification System]
end

API4 --> C1 --> C2 --> C3 --> C4 --> C5

%% =====================================================
%% FILE PROCESSING
%% =====================================================

subgraph L4["FILE PROCESSING PIPELINE"]
    direction LR

    P1[Scanner]
    P2[Filter Engine]
    P3[Priority Queue]
    P4[Disk Selector]
    P5[File Mover]
    P6[Integrity Validator]
end

C2 --> P1
P1 --> P2 --> P3 --> P4 --> P5 --> P6

%% =====================================================
%% REDUNDANCY LAYER
%% =====================================================

subgraph L5["BACKUP & REDUNDANCY"]
    direction LR

    B1[Backup Strategy Engine]
    B2[Reverse RAID]
    B3[Parity Simulation]
    B4[Redundancy Layer]
    B5[Self-Healing Recovery]
end

P4 -.-> B1
B1 --> B2 --> B3 --> B4 --> B5
B5 -.-> P5
C4 -.-> B5

%% =====================================================
%% STORAGE LAYER
%% =====================================================

subgraph L6["STORAGE LAYER"]
    direction TB

    DS[(Storage Aggregation Layer)]

    subgraph DISKS["PHYSICAL STORAGE"]
        direction LR
        D1[(Disk 1)]
        D2[(Disk 2)]
        D3[(Disk 3)]
        D4[(Disk N)]
    end
end

P6 --> DS
C4 -.-> DS

DS --> D1
DS --> D2
DS --> D3
DS --> D4

%% =====================================================
%% VIRTUAL FILESYSTEM
%% =====================================================

subgraph L7["VIRTUAL FILESYSTEM"]
    direction LR

    V1[Path Mapping]
    V2[Namespace Manager]
    V3[Resolver]
    V4[Collision Resolver]
    V5[Metadata Cache]
end

DS --> V1 --> V2 --> V3 --> V4 --> V5

%% =====================================================
%% ACCESS LAYER
%% =====================================================

subgraph L8["ACCESS LAYER"]
    direction LR

    A1[FUSE]
    A2[SFTP]
    A3[WebDAV]
    A4[S3-Compatible API]
end

V5 --> A1
V5 --> A2
V5 --> A3
V5 --> A4

%% =====================================================
%% MONITORING
%% =====================================================

subgraph L9["MONITORING & ANALYTICS"]
    direction LR

    M1[Discord Webhooks]
    M2[Realtime Logs]
    M3[Usage Analytics]
    M4[Health Metrics]
end

C5 --> M1
P5 --> M2
P6 --> M3
C3 --> M4
```

---

# 🔥 Core Features

## 📦 Intelligent Multi-Disk Balancing

- Monitors one or multiple input folders
- Moves files after a configurable age
- Uses round-robin disk selection
- Ensures sufficient free space before moving
- Supports scalable multi-disk growth

---

## 🧠 Advanced Cleanup System (Space Hunter)

Automatically frees disk space when needed.

### Features

- Recursive scanning
- Folder exclusions
- File lock detection
- File stability checks
- Configurable cleanup policies

### Actions

- Delete files
- Move cold data elsewhere

### Safety Features

- Dry-run mode
- Minimum file age enforcement
- Maximum actions per cycle
- Active file protection

---

## 🔁 Reverse RAID (Optional)

Moves files back from storage disks to a central location.

Useful for:

- Reprocessing workflows
- Archival pipelines
- Migration operations
- Data consolidation

---

## 🧩 Virtual Filesystem (FUSE)

Combines all disks into one unified virtual folder.

### Features

- Merges directory structures
- Supports nested folders
- Collision-safe filename handling
- Metadata caching
- Transparent file access
- Path traversal protection

### Example

```text
file.txt → file__a1b2c3d4.txt
```

Applications interact with one unified storage layer while FileBalancer manages the physical disk layout underneath.

---

# 🌐 Multi-Protocol Access

The storage pool can be accessed simultaneously through:

| Protocol | Purpose |
|---|---|
| FUSE | Native filesystem mounting |
| SFTP | Secure remote file access |
| WebDAV | Web-based filesystem access |
| S3-Compatible API | Object storage integration |

Compatible with:

- Windows
- Linux
- macOS
- Rclone
- Nextcloud
- Backup systems
- Media servers

---

# ⚙️ FUSE Auto Setup

Automatically detects your operating system and attempts setup assistance.

### Supported Platforms

- Linux: `apt`, `dnf`, `pacman`
- Windows: `winget` (WinFsp)
- macOS: `brew` (macFUSE)

The system also detects:
- Permission issues
- Missing dependencies
- Unsupported environments

---

# 📊 Startup Preflight Check

At launch, the application displays:

- OS information
- Python version
- Privilege status
- Enabled services
- FUSE readiness
- Environment diagnostics

---

# 🔔 Monitoring & Notifications

## Discord Notifications

Send logs and events directly to a Discord webhook.

Useful for:

- Server monitoring
- Automated alerts
- Storage notifications
- Recovery warnings

## Monitoring Features

- Disk usage tracking
- Transfer logs
- Health metrics
- Usage analytics
- Recovery visibility

---

# 🛡️ Fault Tolerance

Unlike RAID 0, disk failure only affects files stored on the failed disk.

Additional safeguards include:

- File stability checks
- Corruption prevention
- Path validation
- Concurrent operation protection
- Degraded operation support
- Automatic disk reintegration support

---

# ⚡ Quick Start

```bash
pip install -r requirements.txt
python multidisk_filebalancer.py
```

On some systems:

```bash
pip install -r requirements.txt --break-system-packages
```

---

# 🧾 First Run

On first launch:

- Guided setup starts automatically
- A `config.yml` file is generated
- Optional services can be configured interactively

---

# ⚙️ Configuration Example

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

# 🧠 How It Works

1. Load configuration
2. Perform system preflight checks
3. Start optional services:
   - FUSE mount
   - WebDAV
   - SFTP
   - S3 API
4. Enter balancing loop:
   - Scan input folders
   - Filter eligible files
   - Select target disk
   - Move files safely
5. Run background systems:
   - Space Hunter cleanup
   - Monitoring
   - Reverse RAID workflows

---

# 🖥️ Supported Platforms

- Windows (WinFsp required)
- Linux (libfuse required)
- macOS (macFUSE required)

---

# 💡 Use Cases

- Automated backup servers
- Media storage systems
- Low-cost NAS environments
- Large archive pools
- Multi-disk home servers
- File ingestion pipelines

---

# 📁 Project Structure

```text
multidisk_filebalancer.py   # Main application
config.yml                  # Auto-generated configuration
requirements.txt            # Dependencies
```

---

# 🧩 Design Philosophy

- Keep deployment simple
- Avoid RAID complexity
- Maximize storage flexibility
- Provide unified filesystem access
- Prioritize safety over striping
- Remain modular and extensible

---

# 🏁 Summary

MultiDisk FileBalancer provides:

✅ Multi-disk storage without RAID  
✅ Unified filesystem abstraction  
✅ Intelligent balancing & cleanup  
✅ Multi-protocol access  
✅ Flexible automation workflows  
✅ Safer failure isolation  
✅ Modular architecture  

---

# 📌 Future Ideas

- Web dashboard
- Metrics & graphs
- File replication mode
- Distributed node support
- Smarter balancing algorithms
- Snapshot support
