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

  UX --> UI --> API --> CORE --> PROC --> AGG --> VFS --> PROTO

  classDef frontend fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1px;
  classDef backend fill:#dcfce7,stroke:#15803d,color:#0f172a,stroke-width:1px;
  classDef storage fill:#ffedd5,stroke:#c2410c,color:#0f172a,stroke-width:1px;

  class UI,UX frontend;
  class API,CORE,PROC backend;
  class AGG,VFS,PROTO storage;
```

## Component Boundaries

- Frontend handles user interaction and operational visibility.
- Backend handles orchestration, policy decisions, integrity, and recovery.
- Storage handles placement, namespace unification, metadata, and protocol serving.

<details>
<summary>Advanced details</summary>

- Monitoring and notification paths are attached to backend and pipeline events.
- Backup/redundancy workflows integrate with disk selection and recovery loops.
- Design supports optional services without changing the core balancing loop.

</details>

## Navigation

- [Back to Intro](./intro)

## Related Pages

- [Core Services](./core-services)
- [Processing Pipeline](./processing-pipeline)
- [Storage Layer](./storage-layer)
