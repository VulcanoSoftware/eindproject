---
id: virtualisatie
title: Virtualisatiegids (Windows)
---

# Virtualisatiegids — MultiDisk FileBalancer op Windows

Deze gids legt stap voor stap uit hoe je MultiDisk FileBalancer draait op Windows via een Debian Linux VM in VirtualBox. Het programma is Linux-only en werkt niet rechtstreeks op Windows of via WSL.

## Benodigdheden

- Windows-pc met VirtualBox geïnstalleerd
- Debian ISO
- De MultiDisk FileBalancer programmamap (gedeeld als VirtualBox Shared Folder)

---

## Stap 1 — Debian downloaden

1. Ga naar [debian.org](https://www.debian.org)
2. Scroll naar beneden en klik op **Download**
3. Wacht tot de download klaar is

---

## Stap 2 — VirtualBox downloaden en installeren

1. Ga naar [virtualbox.org](https://www.virtualbox.org)
2. Klik op **Download**
3. Klik op **Windows hosts**
4. Wacht tot de download klaar is
5. Klik op het gedownloade `.exe`-bestand om de installatie te starten
6. Klik door de installatie-wizard (Next → Next → Install → Finish)

---

## Stap 3 — Nieuwe VM aanmaken

1. Open VirtualBox en klik op **New**
2. Geef de VM een naam (bijv. `Debian-FileBalancer`)
3. Klik bij ISO op **Other** en selecteer de gedownloade Debian ISO — klik **Open**
4. **Vink "Skip Unattended Installation" uit** (zodat je zelf de installatie doorloopt)
5. Ken hardware toe:
   - Minimaal **2 GB RAM** (2048 MB)
   - Minimaal **2 CPU-cores**
6. Ken schijfruimte toe:
   - Minimaal **20 GB** voor de VM-schijf
7. Klik op **Finish**

---

## Stap 4 — Debian installeren

1. Selecteer de VM en klik op **Start**
2. Selecteer **Graphical install** en druk Enter
3. Doorloop de installatie-wizard:
   - **Taal, locatie, toetsenbord:** kies naar voorkeur en klik Continue
   - **Hostnaam:** standaard laten of aanpassen
   - **Root-wachtwoord:** kies een wachtwoord en klik Continue
   - **Gebruikersnaam:** kies een gebruikersnaam (bijv. `user`)
   - **Gebruikerswachtwoord:** kies een wachtwoord en klik Continue
   - **Schijfindeling:** kies **Guided - use entire disk**, bevestig en klik Continue
   - **Schrijf wijzigingen naar schijf:** klik **Yes** en Continue
   - **Pakketbeheerder (mirror):** kies een land en mirror, klik Continue
   - **Deelnemen aan popularity-contest:** keuze is vrij, klik Continue
   - **Softwareselectie:** zorg dat de selectie er als volgt uitziet:
     - ✅ Debian desktop environment
     - ✅ GNOME (of een andere desktop naar voorkeur)
     - ✅ SSH server
     - ✅ Standard system utilities
     - ❌ Alles andere naar wens uitzetten
   - Klik Continue
4. **GRUB bootloader:** klik op de schijf (bijv. `/dev/sda`) en klik Continue
5. Wacht tot de installatie klaar is
6. Klik op **Continue** om te herstarten

---

## Stap 5 — VM-instellingen configureren (vóór eerste boot)

Schakel de VM uit na de installatie (**Shutdown**), open dan de VM-instellingen:

### Netwerk instellen (Bridged Adapter)

1. Klik op **Settings** → **Network**
2. Verander **Attached to** naar **Bridged Adapter**
3. Klik **OK**

> Dit geeft de VM een eigen IP-adres op je lokale netwerk, zodat je SFTP/WebDAV/NFS van buitenaf kunt bereiken.

### Gedeelde map instellen

1. Klik op **Settings** → **Shared Folders**
2. Klik op het map-icoon met het plusje
3. Klik op **Other** en selecteer de map van het MultiDisk FileBalancer programma op je Windows-pc
4. Vink **Auto-mount** en **Make Permanent** aan
5. Klik **OK** → **OK**

---

## Stap 6 — VirtualBox Guest Additions installeren

Start de VM en log in. Voer vervolgens de volgende stappen uit:

1. Klik in het VirtualBox-venster op **Devices** → **Insert Guest Additions CD image...**
2. De CD verschijnt op het bureaublad — dubbelklik om te mounten, klik **Mount and Open**
3. Rechtsclick in de bestandsverkenner → **Open Terminal Here**
4. Voer de volgende commando's uit:

```bash
su -
```

```bash
sudo apt update && sudo apt install -y build-essential dkms linux-headers-$(uname -r)
```

```bash
cd /media/cdrom0/
```

```bash
sudo sh ./VBoxLinuxAdditions.run
```

```bash
sudo reboot
```

---

## Stap 7 — Gebruikersrechten instellen

Log in na de herstart en open een terminal:

```bash
su -
```

```bash
usermod -aG sudo user
```

```bash
usermod -aG vboxsf user
```

```bash
# Herstart de VM zodat de groepswijzigingen van kracht worden
reboot
```

> Vervang `user` door je eigen gebruikersnaam als je een andere naam gekozen hebt.

---

## Stap 8 — Gedeelde map openen en programma installeren

Na herstart:

1. Open de bestandsverkenner
2. Navigeer naar **Root Disk** → **media** → de gedeelde map (bijv. `sf_MultiDisk-FileBalancer`)
3. Rechtsclick → **Open Terminal Here**
4. Installeer de vereiste software:

```bash
sudo apt install python3 python-is-python3 pip tmux
```

```bash
pip install -r requirements.txt --break-system-packages
```

---

## Stap 9 — Programma starten met tmux

Gebruik `tmux` zodat het programma blijft draaien, ook als je het terminalvenster sluit:

```bash
tmux
```

```bash
python multidisk_filebalancer.py
```

Het programma start de interactieve wizard als er nog geen `config.yml` aanwezig is.

---

## tmux cheatsheet

| Actie | Commando |
|---|---|
| Sessie loskoppelen (programma blijft draaien) | `Ctrl+B`, dan `D` |
| Actieve tmux-sessies bekijken | `tmux ls` |
| Opnieuw koppelen aan sessie | `tmux attach -d -t 0` |

---

## Handige commando's

```bash
# Huidig pad opvragen
pwd

# IP-adres van de VM opvragen (voor SFTP/WebDAV/NFS verbindingen)
ip a
```

> Gebruik het IP-adres uit `ip a` om verbinding te maken met de SFTP- of WebDAV-server vanaf andere apparaten op hetzelfde netwerk.

---

## Navigatie

- [Terug naar Intro](./intro)

## Gerelateerde pagina's

- [Configuration](./configuration)
- [Access Layer](./access-layer)
- [Use Cases](./use-cases)
