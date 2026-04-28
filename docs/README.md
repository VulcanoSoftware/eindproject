# MultiDisk FileBalancer

> 📘 This documentation is structured in layers. Start with the overview
> and drill down.

## 🎨 Legend

-   🔵 Frontend
-   🟢 Backend
-   🟠 Storage

## 📊 High-Level Architecture

``` mermaid
flowchart LR

UI[User Interface]
API[API Layer]
Core[Core Services]
Pipeline[Processing Pipeline]
VFS[Virtual Filesystem]
Disks[(Physical Disks)]

UI --> API
API --> Core
Core --> Pipeline
Pipeline --> VFS
VFS --> Disks

classDef frontend fill:#4da6ff,stroke:#1c6ed5,color:#fff;
classDef backend fill:#51cf66,stroke:#2f9e44,color:#000;
classDef storage fill:#ffa94d,stroke:#e67700,color:#000;

class UI frontend;
class API,Core,Pipeline backend;
class VFS,Disks storage;
```

## 🔍 Explore

-   🧠 [Core Services](docs/core.md)
-   🔄 [Pipeline](docs/pipeline.md)
-   💾 [Storage](docs/storage.md)
-   🌐 [Access](docs/access.md)
-   ⚙️ [Configuration](docs/config.md)
