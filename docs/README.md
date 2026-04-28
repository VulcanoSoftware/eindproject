# MultiDisk FileBalancer

> 📘 This project uses a modular documentation system.\
> Start with the overview and drill down into each component.

## 📊 High-Level Architecture

``` mermaid
flowchart LR
    User --> API
    API --> Core
    Core --> Pipeline
    Pipeline --> Storage
    Storage --> Disks
```

## 🔍 Explore the system

-   🧠 [Core Services](docs/core.md)
-   🔄 [File Processing Pipeline](docs/pipeline.md)
-   💾 [Storage Layer & VFS](docs/storage.md)
-   🌐 [Access Layer](docs/access.md)
-   📊 [Full Architecture Overview](docs/architecture.md)
