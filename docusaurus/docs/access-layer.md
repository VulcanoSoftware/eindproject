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
    NFS[NFS via Docker]
  end

  CLIENTS --> GATE --> AUTH --> VFS
  VFS --> FUSE
  VFS --> SFTP
  VFS --> WEBDAV
  VFS --> NFS

  classDef frontend fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1px;
  classDef backend fill:#dcfce7,stroke:#15803d,color:#0f172a,stroke-width:1px;
  classDef storage fill:#ffedd5,stroke:#c2410c,color:#0f172a,stroke-width:1px;

  class CLIENTS frontend;
  class GATE,AUTH backend;
  class VFS,FUSE,SFTP,WEBDAV,NFS storage;
```

## Protocols

### FUSE
Native mount behaviour for local filesystem access. Requires `libfuse2` and the Python `fusepy` binding. The program attempts to install `libfuse` automatically if it is missing. Requires root privileges.

### SFTP
Secure remote file transfer and administration via SSH/SFTP (asyncssh). Supports read, write, delete, and directory operations on the virtual namespace. Default port: `8081`.

### WebDAV
Web-friendly filesystem interoperability (wsgidav + cheroot). Compatible with Windows Explorer, macOS Finder, and backup tools. Default port: `8080`.

### NFS
Network File System via a Docker container. Requires Docker Engine on the host machine. Exports the VFS root as `/nfsshare`. Mount tip: `mount <server-ip>:/ /mnt/nfs`. Default port: `2049`.

> **Note:** The S3-compatible API (`s3_server`) has been removed from the program. Older `config.yml` files containing an `s3_server` section are automatically migrated and that section is dropped.

<details>
<summary>Advanced details</summary>

- Protocol services can be enabled independently in the configuration.
- When `use_fuse_mount_as_root: true`, the protocol server serves the FUSE mount point as its root — FUSE must be enabled and running first.
- SFTP automatically generates an Ed25519 or RSA host key if no `host_key_path` is configured.
- SFTP explicitly warns when the server is bound only to `127.0.0.1`, which blocks external connections.
- Preflight checks verify permissions and dependency readiness for each service.

</details>

## Navigation

- [Back to Intro](./intro)

## Related Pages

- [Storage Layer](./storage-layer)
- [Configuration](./configuration)
- [Use Cases](./use-cases)
