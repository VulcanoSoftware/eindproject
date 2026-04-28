# 📊 Full Architecture Overview

## Layered View

``` mermaid
flowchart TB
    UI --> API
    API --> Core
    Core --> Pipeline
    Pipeline --> Storage
    Storage --> VFS
    VFS --> Access
```

## Description

This diagram shows the high-level interaction between all major layers.

🔙 [Back to overview](../README.md)
