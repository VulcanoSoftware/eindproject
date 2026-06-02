---
id: architecture
title: Architecture
---

# Architecture

The architecture is intentionally split into Frontend, Backend, and Storage to keep responsibilities clear and scalable.

## Layered Architecture

```mermaid
flowchart TB
  subgraph Frontend
    UI[Dashboard + Config + Stats]
    WP[Web Panel — Flask port 5000]
    UX[Operator Actions]
  end

  subgraph Backend
    API[API + Auth + Sessions]
    CORE[Core Services]
    PROC[File Processing]
  end

  subgraph Storage
    AGG[Disk Aggregation]
    VFS[Virtual Filesystem]
    PROTO[Access Protocols]
  end

  UX --> UI --> API
  UX --> WP --> API
  API --> CORE --> PROC --> AGG --> VFS --> PROTO

  classDef frontend fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1px;
  classDef backend fill:#dcfce7,stroke:#15803d,color:#0f172a,stroke-width:1px;
  classDef storage fill:#ffedd5,stroke:#c2410c,color:#0f172a,stroke-width:1px;

  class UI,WP,UX frontend;
  class API,CORE,PROC backend;
  class AGG,VFS,PROTO storage;
```

## Component Boundaries

- **Frontend** handles user interaction and operational visibility, including the built-in Flask web panel.
- **Backend** handles orchestration, policy decisions, integrity, and recovery.
- **Storage** handles placement, namespace unification, metadata, and protocol serving.

<details>
<summary>Advanced details</summary>

- Monitoring and notification paths (including Discord webhooks) are attached to backend and pipeline events.
- Backup/redundancy workflows integrate with disk selection and recovery loops.
- Design supports optional services without changing the core balancing loop.
- The NFS service uses the Linux kernel NFS server (`nfs-kernel-server`) — Docker is **not** required.
- The Web Panel (Flask) runs as a daemon thread and exposes `/api/stats` and `/api/config` endpoints.

</details>

## Navigation

- [Back to Intro](./intro)

## Related Pages

- [Core Services](./core-services)
- [Processing Pipeline](./processing-pipeline)
- [Storage Layer](./storage-layer)
- [Access Layer](./access-layer)
