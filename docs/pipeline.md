# 🔄 File Processing Pipeline

## Overview

Handles file movement from input to storage.

## Flow

``` mermaid
flowchart LR
    Scanner --> Filter
    Filter --> Queue
    Queue --> DiskSelector
    DiskSelector --> Mover
    Mover --> Validator
```

## Steps

-   Scanner: detects files
-   Filter: applies rules
-   Queue: prioritizes
-   DiskSelector: chooses disk
-   Mover: moves file
-   Validator: checks integrity

## 🔗 Related

-   🧠 [Core](core.md)
-   💾 [Storage](storage.md)

🔙 [Back to overview](../README.md)
