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
    NOTIF[Notifications]
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

- Config Loader: validates startup configuration and service toggles.
- Scheduler: orchestrates recurring scan and maintenance cycles.
- Disk Monitor: tracks free space, availability, and health indicators.
- Recovery Engine: supports degraded operation and reintegration.
- Notifications: emits operational events and warning signals.

<details>
<summary>Advanced details</summary>

- Startup preflight can gate service enablement based on dependency readiness.
- Recovery integrates with validation outcomes and disk health telemetry.
- Notifications can map to webhooks for remote alerting and observability.

</details>

## Navigation

- [Back to Intro](./intro)

## Related Pages

- [Architecture](./architecture)
- [Processing Pipeline](./processing-pipeline)
- [Storage Layer](./storage-layer)
