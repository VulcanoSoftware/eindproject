# 🌐 Access Layer

🔙 [Back](../README.md)

## Role

Exposes system externally.

## Flow

``` mermaid
flowchart LR
VFS --> FUSE
VFS --> SFTP
VFS --> WebDAV
VFS --> S3

classDef backend fill:#51cf66,stroke:#2f9e44,color:#000;
class FUSE,SFTP,WebDAV,S3 backend;

classDef storage fill:#ffa94d,stroke:#e67700,color:#000;
class VFS storage;
```

## Details

-   Local mount
-   Remote protocols

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
Auth, performance tuning.

```{=html}
</details>
```
