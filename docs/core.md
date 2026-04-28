# 🧠 Core Services

🔙 [Back](../README.md)

## Role

Handles orchestration, scheduling and system health.

## Flow

``` mermaid
flowchart LR
Config --> Scheduler --> Monitor --> Recovery

classDef backend fill:#51cf66,stroke:#2f9e44,color:#000;
class Config,Scheduler,Monitor,Recovery backend;
```

## Details

### Scheduler

-   Job execution
-   Interval control

### Disk Monitor

-   Health tracking
-   Failure detection

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
Recovery strategies, retry logic, state persistence.

```{=html}
</details>
```
