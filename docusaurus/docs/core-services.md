---
id: core-services
title: Core Services
---

# Core Services

Core services coordinate scheduling, health, and system safety before and during file operations.

## Service Coordination

```mermaid
flowchart LR
  subgraph Frontend
    OPS[Operator Triggers]
  end

  subgraph Backend
    CFG[Config Loader]
    SCH[Scheduler]
    MON[Disk Monitor]
    REC[Recovery Engine]
    NOTIF[Notifications / Discord]
  end

  subgraph Storage
    STATE[Disk State + Capacity]
  end

  OPS --> CFG --> SCH --> MON --> REC --> NOTIF
  MON --> STATE
  REC --> STATE

  classDef frontend fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1px;
  classDef backend fill:#dcfce7,stroke:#15803d,color:#0f172a,stroke-width:1px;
  classDef storage fill:#ffedd5,stroke:#c2410c,color:#0f172a,stroke-width:1px;

  class OPS frontend;
  class CFG,SCH,MON,REC,NOTIF backend;
  class STATE storage;
```

## Components

- **Config Loader:** validates startup configuration and service toggles. Launches an interactive setup wizard when no `config.yml` is present.
- **Scheduler:** orchestrates recurring scan and maintenance cycles based on `scan_interval_seconds`.
- **Disk Monitor:** tracks free space, availability, and health indicators.
- **Recovery Engine:** supports degraded operation and reintegration after disk recovery.
- **Notifications:** emits operational events and warnings via Discord webhook or console output.

## Startup Preflight

On every start the program runs a preflight check that reports:

- OS and Python version
- Admin/root privileges
- FUSE availability and mount point
- Enabled services (FUSE, WebDAV, SFTP, NFS)
- Installation advice for missing dependencies

This output appears both in the console and via the Discord webhook (if configured).

## Discord Notifications

Set `webhook_url` in `config.yml` to a Discord webhook URL to receive alerts about:

- File moves and deletions
- Disk space warnings
- Server startup statuses
- Errors and recovery events

Leave `webhook_url` empty or omit it to disable notifications.

<details>
<summary>Advanced details</summary>

- Startup preflight can gate service enablement based on dependency readiness.
- Recovery integrates with validation outcomes and disk health telemetry.
- Notifications post to a single Discord webhook; a Discord bot can be used as a relay for multiple channels.
- The NFS service uses the Linux kernel NFS server (`nfs-kernel-server`), installed automatically if missing. It requires root or sudo to write export entries and reload `exportfs`.

</details>

## Navigation

- [Back to Intro](./intro)

## Related Pages

- [Architecture](./architecture)
- [Processing Pipeline](./processing-pipeline)
- [Storage Layer](./storage-layer)
