# FileBalancer Architecture (Advanced)

> Software-defined storage balancer with virtual filesystem abstraction

## Overview
This diagram represents a modular storage system with:
- Web interface (frontend)
- Backend control/API
- File processing pipeline
- Storage & virtual filesystem abstraction
- Fault tolerance & backup strategies

---


## Architecture Diagram

```mermaid
flowchart LR

%% ================= UI =================
subgraph UI["WEB PANEL"]
    UI1[Dashboard]
    UI2[Config GUI]
    UI3[File Manager]
    UI4[Backup Selector]
end

%% ================= API =================
subgraph API["BACKEND"]
    API1[REST API]
    API2[Auth]
end

%% ================= CORE =================
subgraph CORE["CORE"]
    C1[Config Loader]
    C2[Scheduler]
end

%% ================= PIPELINE =================
subgraph PIPE["PIPELINE"]
    P1[Scanner]
    P2[Filter]
    P3[Queue]
    P4[Disk Selector]
    P5[File Mover]
end

%% ================= BACKUP =================
subgraph BACKUP["BACKUP"]
    B1[Strategy]
    B2[RAID Sim]
    B3[Redundancy]
end

%% ================= STORAGE =================
subgraph STORAGE["DISKS"]
    D1[(Disk 1)]
    D2[(Disk 2)]
    D3[(Disk 3)]
end

%% Aggregation node (voorkomt wirwar)
DS[(Disk Layer)]

%% ================= VFS =================
subgraph VFS["VIRTUAL FS"]
    V1[Path Mapping]
    V2[Namespace]
    V3[Resolver]
end

%% ================= ACCESS =================
subgraph ACCESS["ACCESS"]
    A1[FUSE]
    A2[SFTP]
    A3[WebDAV]
end

%% ================= FLOW =================

UI1 --> API1
UI2 --> API1
UI3 --> API1
UI4 --> API1

API1 --> API2 --> C1 --> C2

C2 --> P1 --> P2 --> P3 --> P4 --> P5

%% Backup flow (netjes inline)
P4 --> B1 --> B2 --> B3 --> P5

%% Storage via centrale node (geen spaghetti meer)
P5 --> DS
DS --> D1
DS --> D2
DS --> D3

%% Terug via dezelfde node
D1 --> DS
D2 --> DS
D3 --> DS
DS --> V1

V1 --> V2 --> V3

V3 --> A1
V3 --> A2
V3 --> A3
```

---

## Key Concepts

- File-level distribution (not block-level like RAID)
- Virtual filesystem abstraction
- Multiple access protocols (FUSE, SFTP, WebDAV)
- Fault tolerance and recovery
- Configurable backup strategies
- Scalable architecture

---

## Summary

This system acts as a:

**Modular storage orchestration platform combining flexibility, accessibility, and automation without relying on traditional RAID.**
