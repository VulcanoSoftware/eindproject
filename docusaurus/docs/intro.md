---
id: intro
title: Intro
slug: /
---

# MultiDisk FileBalancer

MultiDisk FileBalancer is een software-defined storage orchestration platform dat bestanden verdeelt over meerdere schijven en tegelijkertijd één unified filesystem-weergave aanbiedt.

> **Vereiste:** Het programma draait uitsluitend op Linux. Windows wordt niet ondersteund — ook WSL niet. Gebruik een Linux VM (bijv. Debian in VirtualBox). Zie de [Virtualisatiegids](./virtualisatie) voor een stap-voor-stap installatie.

## Systeem in één oogopslag

```mermaid
flowchart LR
  subgraph Frontend
    UI[Dashboard + Config UI]
    FM[File Manager]
  end

  subgraph Backend
    API[API + Session Layer]
    CORE[Scheduler + Services]
    PIPE[Processing Pipeline]
  end

  subgraph Storage
    AGG[Disk Aggregation]
    VFS[Virtual Filesystem]
    ACCESS[FUSE/SFTP/WebDAV/NFS]
  end

  UI --> API
  FM --> API
  API --> CORE --> PIPE --> AGG --> VFS --> ACCESS

  classDef frontend fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1px;
  classDef backend fill:#dcfce7,stroke:#15803d,color:#0f172a,stroke-width:1px;
  classDef storage fill:#ffedd5,stroke:#c2410c,color:#0f172a,stroke-width:1px;

  class UI,FM frontend;
  class API,CORE,PIPE backend;
  class AGG,VFS,ACCESS storage;
```

## Wat dit systeem oplost

- Multi-disk balancing zonder RAID-striping risico.
- Failure isolation: één defecte schijf raakt alleen de bestanden op die schijf.
- Unified namespace via virtual filesystem abstractie.
- Multi-protocol toegang voor lokale en remote clients (FUSE, SFTP, WebDAV, NFS).
- Achtergrond veiligheidschecks en operationele controles.
- Automatische schijfruimte-bewaking en cleanup via Space Hunter.
- Discord-notificaties voor operationele events en waarschuwingen.

<details>
<summary>Geavanceerde details</summary>

- Startup preflight controleert OS, Python, rechten, dependencies en FUSE-gereedheid.
- Optionele ondersteunende services zijn: reverse workflows, cleanup-automatisering, monitoring en notificaties.
- Het ontwerp legt de nadruk op modulaire groei en veiliger uitbreiden boven strakke RAID-koppeling.
- NFS wordt aangeboden via een Docker-container (vereist Docker Engine op de host).

</details>

## Componentenoverzicht

- **Frontend:** Dashboard, configuratie-interface, file manager, observability views.
- **Backend:** API, authenticatie/sessie-flow, scheduler, disk monitor, recovery, pipeline-logica.
- **Storage:** Aggregatielaag, fysieke schijven, metadata-mapping, VFS, toegangsprotocollen.

## Gerelateerde pagina's

- [Architecture](./architecture)
- [Core Services](./core-services)
- [Processing Pipeline](./processing-pipeline)
- [Storage Layer](./storage-layer)
- [Access Layer](./access-layer)
- [Configuration](./configuration)
- [Use Cases](./use-cases)
- [Virtualisatiegids](./virtualisatie)
