---
id: storage-layer
title: Storage Layer
---

# Storage Layer

De storage layer aggregeert meerdere fysieke schijven en stelt één unified virtuele namespace beschikbaar.

## Aggregatie en VFS

```mermaid
flowchart TB
  subgraph Frontend
    VIEW[Unified Folder View]
  end

  subgraph Backend
    MAP[Path Mapping]
    META[Metadata Cache]
    RESOLVE[Collision Resolver]
  end

  subgraph Storage
    AGG[Disk Aggregation]
    PHYS[Physical Disks]
    VFS[Virtual Filesystem]
  end

  AGG --> PHYS
  AGG --> VFS
  VFS --> MAP --> RESOLVE --> META --> VIEW

  classDef frontend fill:#dbeafe,stroke:#1d4ed8,color:#0f172a,stroke-width:1px;
  classDef backend fill:#dcfce7,stroke:#15803d,color:#0f172a,stroke-width:1px;
  classDef storage fill:#ffedd5,stroke:#c2410c,color:#0f172a,stroke-width:1px;

  class VIEW frontend;
  class MAP,META,RESOLVE backend;
  class AGG,PHYS,VFS storage;
```

## Componenten

- **Disk Aggregation:** normaliseert schijfpoolgedrag over onafhankelijke apparaten.
- **Physical Disks:** bevatten volledige bestanden — geen striping over schijven.
- **Virtual Filesystem (VFS):** biedt één logische directorynamespace voor alle protocols.
- **Path Mapping:** mapt virtuele paden naar fysieke locaties.
- **Metadata Handling:** cachet toegangsmetadata voor snellere resolutie (TTL: 2 seconden).
- **Collision Resolver:** voorkomt bestandsnaamconflicten deterministisch via hash-gebaseerde hernoeming.

<details>
<summary>Geavanceerde details</summary>

- Path traversal-protecties verdedigen tegen onveilige padconstructie.
- Gedegradeerde modus blijft gezonde schijven bedienen tijdens gedeeltelijke uitval.
- Herintegration kan volledige poolzichtbaarheid herstellen na schijfherstel.
- De VFS-cache wordt automatisch ongeldig gemaakt na bestandsoperaties.

</details>

## Navigatie

- [Terug naar Intro](./intro)

## Gerelateerde pagina's

- [Architecture](./architecture)
- [Access Layer](./access-layer)
- [Configuration](./configuration)
