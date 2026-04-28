# 💾 Storage Layer

🔙 [Back](../README.md)

## Role

Manages disks and virtual filesystem.

## Flow

``` mermaid
flowchart TB
Agg --> VFS
Agg --> D1
Agg --> D2
Agg --> DN

classDef storage fill:#ffa94d,stroke:#e67700,color:#000;
class Agg,VFS,D1,D2,DN storage;
```

## Details

-   Aggregation
-   Metadata
-   Disk balancing

```{=html}
<details>
```
```{=html}
<summary>
```
⚙️ Advanced
```{=html}
</summary>
```
Redundancy, caching, failure recovery.

```{=html}
</details>
```
