---
id: architecture
title: Architecture
---

# Architecture

De architectuur is bewust opgesplitst in Frontend, Backend en Storage om verantwoordelijkheden duidelijk en schaalbaar te houden.

## Gelaagde architectuur

```mermaid
flowchart TB
  subgraph Frontend
    UI[Dashboard + Config + Stats]
    UX[Operator Actions]
  end

  subgraph Backend
    API[API + Auth + Sessions]
    CORE[Core Services]
    PROC[File Processing]
  end

  subgraph Storage
    AGG[Disk Aggregation]
    VFS[Virtual Filesystem]
    PROTO[Access Protocols]
  end

  UX --> UI --> API --> CORE --> PROC --> AGG --> VFS --> PROTO

  classDef frontend fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1px;
  classDef backend fill:#dcfce7,stroke:#15803d,color:#0f172a,stroke-width:1px;
  classDef storage fill:#ffedd5,stroke:#c2410c,color:#0f172a,stroke-width:1px;

  class UI,UX frontend;
  class API,CORE,PROC backend;
  class AGG,VFS,PROTO storage;
```

## Component grenzen

- **Frontend** behandelt gebruikersinteractie en operationele zichtbaarheid.
- **Backend** behandelt orchestratie, beleidsbeslissingen, integriteit en herstel.
- **Storage** behandelt plaatsing, namespace-unificatie, metadata en protocol-serving.

<details>
<summary>Geavanceerde details</summary>

- Monitoring- en notificatiepaden (inclusief Discord webhooks) zijn gekoppeld aan backend- en pipeline-events.
- Backup/redundantie-workflows integreren met schijfselectie en herstellussen.
- Het ontwerp ondersteunt optionele services zonder de kernbalanceringsloop te wijzigen.
- NFS-service vereist Docker Engine op de host voor containerisatie van de NFS-daemon.

</details>

## Navigatie

- [Terug naar Intro](./intro)

## Gerelateerde pagina's

- [Core Services](./core-services)
- [Processing Pipeline](./processing-pipeline)
- [Storage Layer](./storage-layer)
