# 💾 Storage Layer & VFS

## Overview

Combines multiple disks into one virtual filesystem.

## Flow

``` mermaid
flowchart TB
    Files --> Aggregation
    Aggregation --> Disk1
    Aggregation --> Disk2
    Aggregation --> DiskN
    Aggregation --> VFS
```

## Features

-   Disk aggregation
-   Virtual filesystem
-   Metadata caching
-   Collision handling

## 🔗 Related

-   🔄 [Pipeline](pipeline.md)
-   🌐 [Access](access.md)

🔙 [Back to overview](../README.md)
