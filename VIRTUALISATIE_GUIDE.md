# MultiDisk FileBalancer (Linux-only) gebruiken vanuit Windows (beginners)

Deze tool draait alleen op Linux en ondersteunt geen WSL. Gebruik vanuit Windows:
- VirtualBox (Linux VM)
- VMware (Linux VM)

Na het starten wil je vanuit Windows kunnen uploaden via:
- WebDAV: `http://localhost:8080/`
- SFTP: `localhost:8081`

Belangrijk:
- Je hoeft geen config-bestanden “voor te bereiden”: bij de eerste run stelt het programma vragen en maakt het zelf `config.yml`.
- Gebruik in de config altijd Linux paden (bv. `/home/...`), geen Windows paden.

## VirtualBox / VMware (Linux VM)

### Stap 1 — Ubuntu VM installeren
Installeer Ubuntu in VirtualBox/VMware.
Zet netwerk op **NAT**.

### Stap 2 — Port forwarding instellen (zodat “localhost” in Windows werkt)
Forward Windows (host) → Linux VM (guest):
- TCP `8080` → `8080` (WebDAV)
- TCP `8081` → `8081` (SFTP)

VirtualBox:
- VM → Settings → Network → Adapter 1 (NAT)
- Advanced → Port Forwarding
- Rule 1: Host Port `8080`, Guest Port `8080`
- Rule 2: Host Port `8081`, Guest Port `8081`

### Stap 3 — Projectmap in de VM zetten
Makkelijkste opties:
- Shared Folder (VirtualBox Guest Additions / VMware Tools)
- Download de project-zip in de VM en unzip in je home folder

### Stap 4 — Dependencies installeren (in de VM)
```bash
cd ~/MultiDisk-FileBalancer
sudo apt update
sudo apt install -y python3 python3-pip
python3 -m pip install -r requirements.txt
```

### Stap 5 — Tool starten (eerste run maakt config.yml)
```bash
cd ~/MultiDisk-FileBalancer
python3 multidisk_filebalancer_nieuw_unstable.py
```
Beantwoord de vragen:
- WebDAV: host `0.0.0.0`, port `8080`
- SFTP: host `0.0.0.0`, port `8081`

### Stap 6 — Uploaden vanuit Windows
Door port forwarding werkt dit gewoon:
- WebDAV: `http://localhost:8080/`
- SFTP: `localhost:8081`

## Als iets niet werkt (kort)
- “Module not found …”: voer opnieuw uit:
  ```bash
  python3 -m pip install -r requirements.txt
  ```
- WebDAV/SFTP niet bereikbaar vanuit Windows: controleer dat in `config.yml` de `host` op `0.0.0.0` staat (niet `127.0.0.1`).
