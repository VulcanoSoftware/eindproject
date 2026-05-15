---
id: processing-pipeline
title: Processing Pipeline
---

# Processing Pipeline

The processing pipeline moves eligible files safely from input folders to selected storage targets.

## Pipeline Flow

```mermaid
flowchart LR
  subgraph Frontend
    RULES[Policy Inputs]
  end

  subgraph Backend
    SCAN[File Scanner]
    FILT[Filter Engine]
    QUEUE[Priority Queue]
    PICK[Disk Selection]
    MOVE[File Mover]
    VALID[Integrity Validator]
  end

  subgraph Storage
    TARGET[Selected Disk Path]
  end

  RULES --> SCAN --> FILT --> QUEUE --> PICK --> MOVE --> VALID --> TARGET

  classDef frontend fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1px;
  classDef backend fill:#dcfce7,stroke:#15803d,color:#0f172a,stroke-width:1px;
  classDef storage fill:#ffedd5,stroke:#c2410c,color:#0f172a,stroke-width:1px;

  class RULES frontend;
  class SCAN,FILT,QUEUE,PICK,MOVE,VALID backend;
  class TARGET storage;
```

## Components

- File Scanner: recursively discovers candidate files.
- Filter Engine: applies age, exclusions, lock checks, and stability checks.
- Priority Queue: orders candidate work for predictable throughput.
- Disk Selection Logic: round-robin plus safety-space and eligibility controls.
- File Mover: performs transfer with collision-safe naming behavior.
- Validation: confirms move integrity and consistency before completion.

<details>
<summary>Advanced details</summary>

- Cleanup automation can run in parallel to enforce minimum free space goals.
- Optional reverse workflows can move data back for reprocessing or migration.
- Action limits and dry-run modes reduce operational risk during maintenance.

</details>

## Navigation

- [Back to Intro](./intro)

## Related Pages

- [Core Services](./core-services)
- [Storage Layer](./storage-layer)
- [Configuration](./configuration)
