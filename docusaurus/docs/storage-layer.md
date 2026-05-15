---
id: storage-layer
title: Storage Layer
---

# Storage Layer

The storage layer aggregates multiple physical disks and exposes a unified virtual namespace.

## Aggregation And VFS

```mermaid
flowchart TB
  subgraph Frontend
    VIEW[Unified Folder View]
  end

  subgraph Backend
    MAP[Path Mapping]
    META[Metadata Cache]
    RESOLVE[Collision Resolver]
  end

  subgraph Storage
    AGG[Disk Aggregation]
    PHYS[Physical Disks]
    VFS[Virtual Filesystem]
  end

  AGG --> PHYS
  AGG --> VFS
  VFS --> MAP --> RESOLVE --> META --> VIEW

  classDef frontend fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1px;
  classDef backend fill:#dcfce7,stroke:#15803d,color:#0f172a,stroke-width:1px;
  classDef storage fill:#ffedd5,stroke:#c2410c,color:#0f172a,stroke-width:1px;

  class VIEW frontend;
  class MAP,META,RESOLVE backend;
  class AGG,PHYS,VFS storage;
```

## Components

- Disk Aggregation: normalizes disk pool behavior across independent devices.
- Physical Disks: hold full files; no striping across disks.
- Virtual Filesystem (VFS): provides one logical directory namespace.
- Path Mapping: maps virtual paths to physical locations.
- Metadata Handling: caches access metadata for faster resolution.
- Collision Resolver: prevents filename conflicts deterministically.

<details>
<summary>Advanced details</summary>

- Path traversal protections defend against unsafe path construction.
- Degraded mode continues serving healthy disks during partial failure.
- Reintegration can restore full pool visibility after disk recovery.

</details>

## Navigation

- [Back to Intro](./intro)

## Related Pages

- [Architecture](./architecture)
- [Access Layer](./access-layer)
- [Configuration](./configuration)
