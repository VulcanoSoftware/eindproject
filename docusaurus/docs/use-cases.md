---
id: use-cases
title: Use Cases
---

# Use Cases

These scenarios show practical deployments of MultiDisk FileBalancer in production-like environments.

## Scenario Map

```mermaid
flowchart LR
  subgraph Frontend
    TEAM[Ops Team]
    APPS[Client Apps]
  end

  subgraph Backend
    ORCH[Scheduler + Pipeline]
    SAFETY[Monitoring + Recovery]
  end

  subgraph Storage
    POOL[Disk Pool + VFS]
    ACCESS[FUSE/SFTP/WebDAV/S3]
  end

  TEAM --> ORCH --> POOL --> ACCESS --> APPS
  SAFETY --> ORCH

  classDef frontend fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1px;
  classDef backend fill:#dcfce7,stroke:#15803d,color:#0f172a,stroke-width:1px;
  classDef storage fill:#ffedd5,stroke:#c2410c,color:#0f172a,stroke-width:1px;

  class TEAM,APPS frontend;
  class ORCH,SAFETY backend;
  class POOL,ACCESS storage;
```

## Real-Life Examples

- Automated backup server: ingest backup outputs, age-gate transfers, and protect free space with cleanup rules.
- Media archive platform: unify multiple disks under one namespace and serve remote reads over SFTP/WebDAV.
- Home or SMB NAS: expand storage incrementally without RAID striping constraints.
- Data ingestion pipeline: collect files rapidly, prioritize queue execution, and validate post-move integrity.
- Migration and reprocessing: use reverse workflows to bring files back to central processing stages.

## Practical Scenarios

- Disk failure handling: continue operations on healthy disks with isolated impact.
- Bursty workloads: tune queueing and scan intervals for predictable throughput.
- Mixed protocol clients: expose one VFS to local mounts and object-compatible tooling.

<details>
<summary>Advanced details</summary>

- Add webhook-based notifications for operational observability.
- Pair health metrics with proactive cleanup thresholds.
- Use staged rollout of optional protocols to simplify troubleshooting.

</details>

## Navigation

- [Back to Intro](./intro)

## Related Pages

- [Architecture](./architecture)
- [Storage Layer](./storage-layer)
- [Access Layer](./access-layer)
- [Configuration](./configuration)
