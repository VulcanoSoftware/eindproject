---
id: access-layer
title: Access Layer
---

# Access Layer

The access layer exposes the same storage namespace through multiple protocols for local and remote workflows.

## Protocol Gateway

```mermaid
flowchart LR
  subgraph Frontend
    CLIENTS[Apps, Backup Tools, Operators]
  end

  subgraph Backend
    GATE[Protocol Services]
    AUTH[Auth + Session Controls]
  end

  subgraph Storage
    VFS[Unified VFS Namespace]
    FUSE[FUSE]
    SFTP[SFTP]
    WEBDAV[WebDAV]
    S3[S3-Compatible API]
  end

  CLIENTS --> GATE --> AUTH --> VFS
  VFS --> FUSE
  VFS --> SFTP
  VFS --> WEBDAV
  VFS --> S3

  classDef frontend fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1px;
  classDef backend fill:#dcfce7,stroke:#15803d,color:#0f172a,stroke-width:1px;
  classDef storage fill:#ffedd5,stroke:#c2410c,color:#0f172a,stroke-width:1px;

  class CLIENTS frontend;
  class GATE,AUTH backend;
  class VFS,FUSE,SFTP,WEBDAV,S3 storage;
```

## Protocols

- FUSE: native mount behavior for local filesystem access.
- SFTP: secure remote file transfer and administration.
- WebDAV: web-friendly filesystem interoperability.
- S3-Compatible API: object-style integration for automation stacks.

<details>
<summary>Advanced details</summary>

- Protocol services can be enabled independently in configuration.
- Platform setup paths vary: WinFsp, libfuse, and macFUSE ecosystems.
- Preflight checks verify permissions and dependency readiness.

</details>

## Navigation

- [Back to Intro](./intro)

## Related Pages

- [Storage Layer](./storage-layer)
- [Configuration](./configuration)
- [Use Cases](./use-cases)
