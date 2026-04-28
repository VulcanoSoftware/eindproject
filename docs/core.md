# 🧠 Core Services

## Overview

Core services handle scheduling, monitoring and recovery.

## Flow

``` mermaid
flowchart LR
    Config --> Scheduler
    Scheduler --> DiskMonitor
    DiskMonitor --> Recovery
```

## Components

### Scheduler

-   Triggers tasks
-   Manages intervals

### Disk Monitor

-   Tracks health
-   Detects failures

### Recovery Engine

-   Handles reintegration
-   Restores metadata

## 🔗 Related

-   🔄 [Pipeline](pipeline.md)
-   💾 [Storage](storage.md)

🔙 [Back to overview](../README.md)
