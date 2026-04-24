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
flowchart TB

subgraph UI["WEB PANEL - FRONTEND"]
    UI1[Dashboard - graphs and statistics]
    UI2[Config GUI - edit config.yml]
    UI3[File Manager - Nextcloud-like]
    UI4[Backup Strategy Selector]
end

subgraph API["BACKEND API - CONTROL"]
    API1[REST API Controller]
    API2[Auth and Session Management]
end

subgraph CORE["CORE SYSTEM"]
    C1[Config Loader]
    C2[Main Scheduler]
end

subgraph PIPE["FILE PROCESSING PIPELINE"]
    P1[File Scanner]
    P2[Filter Engine]
    P3[Queue Manager]
    P4[Disk Selection Engine]
    P5[File Move Engine]
end

subgraph BACKUP["BACKUP STRATEGY ENGINE"]
    B1[Strategy Manager]
    B2[RAID-like Simulation]
    B3[Redundancy Logic]
end

subgraph STORAGE["PHYSICAL STORAGE"]
    D1[(Disk 1)]
    D2[(Disk 2)]
    D3[(Disk 3)]
end

subgraph FT["FAULT TOLERANCE SYSTEM"]
    F1[Disk Failure Detection]
    F2[Auto Recovery Engine]
    F3[Hot Re-Add Detection]
end

subgraph MGMT["STORAGE MANAGEMENT"]
    M1[Space Hunter]
    M2[Cleanup and Rebalancer]
end

subgraph VFS["VIRTUAL FILESYSTEM"]
    V1[Path Mapping Layer]
    V2[Unified Namespace]
    V3[Conflict Resolver]
end

subgraph ACCESS["ACCESS LAYER"]
    A1[FUSE Mount]
    A2[SFTP Server]
    A3[WebDAV Server]
end

UI1 --> API1
UI2 --> API1
UI3 --> API1
UI4 --> API1

API1 --> API2 --> C1 --> C2

C2 --> P1 --> P2 --> P3 --> P4 --> P5

P5 --> D1
P5 --> D2
P5 --> D3

D1 --> V1
D2 --> V1
D3 --> V1

V1 --> V2 --> V3

V3 --> A1
V3 --> A2
V3 --> A3

P4 --> B1 --> B2 --> B3 --> P5

F1 -.-> D1
F1 -.-> D2
F1 -.-> D3

F2 -.-> P5
F3 -.-> D1
F3 -.-> D2
F3 -.-> D3

M1 -.-> D1
M1 -.-> D2
M1 -.-> D3

M2 -.-> P3
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
