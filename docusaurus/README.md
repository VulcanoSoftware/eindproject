# MultiDisk FileBalancer — Docusaurus Docs

This folder contains the Docusaurus documentation site for MultiDisk FileBalancer.

## Requirements

- Node.js 18 or higher
- npm

## Getting Started

```bash
npm install
npm run start
```

The site will be available at `http://localhost:3000`.

## Build for Production

```bash
npm run build
npm run serve
```

## Structure

```
docs/
  intro.md               # Overview and system-at-a-glance
  architecture.md        # Layered architecture diagram
  core-services.md       # Scheduler, monitor, recovery, notifications
  processing-pipeline.md # File scanner, filter, disk selection, Space Hunter
  storage-layer.md       # Disk aggregation, VFS, metadata, collision resolver
  access-layer.md        # FUSE, SFTP, WebDAV, NFS, Web Panel
  configuration.md       # Full config.yml reference
  use-cases.md           # Real-life deployment scenarios
  virtualisation.md      # Linux VM setup guide (VirtualBox/Debian)
```

## Notes

- Diagrams use [Mermaid](https://mermaid.js.org/) via `@docusaurus/theme-mermaid`.
- NFS uses the Linux kernel `nfs-kernel-server` — Docker is **not** required.
- The Web Panel runs on Flask (default port `5000`) and is enabled by default.
