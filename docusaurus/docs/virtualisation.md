---
id: virtualisation
title: Virtualisation Guide (Windows)
---

# Virtualisation Guide — Running MultiDisk FileBalancer on Windows

This guide walks you through running MultiDisk FileBalancer on Windows using a Debian Linux VM in VirtualBox. The program is Linux-only and does not run directly on Windows or via WSL.

## Requirements

- A Windows PC
- VirtualBox (downloaded in this guide)
- The Debian ISO (downloaded in this guide)
- The MultiDisk FileBalancer program folder

---

## Step 1 — Go to debian.org

![Step 1](/img/virtualisatie/image1.png)

## Step 2 — Scroll down and click on Download

![Step 2](/img/virtualisatie/image2.png)

## Step 3 — Wait until the download is ready

![Step 3](/img/virtualisatie/image3.png)

## Step 4 — Go to virtualbox.org

![Step 4](/img/virtualisatie/image4.png)

## Step 5 — Click on Download

![Step 5](/img/virtualisatie/image5.png)

## Step 6 — Click on Windows hosts

![Step 6](/img/virtualisatie/image6.png)

## Step 7 — Wait until the download is ready

![Step 7](/img/virtualisatie/image7.png)

## Step 8 — Click on the VirtualBox installer (.exe)

![Step 8](/img/virtualisatie/image8.png)

## Step 9 — Click Next

![Step 9](/img/virtualisatie/image9.png)

## Step 10 — Click Next

![Step 10](/img/virtualisatie/image10.png)

## Step 11 — Click Next

![Step 11](/img/virtualisatie/image11.png)

## Step 12 — Click Next

![Step 12](/img/virtualisatie/image12.png)

## Step 13 — Click Next

![Step 13](/img/virtualisatie/image13.png)

## Step 14 — Click Next

![Step 14](/img/virtualisatie/image14.png)

## Step 15 — Click Next

![Step 15](/img/virtualisatie/image15.png)

## Step 16 — Click Install

![Step 16](/img/virtualisatie/image16.png)

## Step 17 — Click New to create a new VM

![Step 17](/img/virtualisatie/image17.png)

## Step 18 — Give the VM a name

![Step 18](/img/virtualisatie/image18.png)

## Step 19 — Click Other to select the ISO

![Step 19](/img/virtualisatie/image19.png)

## Step 20 — Select the Debian ISO and click Open

![Step 20](/img/virtualisatie/image20.png)

## Step 21 — Uncheck "Skip Unattended Installation"

![Step 21](/img/virtualisatie/image21.png)

## Step 22 — Give the VM some hardware (RAM and CPU)

Allocate at least **2 GB RAM** and **2 CPU cores**.

![Step 22](/img/virtualisatie/image22.png)

## Step 23 — Give the VM some storage

Allocate at least **20 GB** of disk space.

![Step 23](/img/virtualisatie/image23.png)

## Step 24 — Click Finish

![Step 24](/img/virtualisatie/image24.png)

## Step 25 — Click Start to boot the VM

![Step 25](/img/virtualisatie/image25.png)

## Step 26 — Select "Graphical install"

![Step 26](/img/virtualisatie/image26.png)

## Step 27 — Click Continue (language selection)

![Step 27](/img/virtualisatie/image27.png)

## Step 28 — Click Continue (location selection)

![Step 28](/img/virtualisatie/image28.png)

## Step 29 — Click Continue (keyboard layout)

![Step 29](/img/virtualisatie/image29.png)

## Step 30 — Click Continue (hostname)

![Step 30](/img/virtualisatie/image30.png)

## Step 31 — Click Continue (domain name)

![Step 31](/img/virtualisatie/image31.png)

## Step 32 — Choose a root password and click Continue

![Step 32](/img/virtualisatie/image32.png)

## Step 33 — Click Continue (confirm root password)

![Step 33](/img/virtualisatie/image33.png)

## Step 34 — Click Continue (full name for user)

![Step 34](/img/virtualisatie/image34.png)

## Step 35 — Choose a user password and click Continue

![Step 35](/img/virtualisatie/image35.png)

## Step 36 — Click Continue (confirm user password)

![Step 36](/img/virtualisatie/image36.png)

## Step 37 — Click Continue (timezone)

![Step 37](/img/virtualisatie/image37.png)

## Step 38 — Click Continue (disk partitioning — use entire disk)

![Step 38](/img/virtualisatie/image38.png)

## Step 39 — Click Continue (select disk to partition)

![Step 39](/img/virtualisatie/image39.png)

## Step 40 — Click Continue (partitioning scheme)

![Step 40](/img/virtualisatie/image40.png)

## Step 41 — Click Yes and Continue (write changes to disk)

![Step 41](/img/virtualisatie/image41.png)

## Step 42 — Click Continue (scan extra installation media)

![Step 42](/img/virtualisatie/image42.png)

## Step 43 — Click Continue (package manager mirror country)

![Step 43](/img/virtualisatie/image43.png)

## Step 44 — Click Continue (select mirror)

![Step 44](/img/virtualisatie/image44.png)

## Step 45 — Click Continue (proxy settings)

![Step 45](/img/virtualisatie/image45.png)

## Step 46 — Click Continue (popularity contest)

![Step 46](/img/virtualisatie/image46.png)

## Step 47 — Check and uncheck items to match the following software selection

Make sure **SSH server** and **Standard system utilities** are checked. Select a desktop environment of your choice (e.g. GNOME).

![Step 47](/img/virtualisatie/image47.png)

## Step 48 — Click Continue (software selection)

![Step 48](/img/virtualisatie/image48.png)

## Step 49 — Select the disk for GRUB and click Continue

![Step 49](/img/virtualisatie/image49.png)

## Step 50 — Click Continue (finish installation)

![Step 50](/img/virtualisatie/image50.png)

## Step 51 — Click Shutdown (power off the VM before configuring settings)

![Step 51](/img/virtualisatie/image51.png)

---

## Configuring VM Settings (before next boot)

### Step 52 — Click Settings

![Step 52](/img/virtualisatie/image52.png)

### Step 53 — Click Network

![Step 53](/img/virtualisatie/image53.png)

### Step 54 — Change the adapter to "Bridged Adapter"

This gives the VM its own IP address on your local network, so you can reach SFTP/WebDAV/NFS from other devices.

![Step 54](/img/virtualisatie/image54.png)

### Step 55 — Click Shared Folders

![Step 55](/img/virtualisatie/image55.png)

### Step 56 — Click the add shared folder button

![Step 56](/img/virtualisatie/image56.png)

### Step 57 — Click the folder path dropdown

![Step 57](/img/virtualisatie/image57.png)

### Step 58 — Click Other

![Step 58](/img/virtualisatie/image58.png)

### Step 59 — Select the MultiDisk FileBalancer program folder on your Windows PC

![Step 59](/img/virtualisatie/image59.png)

### Step 60 — Check "Auto-mount" and "Make Permanent", then click OK

![Step 60](/img/virtualisatie/image60.png)

### Step 61 — Click OK to close VM settings

![Step 61](/img/virtualisatie/image61.png)

---

## Installing Guest Additions

### Step 62 — Click Start to boot the VM

![Step 62](/img/virtualisatie/image62.png)

### Step 63 — Enter your password and press Enter

![Step 63](/img/virtualisatie/image63.png)

### Step 64 — Click Devices → Insert Guest Additions CD image...

![Step 64](/img/virtualisatie/image64.png)

### Step 65 — Click Mount and Open

![Step 65](/img/virtualisatie/image65.png)

### Step 66 — Right-click inside the folder and click "Open Terminal Here"

![Step 66](/img/virtualisatie/image66.png)

### Step 67 — Run `su -`

```bash
su -
```

![Step 67](/img/virtualisatie/image67.png)

### Step 68 — Install build dependencies

```bash
sudo apt update && sudo apt install -y build-essential dkms linux-headers-$(uname -r)
```

![Step 68](/img/virtualisatie/image68.png)

### Step 69 — Navigate to the CD-ROM

```bash
cd /media/cdrom0/
```

![Step 69](/img/virtualisatie/image69.png)

### Step 70 — Run the Guest Additions installer

```bash
sudo sh ./VBoxLinuxAdditions.run
```

![Step 70](/img/virtualisatie/image70.png)

### Step 71 — Reboot the VM

```bash
sudo reboot
```

![Step 71](/img/virtualisatie/image71.png)

---

## Configuring User Permissions

### Step 72 — Log in again

![Step 72](/img/virtualisatie/image72.png)

### Step 73 — Open the file explorer

![Step 73](/img/virtualisatie/image73.png)

### Step 74 — Open the Root Disk

![Step 74](/img/virtualisatie/image74.png)

### Step 75 — Open the media folder

![Step 75](/img/virtualisatie/image75.png)

### Step 76 — Open the program folder (shared folder)

![Step 76](/img/virtualisatie/image76.png)

### Step 77 — Open the terminal

![Step 77](/img/virtualisatie/image77.png)

### Step 78 — Run `su -`

```bash
su -
```

![Step 78](/img/virtualisatie/image78.png)

### Step 79 — Add user to sudo group

```bash
usermod -aG sudo user
```

![Step 79](/img/virtualisatie/image79.png)

### Step 80 — Add user to vboxsf group (shared folders access)

```bash
usermod -aG vboxsf user
```

![Step 80](/img/virtualisatie/image80.png)

### Step 81 — Restart the VM

```bash
reboot
```

![Step 81](/img/virtualisatie/image81.png)

---

## Installing and Running the Program

### Step 82 — Open the file explorer

### Step 83 — Open the Root Disk and open the media folder

![Step 83](/img/virtualisatie/image82.png)

### Step 84 — Open the program folder

![Step 84](/img/virtualisatie/image83.png)

### Step 85 — Right-click and click "Open Terminal Here"

![Step 85](/img/virtualisatie/image84.png)

### Step 86 — Install Python and tmux

```bash
sudo apt install python3 python-is-python3 pip tmux
```

![Step 86](/img/virtualisatie/image85.png)

### Step 87 — Install Python dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

![Step 87](/img/virtualisatie/image86.png)

### Step 88 — Start a tmux session

```bash
tmux
```

![Step 88](/img/virtualisatie/image87.png)

### Step 89 — Run the program

```bash
python multidisk_filebalancer.py
```

![Step 89](/img/virtualisatie/image88.png)

### Step 90 — Done! The program is now running

![Step 90](/img/virtualisatie/image89.png)

---

## tmux Tips

### Step 91 — Detach from tmux (program keeps running in background)

Press `Ctrl+B`, then `D`.

### Step 92 — View active tmux sessions

```bash
tmux ls
```

![Step 92](/img/virtualisatie/image90.png)

### Step 93 — Re-attach to a tmux session

```bash
tmux attach -d -t 0
```

![Step 93](/img/virtualisatie/image91.png)

---

## Useful Commands

### Step 94 — Get the full path of the current directory

```bash
pwd
```

![Step 94](/img/virtualisatie/image92.png)

### Step 95 — Get the IP address of the VM

```bash
ip a
```

> Use this IP address to connect to the SFTP or WebDAV server from other devices on the same network.

---

## Navigation

- [Back to Intro](./intro)

## Related Pages

- [Configuration](./configuration)
- [Access Layer](./access-layer)
- [Use Cases](./use-cases)
