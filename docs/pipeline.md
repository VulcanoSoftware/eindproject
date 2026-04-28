# 🔄 Processing Pipeline

🔙 [Back](../README.md)

## Role

Handles file lifecycle.

## Flow

``` mermaid
flowchart LR
Scan --> Filter --> Queue --> Select --> Move --> Validate

classDef backend fill:#51cf66,stroke:#2f9e44,color:#000;
class Scan,Filter,Queue,Select,Move,Validate backend;
```

## Details

-   Scan: detect files
-   Filter: rules
-   Queue: priority
-   Select: disk choice
-   Move: transfer
-   Validate: integrity

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
Queue strategies, retry logic, hashing.

```{=html}
</details>
```
