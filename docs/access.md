# 🌐 Access Layer

## Overview

Provides multiple ways to access the storage system.

## Flow

``` mermaid
flowchart LR
    VFS --> FUSE
    VFS --> SFTP
    VFS --> WebDAV
    VFS --> S3
```

## Protocols

-   FUSE: local mount
-   SFTP: remote access
-   WebDAV: web-based
-   S3: object storage

## 🔗 Related

-   💾 [Storage](storage.md)

🔙 [Back to overview](../README.md)
