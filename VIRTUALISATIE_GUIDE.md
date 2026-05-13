# MultiDisk FileBalancer (Linux-only) gebruiken vanuit Windows via virtualisatie

Deze tool draait alleen op Linux. Vanuit Windows zijn er 2 praktische opties:
- WSL2 (Ubuntu)
- VirtualBox/VMware (Linux VM)

Doel: vanuit Windows uploaden naar de Linux-tool via:
- WebDAV: http://localhost:8080/
- SFTP: localhost:8081

## 1) WSL2 (Ubuntu)

### 1.1 WSL2 installeren
Open PowerShell als Administrator:
```powershell
wsl --install -d Ubuntu
```
Herstart als Windows dat vraagt. Start daarna de Ubuntu app.

### 1.2 Project naar WSL kopiëren
In Ubuntu:
```bash
cd ~
mkdir -p MultiDisk-FileBalancer
```
Kopieer in Windows Verkenner je projectmap naar:
`\\wsl$\Ubuntu\home\<jouw-linux-user>\MultiDisk-FileBalancer\`

### 1.3 Dependencies installeren (in Ubuntu)
```bash
cd ~/MultiDisk-FileBalancer
sudo apt update
sudo apt install -y python3 python3-pip libfuse2 fuse
python3 -m pip install -r requirements.txt
```

### 1.4 config.yml instellen
Gebruik alleen Linux paden.
Zorg dat deze server-instellingen kloppen:
- `webdav_server.enabled: true`
- `webdav_server.host: 0.0.0.0`
- `webdav_server.port: 8080`
- `sftp_server.enabled: true`
- `sftp_server.host: 0.0.0.0`
- `sftp_server.port: 8081`

Als je FUSE wilt gebruiken:
- `fuse_server.enabled: true`
- `fuse_server.mount_point: /mnt/multidisk` (voorbeeld)

### 1.5 Tool starten
```bash
cd ~/MultiDisk-FileBalancer
python3 multidisk_filebalancer_nieuw_unstable.py
```

### 1.6 Uploaden vanuit Windows
#### WebDAV (localhost:8080)
1. Verkenner → “Deze pc”
2. “Netwerklocatie toevoegen”
3. Adres: `http://localhost:8080/`
4. Login met `username/password` uit `config.yml`

#### SFTP (localhost:8081)
Gebruik WinSCP (of FileZilla):
- Protocol: SFTP
- Host: `localhost`
- Port: `8081`
- User/Password: uit `config.yml`

## 2) VirtualBox / VMware (Linux VM)

### 2.1 VM installeren
Installeer Ubuntu (of andere Linux distro) in VirtualBox/VMware.

Netwerk: zet de VM op **NAT**.

### 2.2 Port forwarding instellen (NAT)
Forward Windows (host) → Linux VM (guest):
- TCP 8080 → 8080 (WebDAV)
- TCP 8081 → 8081 (SFTP)

VirtualBox: VM → Settings → Network → Adapter 1 (NAT) → Advanced → Port Forwarding
- Rule 1: Host Port `8080` → Guest Port `8080`
- Rule 2: Host Port `8081` → Guest Port `8081`

VMware: gebruik NAT Port Forwarding in Virtual Network Editor (of zet bridged en gebruik het VM IP i.p.v. localhost).

### 2.3 Project naar de VM kopiëren
Opties:
- Shared Folder (VirtualBox Guest Additions / VMware Tools)
- SCP naar de VM

### 2.4 Dependencies installeren (in de VM)
```bash
cd ~/MultiDisk-FileBalancer
sudo apt update
sudo apt install -y python3 python3-pip libfuse2 fuse
python3 -m pip install -r requirements.txt
```

### 2.5 config.yml instellen
Zelfde als bij WSL2:
- `host: 0.0.0.0`
- WebDAV `port: 8080`
- SFTP `port: 8081`

### 2.6 Tool starten
```bash
python3 multidisk_filebalancer_nieuw_unstable.py
```

### 2.7 Uploaden vanuit Windows
Door port forwarding:
- WebDAV: `http://localhost:8080/`
- SFTP: `localhost:8081`

