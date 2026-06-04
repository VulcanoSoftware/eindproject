import os
from datetime import datetime, timedelta
import shutil
import yaml
import time
import requests
import threading
import asyncio
import asyncssh
import stat
import errno
import sys
import hashlib
import signal
import atexit
import subprocess
import logging
import platform
from asyncssh.sftp import SFTPName, SFTPAttrs, FXF_READ, FXF_WRITE, FXF_APPEND, FXF_CREAT, FXF_TRUNC
from flask import Flask, jsonify, request, send_from_directory

logger = logging.getLogger("multidisk_filebalancer.vfs")

def _is_wsl():
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        return True
    for path in ("/proc/sys/kernel/osrelease", "/proc/version"):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                if "microsoft" in (f.read() or "").lower():
                    return True
        except OSError:
            continue
    return False

def _ensure_linux():
    if not sys.platform.lower().startswith("linux"):
        raise SystemExit("This tool is Linux-only. Run it on a Linux VM (VirtualBox/VMware).")
    if _is_wsl():
        raise SystemExit("WSL is not supported. Run this tool in a Linux VM (VirtualBox/VMware).")

def try_import_fuse():
    global FUSE, Operations, FuseOSError
    try:
        from fuse import FUSE, Operations, FuseOSError
        return True
    except (ImportError, OSError):
        FUSE = None
        Operations = object
        class FuseOSError(Exception):
            pass
        return False

FUSE = None
Operations = object
class FuseOSError(Exception):
    pass

try_import_fuse()

def has_admin_privileges():
    try:
        geteuid = getattr(os, "geteuid", None)
        if geteuid is None:
            return False
        return geteuid() == 0
    except Exception:
        return False


def is_privilege_error_text(text):
    message = str(text).lower()
    privilege_markers = [
        "permission denied",
        "access is denied",
        "administrator",
        "admin privileges",
        "requires elevation",
        "operation not permitted",
        "must be run as root",
        "not in the sudoers",
        "authentication is required",
        "insufficient privileges",
    ]
    for marker in privilege_markers:
        if marker in message:
            return True
    return False


def admin_restart_instruction():
    return "Restart this program with sudo/root privileges and try again."


def detect_fuse_install_strategy():
    _ensure_linux()
    if shutil.which("apt-get"):
        return "sudo apt-get update && (sudo apt-get install -y fuse3 libfuse3-3 || sudo apt-get install -y fuse libfuse2)"
    if shutil.which("dnf"):
        return "sudo dnf install -y fuse3 fuse3-libs fuse-libs"
    if shutil.which("pacman"):
        return "sudo pacman -S --noconfirm fuse3 || sudo pacman -S --noconfirm fuse2"
    return "Install libfuse via your distro package manager (e.g. apt/dnf/pacman)."

def _is_mount_active(path):
    if not path:
        return False
    try:
        if not os.path.exists(path):
            return False
        return bool(os.path.ismount(path))
    except Exception:
        return False


def _ensure_fuse_user_allow_other(webhook_url):
    _ensure_linux()
    fuse_conf = "/etc/fuse.conf"
    try:
        if not os.path.exists(fuse_conf):
            return True
    except Exception:
        return True

    try:
        with open(fuse_conf, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
    except Exception as exc:
        if has_admin_privileges():
            print_and_discord(f"FUSE warning: could not read {fuse_conf}: {exc}", webhook_url)
        return False

    already_enabled = False
    for line in lines:
        if line.strip() == "user_allow_other":
            already_enabled = True
            break
    if already_enabled:
        return True

    updated = []
    changed = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") and stripped.lstrip("#").strip() == "user_allow_other":
            updated.append("user_allow_other")
            changed = True
        else:
            updated.append(line)
    if not changed:
        if updated and updated[-1].strip() != "":
            updated.append("")
        updated.append("user_allow_other")
        changed = True

    if not changed:
        return True

    if not has_admin_privileges():
        print_and_discord("FUSE hint: enable 'user_allow_other' in /etc/fuse.conf (run as root).", webhook_url)
        return False

    try:
        with open(fuse_conf, "w", encoding="utf-8") as f:
            f.write("\n".join(updated).rstrip("\n") + "\n")
        return True
    except Exception as exc:
        print_and_discord(f"FUSE warning: could not update {fuse_conf}: {exc}", webhook_url)
        return False



def print_startup_preflight(
    webhook_url,
    fuse_enabled,
    webdav_enabled,
    sftp_enabled,
    nfs_enabled,
    fuse_mount_point,
):
    import platform
    os_name = platform.system()
    os_release = platform.release()
    py_version = platform.python_version()
    if has_admin_privileges():
        admin_mode = "yes"
    else:
        admin_mode = "no"

    if FUSE is not None:
        fuse_loaded = "yes"
    else:
        fuse_loaded = "no"

    if fuse_enabled:
        fuse_required = "yes"
    else:
        fuse_required = "no"

    if webdav_enabled:
        webdav_mode = "yes"
    else:
        webdav_mode = "no"

    if sftp_enabled:
        sftp_mode = "yes"
    else:
        sftp_mode = "no"

    if nfs_enabled:
        nfs_mode = "yes"
    else:
        nfs_mode = "no"

    install_strategy = detect_fuse_install_strategy()
    print_and_discord("========== Startup preflight ==========", webhook_url)
    print_and_discord(f"OS: {os_name} {os_release}", webhook_url)
    print_and_discord(f"Python: {py_version}", webhook_url)
    print_and_discord(f"Admin/root privileges: {admin_mode}", webhook_url)
    print_and_discord(
        f"Features enabled -> FUSE: {fuse_required}, WebDAV: {webdav_mode}, SFTP: {sftp_mode}, NFS: {nfs_mode}",
        webhook_url
    )
    print_and_discord(f"FUSE python binding loaded: {fuse_loaded}", webhook_url)
    if fuse_enabled:
        print_and_discord(f"FUSE mount point: {fuse_mount_point}", webhook_url)
        print_and_discord(f"FUSE installer strategy: {install_strategy}", webhook_url)
    print_and_discord("=======================================", webhook_url)


def install_libfuse():
    _ensure_linux()
    system = "linux"
    print(f"Attempting to install libfuse for {system}...")
    last_error = ""

    def run_cmd(cmd, shell=False):
        nonlocal last_error
        result = subprocess.run(cmd, check=True, shell=shell, capture_output=True, text=True)
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        last_error = stderr or stdout

    def install_python_fuse_package():
        nonlocal last_error
        pip_cmd = [sys.executable, "-m", "pip", "install", "fusepy"]
        result = subprocess.run(pip_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        last_error = (result.stderr or result.stdout or "").strip()
        pip_cmd_break = [sys.executable, "-m", "pip", "install", "fusepy", "--break-system-packages"]
        result_break = subprocess.run(pip_cmd_break, capture_output=True, text=True)
        if result_break.returncode == 0:
            return True
        last_error = (result_break.stderr or result_break.stdout or last_error).strip()
        return False

    try:
        if shutil.which("apt-get"):
            run_cmd(["sudo", "apt-get", "update"])
            try:
                run_cmd(["sudo", "apt-get", "install", "-y", "fuse3", "libfuse3-3"])
            except subprocess.CalledProcessError:
                run_cmd(["sudo", "apt-get", "install", "-y", "fuse", "libfuse2"])
        elif shutil.which("dnf"):
            run_cmd(["sudo", "dnf", "install", "-y", "fuse3", "fuse3-libs", "fuse-libs"])
        elif shutil.which("pacman"):
            try:
                run_cmd(["sudo", "pacman", "-S", "--noconfirm", "fuse3"])
            except subprocess.CalledProcessError:
                run_cmd(["sudo", "pacman", "-S", "--noconfirm", "fuse2"])
        else:
            print("No supported package manager (apt, dnf, pacman) found on Linux.")
            return False, "No supported Linux package manager found for FUSE installation.", False

        if not install_python_fuse_package():
            needs_admin = is_privilege_error_text(last_error) or not has_admin_privileges()
            return False, (last_error or "Could not install Python package 'fusepy'."), needs_admin

        if try_import_fuse():
            return True, "", False
        return False, "FUSE dependencies were installed but Python still cannot load FUSE on this OS.", False
    except subprocess.CalledProcessError as e:
        error_parts = [str(e), getattr(e, "stderr", ""), getattr(e, "stdout", ""), last_error]
        filtered_parts = []
        for part in error_parts:
            if part:
                filtered_parts.append(part)
        combined_error = "\n".join(filtered_parts).strip()
        needs_admin = is_privilege_error_text(combined_error) or not has_admin_privileges()
        print(f"Automatic installation failed: {combined_error}")
        return False, combined_error, needs_admin
    except Exception as e:
        error_text = str(e)
        needs_admin = is_privilege_error_text(error_text) or not has_admin_privileges()
        print(f"Automatic installation failed: {error_text}")
        return False, error_text, needs_admin

current_dir = os.getcwd()
config_path = os.path.join(current_dir, "config.yml")

_webpanel_thread = None
_webpanel_app = None

_stats_lock = threading.Lock()
_stats = {
    "start_ts": time.time(),
    "files_moved_total": 0,
    "bytes_moved_total": 0,
    "cleanup_actions_total": 0,
    "errors_total": 0,
    "last_action": None,
    "moves_series": [],
    "max_series_points": 120,
    "recent_actions": [],
    "max_recent_actions": 80,
    "cycle_start_ts": None,
    "cycle_start_totals": None,
    "cycle": {
        "last_start_ts": None,
        "last_end_ts": None,
        "last_duration_seconds": 0,
        "last_moved_files": 0,
        "last_moved_bytes": 0,
        "last_cleanup_actions": 0,
        "last_errors": 0,
        "next_run_ts": None,
    },
}

_vfs_base_paths = []
_vfs_cache_lock = threading.RLock()
_vfs_dir_cache = {}
_vfs_cache_ttl_seconds = 2.0
_file_operation_lock = threading.RLock()
_vfs_dedupe_duplicate_names = False

# Registry of Docker containers started by this process.
# Each entry is a dict with keys: 'name' and 'docker_exe' (usually "docker").
_managed_docker_containers = []
_managed_docker_lock = threading.Lock()

_managed_nfs_export_paths = []
_managed_nfs_lock = threading.Lock()

_automount_thread = None
_pkg_install_lock = threading.Lock()
_apt_updated_once = False
_pkg_install_attempted = {}


def _register_managed_nfs_export_path(export_path):
    with _managed_nfs_lock:
        if export_path and export_path not in _managed_nfs_export_paths:
            _managed_nfs_export_paths.append(export_path)


def _sudo_prefix():
    if has_admin_privileges():
        return []
    if shutil.which("sudo"):
        return ["sudo"]
    return []


def _run_capture(cmd, timeout=30):
    result = subprocess.run(
        [str(c) for c in cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    combined = "\n".join([p for p in (stdout, stderr) if p]).strip()
    return result.returncode, combined


def _run_stream(cmd, timeout=None):
    start = time.time()
    proc = subprocess.Popen(
        [str(c) for c in cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    lines = []
    try:
        while True:
            if timeout is not None and (time.time() - start) > timeout:
                try:
                    proc.kill()
                except Exception:
                    pass
                return 124, "\n".join(lines[-200:]).strip()

            line = proc.stdout.readline() if proc.stdout is not None else ""
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
                continue
            print(line, end="")
            lines.append(line.rstrip("\n"))
            if len(lines) > 400:
                lines = lines[-200:]
    finally:
        try:
            if proc.stdout is not None:
                proc.stdout.close()
        except Exception:
            pass
    return proc.returncode or 0, "\n".join(lines[-200:]).strip()


def _selinux_enforcing():
    try:
        enforce_path = "/sys/fs/selinux/enforce"
        if os.path.exists(enforce_path):
            with open(enforce_path, "r", encoding="utf-8", errors="ignore") as f:
                return (f.read() or "").strip() == "1"
    except Exception:
        pass
    try:
        if shutil.which("getenforce"):
            rc, out = _run_capture(["getenforce"], timeout=5)
            return rc == 0 and (out or "").strip().lower() == "enforcing"
    except Exception:
        pass
    return False


def _selinux_prepare_nfs_export(export_root, webhook_url):
    if not _selinux_enforcing():
        return
    if not has_admin_privileges():
        print_and_discord("SELinux is enforcing. NFS export may be blocked unless SELinux booleans are enabled. Run as root to auto-fix.", webhook_url)
        return
    if not shutil.which("setsebool"):
        return
    try:
        _run_capture(_sudo_prefix() + ["setsebool", "-P", "nfs_export_all_rw", "1"], timeout=60)
        if str(export_root).startswith("/home/"):
            _run_capture(_sudo_prefix() + ["setsebool", "-P", "use_nfs_home_dirs", "1"], timeout=60)
    except Exception:
        pass
    try:
        if shutil.which("chcon"):
            _run_capture(_sudo_prefix() + ["chcon", "-Rt", "public_content_rw_t", export_root], timeout=120)
    except Exception:
        pass


def _ensure_nfs_server_installed(webhook_url):
    if shutil.which("exportfs"):
        return True

    last_error = ""
    try:
        if shutil.which("apt-get"):
            rc, out = _run_capture(_sudo_prefix() + ["apt-get", "update"], timeout=180)
            if rc != 0:
                last_error = out
            rc, out = _run_capture(_sudo_prefix() + ["apt-get", "install", "-y", "nfs-kernel-server"], timeout=300)
            if rc != 0:
                last_error = out
        elif shutil.which("dnf"):
            rc, out = _run_capture(_sudo_prefix() + ["dnf", "install", "-y", "nfs-utils"], timeout=300)
            if rc != 0:
                last_error = out
        elif shutil.which("yum"):
            rc, out = _run_capture(_sudo_prefix() + ["yum", "install", "-y", "nfs-utils"], timeout=300)
            if rc != 0:
                last_error = out
        elif shutil.which("pacman"):
            rc, out = _run_capture(_sudo_prefix() + ["pacman", "-S", "--noconfirm", "nfs-utils"], timeout=300)
            if rc != 0:
                last_error = out
        else:
            print_and_discord(
                "NFS server error: no supported package manager found (apt, dnf, yum, pacman). Install NFS server packages manually.",
                webhook_url,
            )
            return False
    except Exception as e:
        last_error = str(e)

    if not shutil.which("exportfs"):
        needs_admin = is_privilege_error_text(last_error) or not has_admin_privileges()
        if needs_admin:
            print_and_discord(
                "NFS server error: missing exportfs/nfs tools and installation failed. Run this tool as root or ensure sudo works.",
                webhook_url,
            )
        else:
            print_and_discord(
                f"NFS server error: missing exportfs/nfs tools and installation failed: {last_error}",
                webhook_url,
            )
        return False
    return True


def _ensure_os_packages_installed(packages, webhook_url):
    global _apt_updated_once
    if not packages:
        return True

    pkgs = [str(p).strip() for p in packages if str(p).strip()]
    if not pkgs:
        return True

    with _pkg_install_lock:
        key = "|".join(pkgs)
        now = time.time()
        last = _pkg_install_attempted.get(key)
        if last is not None and (now - float(last)) < 60.0:
            return False
        _pkg_install_attempted[key] = now

        last_error = ""
        try:
            if shutil.which("apt-get"):
                if not _apt_updated_once:
                    rc, out = _run_capture(_sudo_prefix() + ["apt-get", "update"], timeout=180)
                    if rc == 0:
                        _apt_updated_once = True
                    else:
                        last_error = out
                rc, out = _run_capture(_sudo_prefix() + ["apt-get", "install", "-y"] + pkgs, timeout=300)
                if rc != 0:
                    last_error = out
            elif shutil.which("dnf"):
                rc, out = _run_capture(_sudo_prefix() + ["dnf", "install", "-y"] + pkgs, timeout=300)
                if rc != 0:
                    last_error = out
            elif shutil.which("yum"):
                rc, out = _run_capture(_sudo_prefix() + ["yum", "install", "-y"] + pkgs, timeout=300)
                if rc != 0:
                    last_error = out
            elif shutil.which("pacman"):
                rc, out = _run_capture(_sudo_prefix() + ["pacman", "-S", "--noconfirm"] + pkgs, timeout=300)
                if rc != 0:
                    last_error = out
            else:
                print_and_discord(
                    f"[AUTOMOUNT] No supported package manager found to install: {', '.join(pkgs)}",
                    webhook_url,
                )
                return False
        except Exception as exc:
            last_error = str(exc)

        if last_error:
            needs_admin = is_privilege_error_text(last_error) or not has_admin_privileges()
            if needs_admin:
                print_and_discord(
                    f"[AUTOMOUNT] OS package installation failed (admin required): {', '.join(pkgs)}",
                    webhook_url,
                )
            else:
                print_and_discord(
                    f"[AUTOMOUNT] OS package installation failed: {', '.join(pkgs)}\n{last_error}",
                    webhook_url,
                )
            return False
        return True


def _ensure_binary_available(binary, package_options, webhook_url):
    if shutil.which(binary):
        return True
    for pkgs in package_options or []:
        ok = _ensure_os_packages_installed(pkgs, webhook_url)
        if ok and shutil.which(binary):
            return True
    return bool(shutil.which(binary))


def _cleanup_managed_nfs_exports():
    with _managed_nfs_lock:
        export_paths = list(_managed_nfs_export_paths)
        _managed_nfs_export_paths.clear()

    for export_path in export_paths:
        try:
            if not export_path:
                continue
            if export_path == "/etc/exports":
                begin = "# multidisk_filebalancer BEGIN\n"
                end = "# multidisk_filebalancer END\n"
                try:
                    with open(export_path, "r", encoding="utf-8", errors="ignore") as f:
                        existing = f.read() or ""
                    if begin in existing and end in existing:
                        pre, _, rest = existing.partition(begin)
                        _, _, post = rest.partition(end)
                        updated = (pre.rstrip("\n") + "\n" + post.lstrip("\n")).strip("\n") + "\n"
                        with open(export_path, "w", encoding="utf-8") as f:
                            f.write(updated)
                except OSError:
                    pass
                continue

            if os.path.exists(export_path):
                os.remove(export_path)
        except Exception:
            pass

    if shutil.which("exportfs"):
        try:
            _run_capture(_sudo_prefix() + ["exportfs", "-ra"], timeout=60)
        except Exception:
            pass


def _register_managed_container(docker_exe, container_name):
    with _managed_docker_lock:
        _managed_docker_containers.append({'docker_exe': docker_exe, 'name': container_name})


def _stop_all_managed_containers():
    with _managed_docker_lock:
        containers = list(_managed_docker_containers)
        _managed_docker_containers.clear()
    seen = set()
    for entry in containers:
        name = entry['name']
        if name in seen:
            continue
        seen.add(name)
        docker_exe = entry['docker_exe']
        try:
            print(f"Stopping Docker container: {name}")
            subprocess.run([docker_exe, 'stop', name], capture_output=True, timeout=30)
            subprocess.run([docker_exe, 'rm', '-f', name], capture_output=True, timeout=15)
            print(f"Docker container stopped and removed: {name}")
        except Exception as e:
            print(f"Warning: could not stop container {name}: {e}")


def _docker_base_cmd(docker_exe):
    return _sudo_prefix() + [docker_exe]


def _docker_run_capture(docker_exe, args, timeout=60):
    cmd = _docker_base_cmd(docker_exe) + [str(a) for a in args]
    return _run_capture(cmd, timeout=timeout)


def _ensure_docker_daemon_running(docker_exe, webhook_url):
    rc, out = _docker_run_capture(docker_exe, ["info"], timeout=30)
    if rc == 0:
        return True

    if platform.system() != "Linux":
        print_and_discord("Docker ondersteuning is enkel voorzien voor Linux.", webhook_url)
        return False

    started = False
    try:
        if shutil.which("systemctl"):
            _run_capture(_sudo_prefix() + ["systemctl", "start", "docker"], timeout=90)
            _run_capture(_sudo_prefix() + ["systemctl", "enable", "docker"], timeout=90)
            started = True
        elif shutil.which("service"):
            _run_capture(_sudo_prefix() + ["service", "docker", "start"], timeout=90)
            started = True
    except Exception:
        started = False

    rc2, out2 = _docker_run_capture(docker_exe, ["info"], timeout=30)
    if rc2 == 0:
        return True

    if started:
        print_and_discord(f"Docker service started, but docker info still fails: {out2}", webhook_url)
    else:
        print_and_discord(f"Docker daemon not reachable: {out2}", webhook_url)
    return False


def _install_docker_if_missing(webhook_url):
    docker_exe = shutil.which("docker")
    if docker_exe:
        return True, False, docker_exe

    os_name = platform.system()
    attempted = False
    last_error = ""
    try:
        if os_name == "Linux":
            attempted = True
            if shutil.which("apt-get"):
                print_and_discord("Docker not found. Starting installation via apt-get...", webhook_url)
                rc, out = _run_stream(_sudo_prefix() + ["apt-get", "update"], timeout=600)
                if rc != 0:
                    last_error = out
                rc, out = _run_stream(_sudo_prefix() + ["apt-get", "install", "-y", "docker.io"], timeout=1800)
                if rc != 0:
                    last_error = out
            elif shutil.which("dnf"):
                print_and_discord("Docker not found. Starting installation via dnf...", webhook_url)
                rc, out = _run_stream(_sudo_prefix() + ["dnf", "install", "-y", "docker"], timeout=1800)
                if rc != 0:
                    last_error = out
                    rc2, out2 = _run_stream(_sudo_prefix() + ["dnf", "install", "-y", "moby-engine", "moby-cli"], timeout=1800)
                    if rc2 != 0:
                        last_error = out2 or last_error
            elif shutil.which("yum"):
                print_and_discord("Docker not found. Starting installation via yum...", webhook_url)
                rc, out = _run_stream(_sudo_prefix() + ["yum", "install", "-y", "docker"], timeout=1800)
                if rc != 0:
                    last_error = out
                    rc2, out2 = _run_stream(_sudo_prefix() + ["yum", "install", "-y", "moby-engine", "moby-cli"], timeout=1800)
                    if rc2 != 0:
                        last_error = out2 or last_error
            elif shutil.which("pacman"):
                print_and_discord("Docker not found. Starting installation via pacman...", webhook_url)
                rc, out = _run_stream(_sudo_prefix() + ["pacman", "-S", "--noconfirm", "docker"], timeout=1800)
                if rc != 0:
                    last_error = out
            else:
                print_and_discord(
                    "Docker is not installed and no supported package manager was found (apt, dnf, yum, pacman).",
                    webhook_url,
                )
                return False, False, None
        else:
            print_and_discord("Docker auto-install is only available for Linux (this is a Linux-only tool).", webhook_url)
            return False, False, None
    except Exception as exc:
        last_error = str(exc)

    docker_exe = shutil.which("docker")
    if not docker_exe:
        if attempted:
            print_and_discord(f"Tried to install Docker but docker is still not available: {last_error}", webhook_url)
        return False, attempted, None
    return True, attempted, docker_exe


def start_filebrowser_docker(filebrowser_config, fuse_mount_point, webhook_url):
    if not isinstance(filebrowser_config, dict):
        filebrowser_config = {}
    enabled = _coerce_bool(filebrowser_config.get("enabled", True), True)
    if not enabled:
        return

    if not fuse_mount_point:
        print_and_discord("Filebrowser: FUSE mount_point is missing. Enable fuse_server.enabled and configure mount_point.", webhook_url)
        return

    if not os.path.exists(fuse_mount_point):
        print_and_discord(f"Filebrowser: FUSE mount does not exist: {fuse_mount_point}", webhook_url)
        return
    try:
        if not os.path.ismount(fuse_mount_point):
            print_and_discord(f"Filebrowser: FUSE mount is not active yet at: {fuse_mount_point}", webhook_url)
            return
    except Exception:
        pass

    ok, installed_now, docker_exe = _install_docker_if_missing(webhook_url)
    if not ok or not docker_exe:
        return

    if installed_now and filebrowser_config.get("port") is None:
        default_port = _coerce_int(filebrowser_config.get("port", 8082), default=8082, min_value=1, max_value=65535)
        port_input = input(f"Filebrowser port (default {default_port}): ").strip()
        selected_port = _coerce_int(port_input, default=default_port, min_value=1, max_value=65535)
        filebrowser_config["port"] = selected_port
        try:
            cfg = _load_config_from_disk()
            if isinstance(cfg, dict):
                cfg["filebrowser"] = dict(filebrowser_config)
                _save_config_to_disk(cfg)
        except Exception:
            pass

    if not _ensure_docker_daemon_running(docker_exe, webhook_url):
        return

    port = _coerce_int(filebrowser_config.get("port", 8082), default=8082, min_value=1, max_value=65535)
    container_name = str(filebrowser_config.get("container_name", "filebrowser") or "filebrowser")
    image = str(filebrowser_config.get("image", "filebrowser/filebrowser") or "filebrowser/filebrowser")
    restart_policy = str(filebrowser_config.get("restart_policy", "unless-stopped") or "unless-stopped")
    try:
        base_repo = image.split(":", 1)[0]
        tag = image.split(":", 1)[1] if ":" in image else ""
        should_pin = (not tag) or (tag.lower() == "latest")
        if should_pin and base_repo == "filebrowser/filebrowser":
            rc_ver, out_ver = _docker_run_capture(docker_exe, ["run", "--rm", image, "version"], timeout=30)
            if rc_ver == 0 and out_ver:
                import re
                m = re.search(r"v(\d+\.\d+\.\d+)", out_ver)
                if m:
                    pinned_image = f"{base_repo}:v{m.group(1)}"
                    image = pinned_image
                    filebrowser_config["image"] = pinned_image
                    try:
                        cfg = _load_config_from_disk()
                        if isinstance(cfg, dict):
                            cfg_fb = cfg.get("filebrowser")
                            if not isinstance(cfg_fb, dict):
                                cfg_fb = {}
                            cfg_fb["image"] = pinned_image
                            cfg["filebrowser"] = cfg_fb
                            _save_config_to_disk(cfg)
                    except Exception:
                        pass
    except Exception:
        pass

    def _default_state_dir():
        try:
            if has_admin_privileges():
                return "/var/lib/multidisk-filebalancer/filebrowser"
        except Exception:
            pass
        return os.path.join(os.path.expanduser("~"), ".local", "share", "multidisk-filebalancer", "filebrowser")

    state_dir = str(filebrowser_config.get("state_dir") or "").strip()
    if not state_dir:
        default_state_dir = _default_state_dir()
        state_input = input(f"Path for Filebrowser data/config (default {default_state_dir}): ").strip()
        state_dir = state_input or default_state_dir
        filebrowser_config["state_dir"] = state_dir
        try:
            cfg = _load_config_from_disk()
            if isinstance(cfg, dict):
                cfg_fb = cfg.get("filebrowser")
                if not isinstance(cfg_fb, dict):
                    cfg_fb = {}
                cfg_fb["state_dir"] = state_dir
                if "port" in filebrowser_config:
                    cfg_fb["port"] = filebrowser_config.get("port")
                cfg["filebrowser"] = cfg_fb
                _save_config_to_disk(cfg)
        except Exception:
            pass

    database_dir = os.path.join(state_dir, "database")
    config_dir = os.path.join(state_dir, "config")
    os.makedirs(database_dir, exist_ok=True)
    os.makedirs(config_dir, exist_ok=True)
    try:
        os.chmod(state_dir, 0o755)
        os.chmod(database_dir, 0o777)
        os.chmod(config_dir, 0o777)
    except Exception:
        pass
    try:
        with open(os.path.join(config_dir, ".write_test"), "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(os.path.join(config_dir, ".write_test"))
    except Exception as exc:
        if str(state_dir).startswith("/media/sf_") or str(state_dir).startswith("/media/sf-") or str(state_dir).startswith("/media/sf"):
            print_and_discord(f"Filebrowser: no write permission in {state_dir} (VirtualBox shared folder). Choose a path on the local Linux disk (e.g. /var/lib/...). Error: {exc}", webhook_url)
        else:
            print_and_discord(f"Filebrowser: no write permission in {state_dir}. Error: {exc}", webhook_url)
        return

    print_and_discord(f"Filebrowser host folders: database={database_dir}, config={config_dir}", webhook_url)
    db_path_in_container = "/database/filebrowser.db"
    branding_dir_host = os.path.join(config_dir, "branding")
    try:
        os.makedirs(branding_dir_host, exist_ok=True)
        with open(os.path.join(branding_dir_host, "custom.css"), "w", encoding="utf-8") as f:
            f.write(
                "aside .used, aside .usage, aside .credits, aside .sidebar__footer, aside .sidebar-footer, aside .sidebar__credits {\n"
                "  display: none !important;\n"
                "}\n"
            )
    except Exception:
        pass
    is_first_db_boot = not os.path.exists(os.path.join(database_dir, "filebrowser.db"))
    username = str(filebrowser_config.get("username") or "admin").strip() or "admin"
    password = None
    configured_password = str(filebrowser_config.get("password") or "").strip()
    if configured_password:
        if len(configured_password) < 12:
            print_and_discord("Filebrowser: password in config.yml is too short (min 12). Update is skipped.", webhook_url)
        else:
            password = configured_password

    need_credentials = (is_first_db_boot or not _coerce_bool(filebrowser_config.get("credentials_initialized", False), False))
    if need_credentials and not password:
        if not str(filebrowser_config.get("username") or "").strip():
            username_input = input(f"Filebrowser username (default {username}): ").strip()
            username = username_input or username
        while True:
            p1 = input("Filebrowser password: ").strip()
            p2 = input("Filebrowser password (again): ").strip()
            if p1 != p2:
                print("Passwords do not match. Try again.")
                continue
            if not p1:
                print("Password cannot be empty.")
                continue
            if len(p1) < 12:
                print("Password is too short. Minimum length is 12.")
                continue
            password = p1
            break

    def _docker_run_filebrowser_cli(args, timeout=120):
        selinux_suffix = ":Z" if _selinux_enforcing() else ""
        return _docker_run_capture(
            docker_exe,
            [
                "run",
                "--rm",
                "--user",
                f"{os.geteuid()}:{os.getegid()}",
                "-v",
                f"{fuse_mount_point}:/srv{selinux_suffix}",
                "-v",
                f"{database_dir}:/database{selinux_suffix}",
                "-v",
                f"{config_dir}:/config{selinux_suffix}",
                image,
            ] + [str(a) for a in args],
            timeout=timeout,
        )

    if password:
        rc_init, out_init = _docker_run_filebrowser_cli(["config", "init", "-d", db_path_in_container, "-r", "/srv"], timeout=120)
        if rc_init != 0 and not os.path.exists(os.path.join(database_dir, "filebrowser.db")):
            print_and_discord(f"Filebrowser init failed: {out_init}", webhook_url)
            return
        rc_find, _ = _docker_run_filebrowser_cli(["users", "find", username, "-d", db_path_in_container], timeout=60)
        if rc_find == 0:
            rc_set, out_set = _docker_run_filebrowser_cli(["users", "update", username, "--password", password, "--perm.admin", "-d", db_path_in_container], timeout=120)
            if rc_set != 0:
                print_and_discord(f"Failed to set Filebrowser credentials:\n{out_set}", webhook_url)
                return
        else:
            rc_add, out_add = _docker_run_filebrowser_cli(["users", "add", username, password, "--perm.admin", "-d", db_path_in_container], timeout=120)
            if rc_add != 0:
                print_and_discord(f"Failed to set Filebrowser credentials:\n{out_add}", webhook_url)
                return
        filebrowser_config["username"] = username
        filebrowser_config["password"] = password
        filebrowser_config["credentials_initialized"] = True
        try:
            cfg = _load_config_from_disk()
            if isinstance(cfg, dict):
                cfg_fb = cfg.get("filebrowser")
                if not isinstance(cfg_fb, dict):
                    cfg_fb = {}
                cfg_fb["username"] = username
                cfg_fb["password"] = password
                cfg_fb["credentials_initialized"] = True
                cfg_fb["state_dir"] = state_dir
                cfg["filebrowser"] = cfg_fb
                _save_config_to_disk(cfg)
        except Exception:
            pass
        rc_verify, out_verify = _docker_run_filebrowser_cli(["users", "find", username, "-d", db_path_in_container], timeout=60)
        if rc_verify == 0:
            print_and_discord(f"Filebrowser credentials ready. Log in with user: {username}", webhook_url)
        else:
            print_and_discord(f"Filebrowser credentials set, but verification failed: {out_verify}", webhook_url)

    try:
        if os.path.exists(os.path.join(database_dir, "filebrowser.db")):
            _docker_run_filebrowser_cli(
                [
                    "config",
                    "set",
                    "-d",
                    db_path_in_container,
                    "--branding.files",
                    "/config/branding",
                    "--branding.disableExternal",
                    "--branding.disableUsedPercentage",
                ],
                timeout=60,
            )
    except Exception:
        pass

    _, existing = _docker_run_capture(
        docker_exe,
        ["ps", "-a", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"],
        timeout=30,
    )
    exists = any(line.strip() == container_name for line in (existing or "").splitlines())
    if exists:
        _docker_run_capture(docker_exe, ["rm", "-f", container_name], timeout=60)

    selinux_suffix = ":Z" if _selinux_enforcing() else ""
    rc, out = _docker_run_capture(
        docker_exe,
        [
            "run",
            "-d",
            "--name",
            container_name,
            "--user",
            f"{os.geteuid()}:{os.getegid()}",
            "-v",
            f"{fuse_mount_point}:/srv{selinux_suffix}",
            "-v",
            f"{database_dir}:/database{selinux_suffix}",
            "-v",
            f"{config_dir}:/config{selinux_suffix}",
            "-p",
            f"{port}:80",
            "--restart",
            restart_policy,
            image,
        ],
        timeout=120,
    )
    if rc != 0:
        print_and_discord(f"Filebrowser Docker error: {out}", webhook_url)
        return

    rc_state, state_out = _docker_run_capture(docker_exe, ["inspect", "-f", "{{.State.Status}}|{{.State.Running}}|{{.State.ExitCode}}", container_name], timeout=30)
    status = ""
    running = ""
    exit_code = ""
    if rc_state == 0 and state_out:
        parts = state_out.strip().split("|")
        if len(parts) >= 3:
            status, running, exit_code = parts[0], parts[1], parts[2]
    if status and status != "running":
        _, logs = _docker_run_capture(docker_exe, ["logs", "--tail", "200", container_name], timeout=30)
        print_and_discord(f"Filebrowser container status: {status} (exit {exit_code}). Logs:\n{logs}", webhook_url)
        return

    try:
        import socket
        ready = False
        for _ in range(30):
            try:
                with socket.create_connection(("127.0.0.1", int(port)), timeout=0.5):
                    ready = True
                    break
            except OSError:
                time.sleep(0.5)
        if not ready:
            _, logs = _docker_run_capture(docker_exe, ["logs", "--tail", "200", container_name], timeout=30)
            print_and_discord(f"Filebrowser started, but port {port} is not reachable. Logs:\n{logs}", webhook_url)
            return
    except Exception:
        pass

    _register_managed_container(docker_exe, container_name)
    urls = [f"http://localhost:{port}"]
    try:
        res = subprocess.run(["hostname", "-I"], capture_output=True, text=True)
        ips = [p.strip() for p in (res.stdout or "").split() if p.strip() and not p.strip().startswith("127.")]
        for ip in ips[:3]:
            urls.append(f"http://{ip}:{port}")
    except Exception:
        pass
    print_and_discord(f"Filebrowser started ({container_name}). URLs: {', '.join(urls)}", webhook_url)


def _invalidate_vfs_caches():
    with _vfs_cache_lock:
        _vfs_dir_cache.clear()


def _current_base_cache_key(base_paths):
    result = []
    for path in base_paths:
        if not path:
            continue
        normalized = os.path.normcase(os.path.normpath(str(path)))
        result.append(normalized)
    return tuple(result)


def set_vfs_base_paths(paths):
    with _vfs_cache_lock:
        _vfs_base_paths.clear()
        for p in paths:
            if p:
                _vfs_base_paths.append(p)
    _invalidate_vfs_caches()


def get_vfs_base_paths():
    with _vfs_cache_lock:
        return list(_vfs_base_paths)

def set_vfs_dedupe_duplicate_names(enabled):
    global _vfs_dedupe_duplicate_names
    with _vfs_cache_lock:
        _vfs_dedupe_duplicate_names = bool(enabled)
    _invalidate_vfs_caches()

def get_vfs_dedupe_duplicate_names():
    with _vfs_cache_lock:
        return bool(_vfs_dedupe_duplicate_names)


def _normalized_existing_path_entries(paths):
    normalized_paths = []
    seen = set()
    for path in paths:
        if not path:
            continue
        normalized = os.path.normcase(os.path.normpath(str(path)))
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_paths.append(path)
    return normalized_paths


def build_vfs_base_paths(src_folders, disks, extra_paths=None):
    all_paths = []
    for path in src_folders:
        all_paths.append(path)

    for disk in disks:
        if not isinstance(disk, dict):
            continue
        disk_path = disk.get('path')
        if not disk_path:
            disk_path = disk.get('pad')
        all_paths.append(disk_path)

    if extra_paths:
        for path in extra_paths:
            all_paths.append(path)

    return _normalized_existing_path_entries(all_paths)


def normalize_virtual_path(virtual_path):
    if not virtual_path:
        return '/'
    cleaned_path = virtual_path.strip()
    if cleaned_path.startswith('/'):
        return cleaned_path
    return '/' + cleaned_path


def _hashed_virtual_name(file_name, physical_path):
    stem, ext = os.path.splitext(file_name)
    path_hash = hashlib.sha1(physical_path.encode('utf-8', errors='ignore')).hexdigest()[:8]
    return f"{stem}__{path_hash}{ext}"


def _join_virtual_path(virtual_dir, name):
    if virtual_dir == '/':
        return '/' + name
    return virtual_dir.rstrip('/') + '/' + name


def _split_virtual_parent_and_name(virtual_path):
    virt = normalize_virtual_path(virtual_path)
    if virt == '/':
        return '/', ''
    parent, _, name = virt.rpartition('/')
    if not parent:
        parent = '/'
    return parent, name


def _collect_virtual_directory_snapshot(virtual_dir):
    virt_dir = normalize_virtual_path(virtual_dir)
    base_paths = get_vfs_base_paths()
    cache_key = (_current_base_cache_key(base_paths), virt_dir)
    now = time.time()
    with _vfs_cache_lock:
        cached = _vfs_dir_cache.get(cache_key)
        if cached and (now - cached['ts']) <= _vfs_cache_ttl_seconds:
            return {'files': dict(cached['files']), 'dirs': set(cached['dirs'])}

    rel = virt_dir.lstrip('/')
    seen_paths = set()
    dirs = set()
    basename_records = {}

    scan_failures = []
    successful_scans = 0
    scanned_paths = 0

    for base in base_paths:
        if rel:
            scan_path = os.path.join(base, rel)
        else:
            scan_path = base
        if not os.path.isdir(scan_path):
            continue
        scanned_paths += 1
        try:
            with os.scandir(scan_path) as entries:
                successful_scans += 1
                for entry in entries:
                    try:
                        entry_name = entry.name
                        entry_path = entry.path
                        norm_entry_path = os.path.normcase(os.path.normpath(entry_path))
                        if norm_entry_path in seen_paths:
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            seen_paths.add(norm_entry_path)
                            dirs.add(entry_name)
                        elif entry.is_file(follow_symlinks=False):
                            seen_paths.add(norm_entry_path)
                            basename_records.setdefault(entry_name, []).append(entry_path)
                    except OSError as exc:
                        logger.debug(
                            "Skipping unreadable dir entry in virtual_dir=%s scan_path=%s: %s",
                            virt_dir,
                            scan_path,
                            exc,
                        )
                        continue
        except OSError as exc:
            scan_failures.append((scan_path, exc))
            continue

    if scanned_paths > 0 and successful_scans == 0 and scan_failures:
        first_path, first_exc = scan_failures[0]
        logger.error(
            "Directory scan failed for virtual_dir=%s (all %d scanned paths failed). First failure at %s: %s",
            virt_dir,
            scanned_paths,
            first_path,
            first_exc,
        )
        raise OSError(errno.EIO, f"Failed to scan virtual directory {virt_dir}")

    files = {}
    occupied_names = set(dirs)
    for file_name, physical_paths in basename_records.items():
        sorted_physical_paths = sorted(physical_paths)
        if get_vfs_dedupe_duplicate_names() and file_name not in occupied_names:
            files[file_name] = sorted_physical_paths[0]
            occupied_names.add(file_name)
            continue
        if len(sorted_physical_paths) == 1 and file_name not in occupied_names:
            files[file_name] = sorted_physical_paths[0]
            occupied_names.add(file_name)
            continue
        for physical_path in sorted_physical_paths:
            candidate_name = _hashed_virtual_name(file_name, physical_path)
            while candidate_name in occupied_names or candidate_name in files:
                candidate_name = _hashed_virtual_name(candidate_name, physical_path)
            files[candidate_name] = physical_path
            occupied_names.add(candidate_name)

    snapshot = {'files': files, 'dirs': dirs}
    with _vfs_cache_lock:
        _vfs_dir_cache[cache_key] = {
            'ts': now,
            'files': dict(files),
            'dirs': set(dirs),
        }
    return {'files': dict(files), 'dirs': set(dirs)}


def get_virtual_item_info(virtual_path):
    """Returns (is_file, is_dir, physical_path) for a virtual path."""
    virt = normalize_virtual_path(virtual_path)
    if virt == '/':
        return False, True, None

    parent, item_name = _split_virtual_parent_and_name(virt)
    snapshot = _collect_virtual_directory_snapshot(parent)
    physical_path = snapshot['files'].get(item_name)
    if physical_path and os.path.exists(physical_path):
        return True, False, physical_path
    if item_name in snapshot['dirs']:
        rel = virt.lstrip('/')
        for base in get_vfs_base_paths():
            candidate = os.path.join(base, rel)
            if os.path.isdir(candidate):
                return False, True, candidate
        return False, True, None
    return False, False, None


def list_virtual_dir(virtual_dir):
    """Returns a dictionary mapping names to full virtual paths for children of virtual_dir."""
    virt_dir = normalize_virtual_path(virtual_dir)
    snapshot = _collect_virtual_directory_snapshot(virt_dir)
    names = {}
    for name in sorted(snapshot['dirs']):
        names[name] = _join_virtual_path(virt_dir, name)
    for name in sorted(snapshot['files']):
        names[name] = _join_virtual_path(virt_dir, name)
    return names


def get_physical_path_for_virtual(virtual_path):
    is_file, _is_dir, physical_path = get_virtual_item_info(virtual_path)
    if not is_file:
        return None
    return physical_path


def _find_docker_executable():
    if shutil.which("docker"):
        # Intentionally use plain "docker" so command resolution behaves like a regular shell.
        return "docker"
    return None


def _docker_port_arg(bind_host, host_port, container_port, protocol='tcp'):
    bind_host = str(bind_host or "").strip()
    host_port = int(host_port)
    container_port = int(container_port)
    if not bind_host or bind_host in ("0.0.0.0", "::"):
        mapping = f"{host_port}:{container_port}"
    else:
        mapping = f"{bind_host}:{host_port}:{container_port}"
    protocol = str(protocol or "").strip().lower()
    if protocol in ("tcp", "udp"):
        mapping = f"{mapping}/{protocol}"
    return mapping


def _run_docker_command(docker_exe, args):
    _ensure_linux()
    cmd = [docker_exe] + [str(arg) for arg in args]
    env = os.environ.copy()
    env.setdefault('DOCKER_CLI_PROGRESS', 'tty')
    result = subprocess.run(cmd, env=env)
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=result.returncode,
        stdout='',
        stderr='',
    )


def _replace_docker_container(docker_exe, container_name, run_args, webhook_url):
    inspect_result = subprocess.run(
        [docker_exe, 'ps', '-a', '--filter', f'name=^{container_name}$', '--format', '{{.ID}}'],
        capture_output=True,
        text=True,
    )
    if inspect_result.returncode != 0:
        err = (inspect_result.stderr or inspect_result.stdout or "").strip()
        print_and_discord(f"Docker inspect error for container {container_name}: {err}", webhook_url)
        return None

    existing_id = (inspect_result.stdout or "").strip()
    if existing_id:
        rm_result = subprocess.run(
            [docker_exe, 'rm', '-f', container_name],
            capture_output=True,
            text=True,
        )
        if rm_result.returncode != 0:
            err = (rm_result.stderr or rm_result.stdout or "").strip()
            print_and_discord(f"Could not remove existing Docker container {container_name}: {err}", webhook_url)
            return None

    run_result = _run_docker_command(
        docker_exe,
        ['run', '-d', '--name', container_name] + list(run_args),
    )
    if run_result.returncode != 0:
        err = (run_result.stderr or run_result.stdout or "").strip()
        print_and_discord(f"Could not start Docker container {container_name}: {err}", webhook_url)
        return None
    return container_name


def start_nfs_server_thread(nfs_config, upload_src_path, webhook_url, serve_root_path=None):
    if not nfs_config.get('enabled', False):
        return

    host = nfs_config.get('host', '0.0.0.0')
    nfs_port = int(nfs_config.get('port', 2049))
    permitted = str(nfs_config.get('permitted', '*'))

    if serve_root_path:
        nfs_root = serve_root_path
    else:
        nfs_root = upload_src_path

    os.makedirs(nfs_root, exist_ok=True)

    def run_server():
        if not _ensure_nfs_server_installed(webhook_url):
            return

        if nfs_port != 2049:
            print_and_discord(
                f"NFS server warning: custom port {nfs_port} is not supported with the kernel NFS server in this tool. Using default port 2049.",
                webhook_url,
            )

        if shutil.which("systemctl"):
            for svc in ("rpcbind", "rpcbind.socket"):
                _run_capture(_sudo_prefix() + ["systemctl", "enable", "--now", svc], timeout=60)
            for svc in ("nfs-idmapd", "rpc-statd", "rpc-statd.service"):
                _run_capture(_sudo_prefix() + ["systemctl", "enable", "--now", svc], timeout=60)

        permitted_spec = (permitted or "*").strip() or "*"
        export_root = os.path.abspath(nfs_root)
        _selinux_prepare_nfs_export(export_root, webhook_url)
        export_line = f"{export_root} {permitted_spec}(rw,sync,no_subtree_check,no_root_squash,fsid=0,crossmnt,insecure)\n"

        export_dir = "/etc/exports.d"
        if os.path.isdir(export_dir):
            export_path = os.path.join(export_dir, "multidisk_filebalancer.exports")
            try:
                with open(export_path, "w", encoding="utf-8") as f:
                    f.write(export_line)
                _register_managed_nfs_export_path(export_path)
            except Exception as e:
                print_and_discord(f"NFS server error: could not write {export_path}: {e}", webhook_url)
                return
        else:
            exports_path = "/etc/exports"
            begin = "# multidisk_filebalancer BEGIN\n"
            end = "# multidisk_filebalancer END\n"
            try:
                existing = ""
                try:
                    with open(exports_path, "r", encoding="utf-8", errors="ignore") as f:
                        existing = f.read() or ""
                except OSError:
                    existing = ""
                if begin in existing and end in existing:
                    pre, _, rest = existing.partition(begin)
                    _, _, post = rest.partition(end)
                    updated = pre + begin + export_line + end + post
                else:
                    updated = existing.rstrip("\n") + "\n" + begin + export_line + end
                with open(exports_path, "w", encoding="utf-8") as f:
                    f.write(updated)
                _register_managed_nfs_export_path(exports_path)
            except Exception as e:
                print_and_discord(f"NFS server error: could not update {exports_path}: {e}", webhook_url)
                return

        rc, out = _run_capture(_sudo_prefix() + ["exportfs", "-ra"], timeout=60)
        if rc != 0:
            print_and_discord(f"NFS server error: exportfs reload failed: {out}", webhook_url)
            return

        if shutil.which("systemctl"):
            started_any = False
            for svc in ("nfs-server", "nfs-kernel-server"):
                rc1, _ = _run_capture(_sudo_prefix() + ["systemctl", "enable", "--now", svc], timeout=90)
                if rc1 == 0:
                    started_any = True
                    _run_capture(_sudo_prefix() + ["systemctl", "restart", svc], timeout=90)
            if not started_any:
                _run_capture(_sudo_prefix() + ["systemctl", "restart", "nfs-server"], timeout=90)
                _run_capture(_sudo_prefix() + ["systemctl", "restart", "nfs-kernel-server"], timeout=90)
        elif shutil.which("service"):
            for svc in ("nfs-server", "nfs-kernel-server"):
                _run_capture(_sudo_prefix() + ["service", svc, "restart"], timeout=90)

        print_and_discord(f"NFS server configured on {host}:2049", webhook_url)
        print_and_discord(f"NFSv4 export root: {export_root}", webhook_url)
        print_and_discord("Tip: mount using <server-ip>:/", webhook_url)

    threading.Thread(target=run_server, daemon=True).start()

def start_webdav_server_thread(webdav_config, upload_src_path, webhook_url, serve_root_path=None):
    if not webdav_config.get('enabled', False):
        return
    
    try:
        from wsgidav.wsgidav_app import WsgiDAVApp
        from cheroot import wsgi
    except ImportError:
        print_and_discord("WebDAV error: 'wsgidav' or 'cheroot' not installed. Check requirements.txt.", webhook_url)
        return

    host = webdav_config.get('host', '0.0.0.0')
    port = int(webdav_config.get('port', 8080))
    username = webdav_config.get('username')
    password = webdav_config.get('password')
    
    # Use FUSE mount path if provided, otherwise fallback to upload_src
    if serve_root_path:
        dav_root = serve_root_path
    else:
        dav_root = upload_src_path
    
    auth_config = {"user_mapping": {"*": True}}
    if username and password:
        auth_config = {"user_mapping": {"*": {username: {"password": password}}}}

    config = {
        "host": host,
        "port": port,
        "provider_mapping": {"/": dav_root},
        "simple_dc": auth_config,
        "verbose": 1,
    }

    app = WsgiDAVApp(config)

    def run_server():
        try:
            server = wsgi.Server((host, port), app)
            print_and_discord(f"WebDAV server started on {host}:{port}", webhook_url)
            server.start()
        except Exception as e:
            print_and_discord(f"Could not start WebDAV server: {e}", webhook_url)

    threading.Thread(target=run_server, daemon=True).start()


class FileBalancerSSHServer(asyncssh.SSHServer):
    def __init__(self, username, password, webhook_url):
        self._username = username
        self._password = password
        self._webhook_url = webhook_url

    def connection_made(self, conn):
        peer = conn.get_extra_info('peername')
        local = conn.get_extra_info('sockname')
        print_and_discord(f"SSH connection received from {peer} to local address {local}", self._webhook_url)

    def connection_lost(self, exc):
        if exc:
            print_and_discord(f"SSH connection lost with error: {exc}", self._webhook_url)
        else:
            print_and_discord(f"SSH connection closed", self._webhook_url)

    def begin_auth(self, username):
        return True

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        is_valid = (username == self._username and password == self._password)
        if not is_valid:
            print_and_discord(f"SFTP login failed for user: {username}", self._webhook_url)
        else:
            print_and_discord(f"SFTP login successful for user: {username}", self._webhook_url)
        return is_valid

class FileBalancerSFTPServer(asyncssh.SFTPServer):
    def __init__(self, chan, upload_src_path, serve_root_path=None):
        self._upload_src_path = upload_src_path
        if serve_root_path:
            self._serve_root_path = os.path.normpath(serve_root_path)
        else:
            self._serve_root_path = None
        os.makedirs(self._upload_src_path, exist_ok=True)
        super().__init__(chan)

    def _normalize_virtual(self, path):
        if isinstance(path, bytes):
            path_str = path.decode('utf-8', errors='ignore')
        else:
            path_str = str(path)
        if path_str in ('', '.', './', '/.', '/'):
            return '/'
        return normalize_virtual_path(path_str)

    def _upload_physical_path(self, virt):
        rel = virt.lstrip('/')
        if rel:
            return os.path.join(self._upload_src_path, rel)
        return self._upload_src_path

    def _resolve_under_root(self, virt):
        if not self._serve_root_path:
            return False, False, None
        if virt == '/':
            return False, True, self._serve_root_path
        rel = virt.lstrip('/').replace('/', os.sep)
        candidate = os.path.normpath(os.path.join(self._serve_root_path, rel))
        root_norm = os.path.normcase(os.path.normpath(self._serve_root_path))
        candidate_norm = os.path.normcase(candidate)
        if candidate_norm != root_norm and not candidate_norm.startswith(root_norm + os.sep):
            return False, False, None
        if os.path.isfile(candidate):
            return True, False, candidate
        if os.path.isdir(candidate):
            return False, True, candidate
        return False, False, None

    def _resolve_virtual_item(self, virt):
        if not self._serve_root_path:
            return get_virtual_item_info(virt)
        return self._resolve_under_root(virt)

    def canonicalize(self, path):
        virt = self._normalize_virtual(path)
        return virt.encode('utf-8')

    def realpath(self, path):
        virt = self._normalize_virtual(path)
        return virt.encode('utf-8')

    async def scandir(self, path):
        virt_dir = self._normalize_virtual(path)
        if self._serve_root_path:
            is_file, is_dir, scan_path = self._resolve_under_root(virt_dir)
            if not is_dir or not scan_path or not os.path.isdir(scan_path):
                names = {}
            else:
                names = {}
                try:
                    for name in os.listdir(scan_path):
                        names[name] = virt_dir.rstrip('/') + '/' + name
                except OSError:
                    names = {}
        else:
            names = list_virtual_dir(virt_dir)

        # Add standard directory entries
        for name in ('.', '..'):
            now = int(time.time())
            attrs = SFTPAttrs(permissions=stat.S_IFDIR | 0o755, atime=now, mtime=now, size=0)
            yield SFTPName(name.encode('utf-8'), None, attrs)

        for name, full_virtual in names.items():
            is_file, is_dir, physical_path = self._resolve_virtual_item(full_virtual)
            if physical_path and os.path.exists(physical_path):
                st = os.stat(physical_path)
                attrs = SFTPAttrs.from_local(st)
            else:
                if is_dir:
                    mode = stat.S_IFDIR | 0o755
                else:
                    mode = stat.S_IFREG | 0o644
                now = int(time.time())
                attrs = SFTPAttrs(
                    permissions=mode,
                    atime=now,
                    mtime=now,
                    size=0
                )
            yield SFTPName(name.encode('utf-8'), None, attrs)

    async def _stat_helper(self, path, follow_symlinks=True):
        virt = self._normalize_virtual(path)
        is_file, is_dir, physical_path = self._resolve_virtual_item(virt)
        if physical_path and os.path.exists(physical_path):
            if follow_symlinks:
                st = os.stat(physical_path)
            else:
                st = os.lstat(physical_path)
            return SFTPAttrs.from_local(st)
        if is_dir:
            mode = stat.S_IFDIR | 0o755
            now = int(time.time())
            return SFTPAttrs(permissions=mode, atime=now, mtime=now, size=0)
        raise asyncssh.SFTPNoSuchFile(virt)

    async def stat(self, path):
        return await self._stat_helper(path, follow_symlinks=True)

    async def lstat(self, path):
        return await self._stat_helper(path, follow_symlinks=False)

    def _mode_from_pflags(self, pflags):
        read = bool(pflags & FXF_READ)
        write = bool(pflags & FXF_WRITE)
        append = bool(pflags & FXF_APPEND)
        creat = bool(pflags & FXF_CREAT)
        trunc = bool(pflags & FXF_TRUNC)
        if read and not write:
            return 'rb'
        if write and not read:
            if append and not trunc:
                return 'ab'
            if trunc or creat:
                return 'wb'
            return 'wb'
        if read and write:
            if append and not trunc:
                return 'a+b'
            if trunc or creat:
                return 'w+b'
            return 'r+b'
        return 'rb'

    async def open(self, path, pflags, attrs):
        virt = self._normalize_virtual(path)
        write = bool(pflags & FXF_WRITE)
        if write:
            rel = virt.lstrip('/')
            if not rel:
                raise asyncssh.SFTPFailure('Invalid file name')
            with _file_operation_lock:
                physical_path = os.path.join(self._upload_src_path, rel)
                os.makedirs(os.path.dirname(physical_path), exist_ok=True)
                _invalidate_vfs_caches()
        else:
            is_file, _is_dir, physical_path = self._resolve_virtual_item(virt)
            if not physical_path or not os.path.exists(physical_path):
                raise asyncssh.SFTPNoSuchFile(virt)
        mode = self._mode_from_pflags(pflags)
        f = open(physical_path, mode)
        return f

    async def remove(self, path):
        virt = self._normalize_virtual(path)
        is_file, _is_dir, physical_path = self._resolve_virtual_item(virt)
        if physical_path and os.path.exists(physical_path):
            with _file_operation_lock:
                os.remove(physical_path)
                _invalidate_vfs_caches()
            return
        raise asyncssh.SFTPNoSuchFile(virt)

    async def mkdir(self, path, attrs):
        virt = self._normalize_virtual(path)
        physical_path = self._upload_physical_path(virt)
        with _file_operation_lock:
            os.makedirs(physical_path, exist_ok=True)
            _invalidate_vfs_caches()

    async def rmdir(self, path):
        virt = self._normalize_virtual(path)
        is_file, is_dir, physical_path = self._resolve_virtual_item(virt)
        if not is_dir:
            raise asyncssh.SFTPNoSuchFile(virt)
        if physical_path and os.path.isdir(physical_path):
            try:
                with _file_operation_lock:
                    os.rmdir(physical_path)
                    _invalidate_vfs_caches()
            except OSError as exc:
                raise asyncssh.SFTPFailure(str(exc)) from exc
            return
        if self._serve_root_path:
            raise asyncssh.SFTPNoSuchFile(virt)
        rel = virt.lstrip('/')
        for base in get_vfs_base_paths():
            candidate = os.path.join(base, rel)
            if os.path.isdir(candidate):
                try:
                    with _file_operation_lock:
                        os.rmdir(candidate)
                        _invalidate_vfs_caches()
                except OSError as exc:
                    raise asyncssh.SFTPFailure(str(exc)) from exc
                return
        raise asyncssh.SFTPNoSuchFile(virt)

    async def rename(self, oldpath, newpath, flags=0):
        old_virt = self._normalize_virtual(oldpath)
        new_virt = self._normalize_virtual(newpath)
        is_file, is_dir, old_physical = self._resolve_virtual_item(old_virt)
        if not old_physical or not os.path.exists(old_physical):
            raise asyncssh.SFTPNoSuchFile(old_virt)
        new_rel = new_virt.lstrip('/')
        with _file_operation_lock:
            new_physical = os.path.join(self._upload_src_path, new_rel)
            os.makedirs(os.path.dirname(new_physical), exist_ok=True)
            os.rename(old_physical, new_physical)
            _invalidate_vfs_caches()

def start_sftp_server_thread(sftp_config, upload_src_path, webhook_url, serve_root_path=None):
    if not sftp_config.get('enabled', False):
        return

    host = sftp_config.get('host', '0.0.0.0')
    port = int(sftp_config.get('port', 8081))
    username_cfg = sftp_config.get('username', 'raiduser')
    password_cfg = sftp_config.get('password', 'changeme')
    host_key_path = sftp_config.get('host_key_path')

    async def start_server():
        try:
            import socket

            # Check if port is already in use
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind((host, port))
                except socket.error:
                    print_and_discord(f"ERROR: SFTP Port {port} is already in use by another process!", webhook_url)
                    print_and_discord(f"Use 'ss -tlnp | grep {port}' to find the conflicting process.", webhook_url)
                    return

            hostname = socket.gethostname()
            local_ips = [socket.gethostbyname(hostname)]
            try:
                # Add all interface IPs on Linux
                import subprocess
                res = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                local_ips.extend(res.stdout.split())
            except Exception:
                pass
            unique_ips = sorted(list(set(local_ips)))
            print_and_discord(f"Starting SFTP server (asyncssh {asyncssh.__version__}) on {host}:{port}...", webhook_url)
            print_and_discord(f"Detected VM IPs: {', '.join(unique_ips)}", webhook_url)
            if serve_root_path:
                print_and_discord(f"SFTP root mode: physical path {serve_root_path}", webhook_url)
            server_host_keys = []
            if host_key_path and os.path.exists(host_key_path):
                server_host_keys = [host_key_path]
            else:
                try:
                    ed25519_key = asyncssh.generate_private_key('ssh-ed25519')
                    server_host_keys.append(ed25519_key)
                except Exception as e:
                    print_and_discord(f"Warning: could not generate Ed25519 key: {e}", webhook_url)
                try:
                    rsa_key = asyncssh.generate_private_key('ssh-rsa')
                    server_host_keys.append(rsa_key)
                except Exception as e:
                    print_and_discord(f"Warning: could not generate RSA key: {e}", webhook_url)

            if not server_host_keys:
                server_host_keys = None

            def make_server():
                return FileBalancerSSHServer(username_cfg, password_cfg, webhook_url)

            def make_sftp(chan):
                return FileBalancerSFTPServer(
                    chan,
                    upload_src_path,
                    serve_root_path=serve_root_path,
                )

            server = await asyncssh.listen(
                host,
                port,
                server_factory=make_server,
                server_host_keys=server_host_keys,
                sftp_factory=make_sftp,
            )

            actual_host, actual_port = server.sockets[0].getsockname()[:2]
            print_and_discord(f"SUCCESS: SFTP server is READY and listening on {actual_host}:{actual_port}", webhook_url)
            if host == '127.0.0.1':
                print_and_discord("CRITICAL WARNING: SFTP server is bound ONLY to 127.0.0.1.", webhook_url)
                print_and_discord("Connections from OUTSIDE the VM (including VirtualBox port forwarding) will fail.", webhook_url)
                print_and_discord("Please set 'host: 0.0.0.0' in config.yml to allow external connections.", webhook_url)
            await server.wait_closed()
        except Exception as e:
            print_and_discord(f"SFTP server error during startup or execution: {e}", webhook_url)

    def run_server():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start_server())
        except Exception as e:
            print_and_discord(f"Could not start SFTP server: {e}", webhook_url)

    threading.Thread(target=run_server, daemon=True).start()

def create_virtual_fuse_class():
    class VirtualFUSE(Operations):
        def __init__(self, upload_src_path):
            self.upload_src_path = upload_src_path
            os.makedirs(self.upload_src_path, exist_ok=True)

        def _upload_physical_path(self, path):
            rel = path.lstrip('/')
            if rel:
                return os.path.join(self.upload_src_path, rel)
            return self.upload_src_path

        def getattr(self, path, fh=None):
            try:
                is_file, is_dir, physical_path = get_virtual_item_info(path)
                if physical_path and os.path.exists(physical_path):
                    st = os.lstat(physical_path)
                    return {
                        'st_atime': st.st_atime,
                        'st_ctime': st.st_ctime,
                        'st_gid': st.st_gid,
                        'st_mode': st.st_mode,
                        'st_mtime': st.st_mtime,
                        'st_nlink': st.st_nlink,
                        'st_size': st.st_size,
                        'st_uid': st.st_uid,
                    }
                if is_dir:
                    mode = stat.S_IFDIR | 0o755
                    now = time.time()
                    if hasattr(os, 'getgid'):
                        gid = os.getgid()
                    else:
                        gid = 0

                    if hasattr(os, 'getuid'):
                        uid = os.getuid()
                    else:
                        uid = 0

                    return {
                        'st_atime': now, 'st_ctime': now, 'st_mtime': now,
                        'st_gid': gid,
                        'st_uid': uid,
                        'st_mode': mode, 'st_nlink': 2, 'st_size': 0
                    }
            except OSError as exc:
                error_no = exc.errno if getattr(exc, 'errno', None) else errno.EIO
                logger.error("getattr failed for path=%s: %s", path, exc)
                raise FuseOSError(error_no) from exc
            except Exception as exc:
                logger.exception("Unexpected getattr failure for path=%s", path)
                raise FuseOSError(errno.EIO) from exc

            logger.debug("getattr path=%s -> ENOENT", path)
            raise FuseOSError(errno.ENOENT)

        def readdir(self, path, fh):
            try:
                names = list_virtual_dir(path)
                dirents = ['.', '..']
                dirents.extend(sorted(names.keys()))
                logger.debug("readdir path=%s count=%d", path, len(dirents))
                return dirents
            except OSError as exc:
                error_no = exc.errno if getattr(exc, 'errno', None) else errno.EIO
                logger.error("readdir failed for path=%s: %s", path, exc)
                raise FuseOSError(error_no) from exc
            except Exception as exc:
                logger.exception("Unexpected readdir failure for path=%s", path)
                raise FuseOSError(errno.EIO) from exc

        def open(self, path, flags):
            is_file, is_dir, physical_path = get_virtual_item_info(path)
            if not physical_path or not os.path.exists(physical_path):
                raise FuseOSError(errno.ENOENT)
            return os.open(physical_path, flags)

        def create(self, path, mode, fi=None):
            rel = path.lstrip('/')
            if not rel:
                raise FuseOSError(errno.EINVAL)
            with _file_operation_lock:
                physical_path = os.path.join(self.upload_src_path, rel)
                os.makedirs(os.path.dirname(physical_path), exist_ok=True)
                _invalidate_vfs_caches()
                return os.open(physical_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)

        def read(self, path, length, offset, fh):
            os.lseek(fh, offset, os.SEEK_SET)
            return os.read(fh, length)

        def write(self, path, buf, offset, fh):
            os.lseek(fh, offset, os.SEEK_SET)
            return os.write(fh, buf)

        def truncate(self, path, length, fh=None):
            is_file, is_dir, physical_path = get_virtual_item_info(path)
            if physical_path:
                with _file_operation_lock:
                    with open(physical_path, 'r+b') as f:
                        f.truncate(length)
                    _invalidate_vfs_caches()

        def flush(self, path, fh):
            return os.fsync(fh)

        def release(self, path, fh):
            return os.close(fh)

        def unlink(self, path):
            physical_path = get_physical_path_for_virtual(path)
            if physical_path and os.path.exists(physical_path):
                with _file_operation_lock:
                    os.remove(physical_path)
                    _invalidate_vfs_caches()
            else:
                raise FuseOSError(errno.ENOENT)

        def mkdir(self, path, mode):
            physical_path = self._upload_physical_path(path)
            with _file_operation_lock:
                os.makedirs(physical_path, exist_ok=True)
                _invalidate_vfs_caches()

        def rmdir(self, path):
            is_file, is_dir, physical_path = get_virtual_item_info(path)
            if not is_dir:
                raise FuseOSError(errno.ENOENT)
            if physical_path and os.path.isdir(physical_path):
                try:
                    with _file_operation_lock:
                        os.rmdir(physical_path)
                        _invalidate_vfs_caches()
                    return
                except OSError as exc:
                    raise FuseOSError(exc.errno) from exc
            rel = path.lstrip('/')
            for base in get_vfs_base_paths():
                candidate = os.path.join(base, rel)
                if os.path.isdir(candidate):
                    try:
                        with _file_operation_lock:
                            os.rmdir(candidate)
                            _invalidate_vfs_caches()
                        return
                    except OSError as exc:
                        raise FuseOSError(exc.errno) from exc
            raise FuseOSError(errno.ENOENT)

        def rename(self, old, new):
            is_file, is_dir, old_physical = get_virtual_item_info(old)
            if not old_physical or not os.path.exists(old_physical):
                raise FuseOSError(errno.ENOENT)
            with _file_operation_lock:
                new_physical = self._upload_physical_path(new)
                os.makedirs(os.path.dirname(new_physical), exist_ok=True)
                os.rename(old_physical, new_physical)
                _invalidate_vfs_caches()

        def statfs(self, path):
            block_size = 4096
            total_blocks = 0
            free_blocks = 0
            for base in get_vfs_base_paths():
                try:
                    if hasattr(os, 'statvfs'):
                        st = os.statvfs(base)
                        total_blocks += st.f_blocks
                        free_blocks += st.f_bavail
                    else:
                        usage = shutil.disk_usage(base)
                        total_blocks += usage.total // block_size
                        free_blocks += usage.free // block_size
                except OSError:
                    pass
            if total_blocks == 0:
                total_blocks = (100 * 1024 ** 3) // block_size
                free_blocks = (10 * 1024 ** 3) // block_size
            return {
                'f_bsize': block_size, 'f_frsize': block_size,
                'f_blocks': total_blocks, 'f_bfree': free_blocks, 'f_bavail': free_blocks,
                'f_files': 1000000, 'f_ffree': 500000, 'f_favail': 500000,
                'f_flag': 0, 'f_namemax': 255,
            }

    return VirtualFUSE


def start_fuse_server_thread(fuse_config, upload_src_path, webhook_url):
    if not fuse_config.get('enabled', False):
        return {'enabled': False, 'failed': False, 'error': ''}
    if FUSE is None:
        print_and_discord("FUSE support is disabled because 'fusepy' is not installed or libfuse is missing.", webhook_url)
        return {'enabled': True, 'failed': True, 'error': "FUSE library not available"}

    mount_point = fuse_config.get('mount_point')
    if not mount_point:
        print_and_discord("FUSE mount point not configured.", webhook_url)
        return {'enabled': True, 'failed': True, 'error': "FUSE mount point not configured"}

    os.makedirs(mount_point, exist_ok=True)
    try:
        os.chmod(mount_point, 0o755)
    except Exception:
        pass

    _ensure_fuse_user_allow_other(webhook_url)
    register_fuse_cleanup_handlers(mount_point, webhook_url, True)
    fuse_status = {'enabled': True, 'failed': False, 'error': ''}

    def run_fuse():
        try:
            print_and_discord(f"Starting FUSE mount at {mount_point}", webhook_url)
            cls = create_virtual_fuse_class()
            FUSE(
                cls(upload_src_path),
                mount_point,
                nothreads=True,
                foreground=True,
                allow_other=True,
                default_permissions=True,
            )
        except Exception as e:
            fuse_status['failed'] = True
            fuse_status['error'] = str(e)
            msg = str(e)
            if "allow_other" in msg or "user_allow_other" in msg:
                print_and_discord("FUSE hint: enable 'user_allow_other' in /etc/fuse.conf (nodig voor zichtbaarheid in de GUI/non-root).", webhook_url)
            print_and_discord(f"FUSE mount failed: {e}", webhook_url)

    threading.Thread(target=run_fuse, daemon=True).start()
    return fuse_status


_fuse_cleanup_lock = threading.Lock()
_fuse_cleanup_done = False
_fuse_cleanup_mount_point = None
_fuse_cleanup_webhook_url = ''
_fuse_cleanup_remove_dir_if_empty = False
_fuse_cleanup_handlers_registered = False


def _run_command_quiet(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def _attempt_unmount_fuse(mount_point):
    _ensure_linux()
    commands = [
        ['fusermount', '-u', mount_point],
        ['fusermount3', '-u', mount_point],
        ['umount', mount_point],
    ]

    for command in commands:
        executable = command[0]
        if not os.path.isabs(executable) and shutil.which(executable) is None:
            continue
        if _run_command_quiet(command):
            return True
    return False


def cleanup_fuse_mount(force=False):
    global _fuse_cleanup_done
    with _fuse_cleanup_lock:
        if _fuse_cleanup_done and not force:
            return
        mount_point = _fuse_cleanup_mount_point
        webhook_url = _fuse_cleanup_webhook_url
        remove_dir_if_empty = _fuse_cleanup_remove_dir_if_empty
        if not mount_point:
            _fuse_cleanup_done = True
            return

        try:
            _attempt_unmount_fuse(mount_point)
            time.sleep(0.5)
            if os.path.exists(mount_point) and not os.path.ismount(mount_point) and remove_dir_if_empty:
                try:
                    os.rmdir(mount_point)
                    print_and_discord(f"FUSE mount directory removed: {mount_point}", webhook_url)
                except OSError:
                    pass
        except Exception as e:
            print_and_discord(f"FUSE cleanup warning: {e}", webhook_url)
        finally:
            _fuse_cleanup_done = True


def register_fuse_cleanup_handlers(mount_point, webhook_url, remove_dir_if_empty):
    global _fuse_cleanup_mount_point, _fuse_cleanup_webhook_url
    global _fuse_cleanup_remove_dir_if_empty, _fuse_cleanup_handlers_registered
    global _fuse_cleanup_done
    _fuse_cleanup_mount_point = mount_point
    _fuse_cleanup_webhook_url = webhook_url
    _fuse_cleanup_remove_dir_if_empty = remove_dir_if_empty
    _fuse_cleanup_done = False
    if _fuse_cleanup_handlers_registered:
        return

    _signal_handler_called = [False]

    def _cleanup_signal_handler(signum, frame):
        if _signal_handler_called[0]:
            return
        _signal_handler_called[0] = True
        for _sn in ('SIGINT', 'SIGTERM'):
            _s = getattr(signal, _sn, None)
            if _s is not None:
                try:
                    signal.signal(_s, signal.SIG_DFL)
                except Exception:
                    pass
        cleanup_fuse_mount()
        _stop_all_managed_containers()
        os._exit(0)

    atexit.register(cleanup_fuse_mount)
    atexit.register(_stop_all_managed_containers)
    for signal_name in ('SIGINT', 'SIGTERM'):
        sig = getattr(signal, signal_name, None)
        if sig is not None:
            signal.signal(sig, _cleanup_signal_handler)
    _fuse_cleanup_handlers_registered = True

def get_last_modified_time(path):
    last_modified_timestamp = os.path.getmtime(path)
    last_modified_date = datetime.fromtimestamp(last_modified_timestamp)
    return last_modified_date

def get_file_size(path):
    return os.path.getsize(path)

def has_sufficient_free_space(disk, required_gb):
    try:
        _total, _used, free = shutil.disk_usage(disk)
    except OSError:
        return False
    free_gb = free / (2**30)
    return free_gb >= float(required_gb or 0)

def save_config_if_missing(config_data, config_path=config_path):
    if os.path.exists(config_path):
        return

    src = config_data.get('src', '')
    webhook_url = config_data.get('webhook_url', '')
    disks = config_data.get('disks', [])
    last_disk = config_data.get('last_disk', '')
    settings = config_data.get('settings', {})
    space_hunter_disks = config_data.get('space_hunter_disks', [])
    reverse_raid_config = config_data.get('reverse_raid')
    if not isinstance(reverse_raid_config, dict):
        reverse_raid_config = {}

    webdav_server_config = config_data.get('webdav_server')
    if not isinstance(webdav_server_config, dict):
        webdav_server_config = {}

    sftp_server_config = config_data.get('sftp_server')
    if not isinstance(sftp_server_config, dict):
        sftp_server_config = {}

    nfs_server_config = config_data.get('nfs_server')
    if not isinstance(nfs_server_config, dict):
        nfs_server_config = {}

    fuse_server_config = config_data.get('fuse_server')
    if not isinstance(fuse_server_config, dict):
        fuse_server_config = {}

    webpanel_config = config_data.get('webpanel')
    if not isinstance(webpanel_config, dict):
        webpanel_config = {}

    filebrowser_config = config_data.get('filebrowser')
    if not isinstance(filebrowser_config, dict):
        filebrowser_config = {}

    min_file_age_hours = settings.get('min_file_age_hours', 4)
    extra_safety_space_gb = settings.get('extra_safety_space_gb', 5)
    scan_interval_seconds = settings.get('scan_interval_seconds', 120)
    console_clear_interval_hours = settings.get('console_clear_interval_hours', 6)
    space_check_default_min_free_gb = settings.get('space_check_default_min_free_gb', 40)
    space_hunter_min_file_age_hours = settings.get('space_hunter_min_file_age_hours', min_file_age_hours)
    space_hunter_exclude_folders = settings.get('space_hunter_exclude_folders', [])
    space_hunter_dry_run = bool(settings.get('space_hunter_dry_run', False))
    space_hunter_max_actions_per_cycle = _normalize_positive_int(settings.get('space_hunter_max_actions_per_cycle'))
    space_hunter_global_fallback = bool(settings.get('space_hunter_global_fallback', False))
    if not isinstance(space_hunter_exclude_folders, list):
        space_hunter_exclude_folders = []

    webdav_enabled = webdav_server_config.get('enabled', False)
    webdav_host = webdav_server_config.get('host', '0.0.0.0')
    webdav_port = webdav_server_config.get('port', 8080)
    webdav_username = webdav_server_config.get('username', 'admin')
    webdav_password = webdav_server_config.get('password', 'admin')
    webdav_upload_src = webdav_server_config.get('upload_src', src)
    webdav_use_fuse = webdav_server_config.get('use_fuse_mount_as_root', True)

    sftp_enabled = sftp_server_config.get('enabled', False)
    sftp_host = sftp_server_config.get('host', '0.0.0.0')
    sftp_port = sftp_server_config.get('port', 8081)
    sftp_username = sftp_server_config.get('username', 'raiduser')
    sftp_password = sftp_server_config.get('password', 'changeme')
    sftp_upload_src = sftp_server_config.get('upload_src', src)
    sftp_use_fuse = sftp_server_config.get('use_fuse_mount_as_root', True)

    nfs_enabled = nfs_server_config.get('enabled', False)
    nfs_host = nfs_server_config.get('host', '0.0.0.0')
    nfs_port = nfs_server_config.get('port', 2049)
    nfs_permitted = nfs_server_config.get('permitted', '*')
    nfs_upload_src = nfs_server_config.get('upload_src', src)
    nfs_use_fuse = nfs_server_config.get('use_fuse_mount_as_root', True)

    fuse_enabled = fuse_server_config.get('enabled', False)
    fuse_mount_point = fuse_server_config.get('mount_point', '')
    fuse_upload_src = fuse_server_config.get('upload_src', src)

    webpanel_enabled = _coerce_bool(webpanel_config.get('enabled', True), True)
    webpanel_host = str(webpanel_config.get('host', '0.0.0.0'))
    webpanel_port = _coerce_int(webpanel_config.get('port', 5000), default=5000, min_value=1, max_value=65535)

    filebrowser_enabled = _coerce_bool(filebrowser_config.get('enabled', True), True)
    filebrowser_port = _coerce_int(filebrowser_config.get('port', 8082), default=8082, min_value=1, max_value=65535)
    filebrowser_state_dir = str(filebrowser_config.get('state_dir') or "")
    if not filebrowser_state_dir:
        if has_admin_privileges():
            filebrowser_state_dir = "/var/lib/multidisk-filebalancer/filebrowser"
        else:
            filebrowser_state_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "multidisk-filebalancer", "filebrowser")
    filebrowser_username = str(filebrowser_config.get('username') or "admin")
    filebrowser_password = str(filebrowser_config.get('password') or "changeme123456")
    filebrowser_credentials_initialized = _coerce_bool(filebrowser_config.get('credentials_initialized', False), False)

    reverse_enabled = reverse_raid_config.get('enabled', False)
    reverse_source_paths = reverse_raid_config.get('source_paths', [])
    reverse_destination_path = reverse_raid_config.get('destination_path', src)
    reverse_min_age_hours = reverse_raid_config.get('min_file_age_hours', 12)
    reverse_interval_minutes = reverse_raid_config.get('run_interval_minutes', 10)

    def _bool_to_yaml(value):
        if value:
            return "true"
        return "false"

    disk_lines = []
    for disk in disks:
        name = disk.get('name', '')
        path = disk.get('path', '')
        disk_lines.append(f"  - name: {name}\n    path: {path}")
    if not disk_lines:
        disk_lines.append("  # add your disks here")

    space_hunter_lines = []
    if space_hunter_disks:
        for disk in space_hunter_disks:
            action = disk.get('action', 'delete')
            min_free_gb = disk.get('min_free_gb', space_check_default_min_free_gb)
            path = disk.get('path', '')
            move_destination = disk.get('move_destination')
            if move_destination:
                move_value = move_destination
            else:
                move_value = "null"
            space_hunter_lines.append(
                f"  - action: {action}\n"
                f"    min_free_gb: {min_free_gb}\n"
                f"    path: {path}\n"
                f"    move_destination: {move_value}"
            )
    else:
        space_hunter_lines.append("  # no automatic cleanup configured")

    reverse_source_lines = []
    if reverse_source_paths:
        for path in reverse_source_paths:
            reverse_source_lines.append(f"    - {path}")
    else:
        for disk in disks:
            path = disk.get('path', '')
            if path:
                reverse_source_lines.append(f"    - {path}")

    lines = []
    lines.append("# VulcanoCraft MultiDisk FileBalancer config")
    lines.append("# generated on first run; adjust the values to your environment.")
    lines.append("")
    lines.append(f"src: {src}")
    lines.append(f"webhook_url: '{webhook_url}'")
    lines.append("")
    lines.append("disks:")
    lines.extend(disk_lines)
    lines.append("")
    lines.append(f"last_disk: {last_disk}")
    lines.append("")
    lines.append("settings:")
    lines.append(f"  min_file_age_hours: {min_file_age_hours}")
    lines.append(f"  extra_safety_space_gb: {extra_safety_space_gb}")
    lines.append(f"  scan_interval_seconds: {scan_interval_seconds}")
    lines.append(f"  console_clear_interval_hours: {console_clear_interval_hours}")
    lines.append(f"  space_check_default_min_free_gb: {space_check_default_min_free_gb}")
    lines.append(f"  space_hunter_min_file_age_hours: {min_file_age_hours}")
    lines.append("  space_hunter_exclude_folders: []")
    lines.append(f"  space_hunter_dry_run: {_bool_to_yaml(space_hunter_dry_run)}")
    lines.append(f"  space_hunter_max_actions_per_cycle: {space_hunter_max_actions_per_cycle or 0}")
    lines.append(f"  space_hunter_global_fallback: {_bool_to_yaml(space_hunter_global_fallback)}")
    lines.append("")
    lines.append("space_hunter_disks:")
    lines.extend(space_hunter_lines)
    lines.append("")
    lines.append("reverse_raid:")
    lines.append(f"  enabled: {_bool_to_yaml(reverse_enabled)}")
    lines.append("  source_paths:")
    lines.extend(reverse_source_lines or ["    # no source folders configured"])
    lines.append(f"  destination_path: {reverse_destination_path}")
    lines.append(f"  min_file_age_hours: {reverse_min_age_hours}")
    lines.append(f"  run_interval_minutes: {reverse_interval_minutes}")
    lines.append("")
    lines.append("webdav_server:")
    lines.append(f"  enabled: {_bool_to_yaml(webdav_enabled)}")
    lines.append(f"  host: {webdav_host}")
    lines.append(f"  port: {webdav_port}")
    lines.append(f"  username: '{webdav_username}'")
    lines.append(f"  password: '{webdav_password}'")
    lines.append(f"  upload_src: {webdav_upload_src}")
    lines.append(f"  use_fuse_mount_as_root: {_bool_to_yaml(webdav_use_fuse)}")
    lines.append("")
    lines.append("sftp_server:")
    lines.append(f"  enabled: {_bool_to_yaml(sftp_enabled)}")
    lines.append(f"  host: {sftp_host}")
    lines.append(f"  port: {sftp_port}")
    lines.append(f"  username: '{sftp_username}'")
    lines.append(f"  password: '{sftp_password}'")
    lines.append(f"  upload_src: {sftp_upload_src}")
    lines.append(f"  use_fuse_mount_as_root: {_bool_to_yaml(sftp_use_fuse)}")
    lines.append("")
    lines.append("nfs_server:")
    lines.append(f"  enabled: {_bool_to_yaml(nfs_enabled)}")
    lines.append(f"  host: {nfs_host}")
    lines.append(f"  port: {nfs_port}")
    lines.append(f"  permitted: '{nfs_permitted}'")
    lines.append(f"  upload_src: {nfs_upload_src}")
    lines.append(f"  use_fuse_mount_as_root: {_bool_to_yaml(nfs_use_fuse)}")
    lines.append("")
    lines.append("fuse_server:")
    lines.append(f"  enabled: {_bool_to_yaml(fuse_enabled)}")
    lines.append(f"  mount_point: {fuse_mount_point}")
    lines.append(f"  upload_src: {fuse_upload_src}")
    lines.append("")
    lines.append("filebrowser:")
    lines.append(f"  enabled: {_bool_to_yaml(filebrowser_enabled)}")
    lines.append(f"  port: {filebrowser_port}")
    lines.append(f"  state_dir: {filebrowser_state_dir}")
    lines.append(f"  username: {filebrowser_username}")
    lines.append(f"  password: '{filebrowser_password}'")
    lines.append(f"  credentials_initialized: {_bool_to_yaml(filebrowser_credentials_initialized)}")
    lines.append("")
    lines.append("webpanel:")
    lines.append(f"  enabled: {_bool_to_yaml(webpanel_enabled)}")
    lines.append(f"  host: {webpanel_host}")
    lines.append(f"  port: {webpanel_port}")

    with open(config_path, 'w', encoding='utf-8') as config_file:
        config_file.write("\n".join(lines) + "\n")

def read_config(config_path=config_path):
    if os.path.exists(config_path):
        with open(config_path, 'r') as yaml_file:
            config_data = yaml.safe_load(yaml_file)
            if isinstance(config_data, dict) and 's3_server' in config_data:
                config_data.pop('s3_server', None)
            print(f"Config loaded from: {os.path.abspath(config_path)}")
            print(f"Config data: {config_data}")
            return config_data
    return None


def _load_config_from_disk():
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, 'r', encoding='utf-8') as yaml_file:
            cfg = yaml.safe_load(yaml_file)
    except Exception:
        return {}
    if not isinstance(cfg, dict):
        return {}
    if 's3_server' in cfg:
        cfg.pop('s3_server', None)
    return cfg


def _save_config_to_disk(cfg):
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)


def _coerce_int(value, default=None, min_value=None, max_value=None):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    if min_value is not None and n < min_value:
        return default
    if max_value is not None and n > max_value:
        return default
    return n


def _coerce_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "yes", "1", "on"):
            return True
        if v in ("false", "no", "0", "off"):
            return False
    return default


def _normalize_backup_strategy(value, default="round_robin"):
    v = str(value or "").strip().lower()
    allowed = {"round_robin", "most_free_space", "least_used_pct", "path_hash"}
    if v in allowed:
        return v
    return default


def _normalize_raid_simulation(value, default="none"):
    v = str(value or "").strip().lower()
    alias = {
        "none": "raid0",
        "raid0": "raid0",
        "raid_0": "raid0",
        "mirror_2": "raid1",
        "raid1": "raid1",
        "raid_1": "raid1",
        "mirror_all": "raid1_all",
        "raid5": "raid5",
        "raid_5": "raid5",
        "raid6": "raid6",
        "raid_6": "raid6",
        "raid10": "raid10",
        "raid_10": "raid10",
    }
    mapped = alias.get(v)
    if mapped:
        return mapped
    default_norm = alias.get(str(default or "").strip().lower())
    return default_norm or "raid0"


def _normalize_disks(disks):
    if not isinstance(disks, list):
        return []
    normalized = []
    for disk in disks:
        if not isinstance(disk, dict):
            continue
        name = disk.get('name') or disk.get('naam') or ""
        path = disk.get('path') or disk.get('pad') or ""
        entry = dict(disk)
        entry['name'] = str(name)
        entry['naam'] = str(name)
        entry['path'] = str(path)
        entry['pad'] = str(path)
        normalized.append(entry)
    return normalized


def _normalize_config_for_runtime(cfg):
    if not isinstance(cfg, dict):
        cfg = {}
    out = dict(cfg)
    settings = out.get('settings')
    if not isinstance(settings, dict):
        settings = {}
    normalized_settings = dict(settings)
    normalized_settings['backup_strategy'] = _normalize_backup_strategy(normalized_settings.get('backup_strategy'))
    normalized_settings['raid_simulation'] = _normalize_raid_simulation(normalized_settings.get('raid_simulation'))
    out['settings'] = normalized_settings

    src_folders = out.get('src_folders')
    if isinstance(src_folders, list):
        out['src_folders'] = [str(p) for p in src_folders if p]
    else:
        out.pop('src_folders', None)

    out['disks'] = _normalize_disks(out.get('disks', []))
    space_hunter_disks = out.get('space_hunter_disks', [])
    if isinstance(space_hunter_disks, list):
        sh = []
        for disk in space_hunter_disks:
            if not isinstance(disk, dict):
                continue
            path = disk.get('path') or disk.get('pad') or ""
            min_free_gb = disk.get('min_free_gb')
            entry = dict(disk)
            entry['path'] = str(path)
            entry['pad'] = str(path)
            if min_free_gb is not None:
                entry['min_free_gb'] = _coerce_int(min_free_gb, default=None, min_value=0)
            sh.append(entry)
        out['space_hunter_disks'] = sh
    else:
        out['space_hunter_disks'] = []

    webpanel = out.get('webpanel')
    if not isinstance(webpanel, dict):
        webpanel = {}
    out['webpanel'] = {
        'enabled': _coerce_bool(webpanel.get('enabled', True), True),
        'host': str(webpanel.get('host', '127.0.0.1')),
        'port': _coerce_int(webpanel.get('port', 5000), default=5000, min_value=1, max_value=65535),
    }

    filebrowser = out.get('filebrowser')
    if not isinstance(filebrowser, dict):
        filebrowser = {}
    out['filebrowser'] = {
        'enabled': _coerce_bool(filebrowser.get('enabled', True), True),
        'port': _coerce_int(filebrowser.get('port', 8082), default=8082, min_value=1, max_value=65535),
        'container_name': str(filebrowser.get('container_name', 'filebrowser')),
        'image': str(filebrowser.get('image', 'filebrowser/filebrowser')),
        'restart_policy': str(filebrowser.get('restart_policy', 'unless-stopped')),
        'state_dir': str(filebrowser.get('state_dir') or ""),
        'username': str(filebrowser.get('username') or "admin"),
        'password': str(filebrowser.get('password') or ""),
        'credentials_initialized': _coerce_bool(filebrowser.get('credentials_initialized', False), False),
    }
    return out


def _validate_config_for_save(cfg):
    cfg = _normalize_config_for_runtime(cfg)
    disks = cfg.get('disks', [])
    if not isinstance(disks, list) or not disks:
        raise ValueError("disks is required and must contain at least 1 item")
    for disk in disks:
        name = str(disk.get('name') or "").strip()
        path = str(disk.get('path') or "").strip()
        if not name or not path:
            raise ValueError("Each disk must have a name and path")

    settings = cfg.get('settings', {})
    if not isinstance(settings, dict):
        settings = {}
    cfg['settings'] = settings
    settings['backup_strategy'] = _normalize_backup_strategy(settings.get('backup_strategy'))
    settings['raid_simulation'] = _normalize_raid_simulation(settings.get('raid_simulation'))
    settings['min_file_age_hours'] = _coerce_int(settings.get('min_file_age_hours', 1), default=1, min_value=0)
    settings['extra_safety_space_gb'] = _coerce_int(settings.get('extra_safety_space_gb', 0), default=0, min_value=0)
    settings['scan_interval_seconds'] = _coerce_int(settings.get('scan_interval_seconds', 120), default=120, min_value=1)
    settings['console_clear_interval_hours'] = _coerce_int(settings.get('console_clear_interval_hours', 6), default=6, min_value=0)
    settings['space_check_default_min_free_gb'] = _coerce_int(settings.get('space_check_default_min_free_gb', 3), default=3, min_value=0)
    settings['space_hunter_min_file_age_hours'] = _coerce_int(
        settings.get('space_hunter_min_file_age_hours', settings['min_file_age_hours']),
        default=settings['min_file_age_hours'],
        min_value=0,
    )
    settings['space_hunter_dry_run'] = _coerce_bool(settings.get('space_hunter_dry_run', False), False)
    max_actions = settings.get('space_hunter_max_actions_per_cycle', 0)
    settings['space_hunter_max_actions_per_cycle'] = _coerce_int(max_actions, default=0, min_value=0)

    src_folders = cfg.get('src_folders')
    if isinstance(src_folders, list) and src_folders:
        cfg['src'] = str(src_folders[0])
    cfg['src'] = str(cfg.get('src', ''))
    if not cfg['src']:
        raise ValueError("src (or src_folders[0]) is required")
    return cfg


def _stats_record_error(message):
    ts = time.time()
    with _stats_lock:
        _stats["errors_total"] += 1
        _stats["last_action"] = {
            "type": "error",
            "ts": ts,
            "message": str(message)[:500],
        }
        _stats["recent_actions"].append({
            "type": "error",
            "ts": ts,
            "message": str(message)[:500],
        })
        max_actions = int(_stats.get("max_recent_actions") or 80)
        if max_actions > 0 and len(_stats["recent_actions"]) > max_actions:
            _stats["recent_actions"] = _stats["recent_actions"][-max_actions:]


def _stats_record_move(source_path, destination_path, size_bytes, disk_name, mode):
    ts = time.time()
    try:
        size_int = int(size_bytes or 0)
    except Exception:
        size_int = 0
    src_name = os.path.basename(str(source_path or ""))[:120]
    dst_name = os.path.basename(str(destination_path or ""))[:120]
    with _stats_lock:
        _stats["files_moved_total"] += 1
        _stats["bytes_moved_total"] += max(0, size_int)
        _stats["last_action"] = {
            "type": "move",
            "ts": ts,
            "disk": str(disk_name or ""),
            "mode": str(mode or ""),
        }
        _stats["recent_actions"].append({
            "type": "move",
            "ts": ts,
            "disk": str(disk_name or ""),
            "mode": str(mode or ""),
            "bytes": max(0, size_int),
            "src": src_name,
            "dst": dst_name,
        })
        max_actions = int(_stats.get("max_recent_actions") or 80)
        if max_actions > 0 and len(_stats["recent_actions"]) > max_actions:
            _stats["recent_actions"] = _stats["recent_actions"][-max_actions:]
        _stats["moves_series"].append({
            "ts": ts,
            "files": 1,
            "bytes": max(0, size_int),
        })
        max_points = int(_stats.get("max_series_points") or 120)
        if max_points > 0 and len(_stats["moves_series"]) > max_points:
            _stats["moves_series"] = _stats["moves_series"][-max_points:]


def _stats_record_cleanup(action, size_bytes):
    ts = time.time()
    try:
        size_int = int(size_bytes or 0)
    except Exception:
        size_int = 0
    with _stats_lock:
        _stats["cleanup_actions_total"] += 1
        _stats["last_action"] = {
            "type": "cleanup",
            "ts": ts,
            "action": str(action or ""),
            "bytes": max(0, size_int),
        }
        _stats["recent_actions"].append({
            "type": "cleanup",
            "ts": ts,
            "action": str(action or ""),
            "bytes": max(0, size_int),
        })
        max_actions = int(_stats.get("max_recent_actions") or 80)
        if max_actions > 0 and len(_stats["recent_actions"]) > max_actions:
            _stats["recent_actions"] = _stats["recent_actions"][-max_actions:]


def _stats_cycle_begin():
    ts = time.time()
    with _stats_lock:
        _stats["cycle_start_ts"] = ts
        _stats["cycle_start_totals"] = {
            "files_moved_total": int(_stats.get("files_moved_total") or 0),
            "bytes_moved_total": int(_stats.get("bytes_moved_total") or 0),
            "cleanup_actions_total": int(_stats.get("cleanup_actions_total") or 0),
            "errors_total": int(_stats.get("errors_total") or 0),
        }


def _stats_cycle_end(scan_interval_seconds):
    ts = time.time()
    with _stats_lock:
        start_ts = _stats.get("cycle_start_ts")
        start_totals = _stats.get("cycle_start_totals") or {}
        if start_ts is None:
            start_ts = ts
        end_totals = {
            "files_moved_total": int(_stats.get("files_moved_total") or 0),
            "bytes_moved_total": int(_stats.get("bytes_moved_total") or 0),
            "cleanup_actions_total": int(_stats.get("cleanup_actions_total") or 0),
            "errors_total": int(_stats.get("errors_total") or 0),
        }
        _stats["cycle"] = {
            "last_start_ts": float(start_ts),
            "last_end_ts": float(ts),
            "last_duration_seconds": max(0, int(ts - start_ts)),
            "last_moved_files": max(0, end_totals["files_moved_total"] - int(start_totals.get("files_moved_total") or 0)),
            "last_moved_bytes": max(0, end_totals["bytes_moved_total"] - int(start_totals.get("bytes_moved_total") or 0)),
            "last_cleanup_actions": max(0, end_totals["cleanup_actions_total"] - int(start_totals.get("cleanup_actions_total") or 0)),
            "last_errors": max(0, end_totals["errors_total"] - int(start_totals.get("errors_total") or 0)),
            "next_run_ts": float(ts + max(0, int(scan_interval_seconds or 0))) if scan_interval_seconds is not None else None,
        }
        _stats["cycle_start_ts"] = None
        _stats["cycle_start_totals"] = None


def _stats_snapshot():
    now = time.time()
    with _stats_lock:
        start_ts = float(_stats.get("start_ts") or now)
        return {
            "uptime_seconds": max(0, int(now - start_ts)),
            "totals": {
                "files_moved_total": int(_stats.get("files_moved_total") or 0),
                "bytes_moved_total": int(_stats.get("bytes_moved_total") or 0),
                "cleanup_actions_total": int(_stats.get("cleanup_actions_total") or 0),
                "errors_total": int(_stats.get("errors_total") or 0),
            },
            "last_action": _stats.get("last_action"),
            "recent_actions": list(_stats.get("recent_actions") or []),
            "cycle": dict(_stats.get("cycle") or {}),
            "timeseries": {
                "moves": list(_stats.get("moves_series") or []),
            },
        }


def _compute_disk_usage(cfg):
    disks = cfg.get('disks', [])
    usage = []
    for disk in disks:
        name = disk.get('name') or disk.get('naam') or ""
        path = disk.get('path') or disk.get('pad') or ""
        if not path:
            continue
        try:
            total, used, free = shutil.disk_usage(path)
            used_pct = (used / total * 100.0) if total else 0.0
            usage.append({
                "name": str(name),
                "path": str(path),
                "total_bytes": int(total),
                "used_bytes": int(used),
                "free_bytes": int(free),
                "used_pct": float(used_pct),
            })
        except Exception as exc:
            usage.append({
                "name": str(name),
                "path": str(path),
                "error": str(exc),
            })
    return usage


def _build_insights(cfg, disks_usage, snapshot):
    insights = []
    disks_ok = [d for d in disks_usage if 'used_pct' in d]
    disks_err = [d for d in disks_usage if 'error' in d]
    if disks_err:
        insights.append({
            "title": "Disk paths not readable",
            "body": f"{len(disks_err)} disk(s) return an error on disk_usage (path does not exist or no permission).",
        })
    if disks_ok:
        worst = sorted(disks_ok, key=lambda d: d.get('used_pct', 0), reverse=True)[0]
        insights.append({
            "title": "Highest disk usage",
            "body": f"{worst.get('name') or worst.get('path')}: {worst.get('used_pct', 0):.1f}% used, {worst.get('free_bytes', 0) / (2**30):.2f} GB free.",
        })
    settings = cfg.get('settings', {})
    scan_interval = settings.get('scan_interval_seconds', 120)
    insights.append({
        "title": "Scan interval",
        "body": f"Scan interval is set to {scan_interval} seconds.",
    })
    totals = snapshot.get('totals', {})
    insights.append({
        "title": "Total moved",
        "body": f"{totals.get('files_moved_total', 0)} files, {totals.get('bytes_moved_total', 0) / (2**30):.2f} GB since start.",
    })
    return insights


def _create_webpanel_app():
    app = Flask(__name__)

    @app.get("/")
    def webpanel_root():
        return send_from_directory(current_dir, "webpanel.html")

    @app.get("/panel")
    def webpanel_page():
        return send_from_directory(current_dir, "webpanel.html")

    @app.get("/webpanel.css")
    def webpanel_css():
        return send_from_directory(current_dir, "webpanel.css")

    @app.get("/webpanel.js")
    def webpanel_js():
        return send_from_directory(current_dir, "webpanel.js")

    @app.get("/api/config")
    def api_get_config():
        cfg = _normalize_config_for_runtime(_load_config_from_disk())
        return jsonify({
            "config": cfg,
            "meta": {
                "config_path": os.path.abspath(config_path),
                "loaded_at": time.time(),
            },
        })

    @app.put("/api/config")
    def api_put_config():
        body = request.get_json(silent=True) or {}
        cfg = body.get("config")
        try:
            validated = _validate_config_for_save(cfg)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
        try:
            _save_config_to_disk(validated)
        except Exception as exc:
            _stats_record_error(exc)
            return jsonify({"error": f"Could not save config.yml: {exc}"}), 500
        return jsonify({
            "config": validated,
            "meta": {
                "config_path": os.path.abspath(config_path),
                "saved_at": time.time(),
                "note": "Restart required to apply everything.",
            },
        })

    @app.get("/api/stats")
    def api_stats():
        cfg = _normalize_config_for_runtime(_load_config_from_disk())
        snapshot = _stats_snapshot()
        disks_usage = _compute_disk_usage(cfg)
        insights = _build_insights(cfg, disks_usage, snapshot)
        services = {
            "webpanel": {
                "enabled": _coerce_bool((cfg.get("webpanel") or {}).get("enabled", True), True),
                "host": str((cfg.get("webpanel") or {}).get("host", "")),
                "port": _coerce_int((cfg.get("webpanel") or {}).get("port", 0), default=0, min_value=0, max_value=65535),
            },
            "filebrowser": {
                "enabled": _coerce_bool((cfg.get("filebrowser") or {}).get("enabled", False), False),
                "port": _coerce_int((cfg.get("filebrowser") or {}).get("port", 0), default=0, min_value=0, max_value=65535),
                "username": str((cfg.get("filebrowser") or {}).get("username", "")),
                "state_dir": str((cfg.get("filebrowser") or {}).get("state_dir", "")),
            },
            "webdav": {
                "enabled": _coerce_bool((cfg.get("webdav_server") or {}).get("enabled", False), False),
                "port": _coerce_int((cfg.get("webdav_server") or {}).get("port", 0), default=0, min_value=0, max_value=65535),
            },
            "sftp": {
                "enabled": _coerce_bool((cfg.get("sftp_server") or {}).get("enabled", False), False),
                "port": _coerce_int((cfg.get("sftp_server") or {}).get("port", 0), default=0, min_value=0, max_value=65535),
            },
            "nfs": {
                "enabled": _coerce_bool((cfg.get("nfs_server") or {}).get("enabled", False), False),
            },
            "fuse": {
                "enabled": _coerce_bool((cfg.get("fuse_server") or {}).get("enabled", False), False),
                "mount_point": str((cfg.get("fuse_server") or {}).get("mount_point", "")),
            },
            "reverse_raid": {
                "enabled": _coerce_bool((cfg.get("reverse_raid") or {}).get("enabled", False), False),
                "run_interval_minutes": _coerce_int((cfg.get("reverse_raid") or {}).get("run_interval_minutes", 0), default=0, min_value=0),
            },
        }
        src_folders = cfg.get("src_folders") or ([cfg.get("src")] if cfg.get("src") else [])
        config_summary = {
            "src_folders_count": len([p for p in src_folders if p]),
            "disks_count": len(cfg.get("disks") or []),
            "space_hunter_disks_count": len(cfg.get("space_hunter_disks") or []),
        }
        return jsonify({
            "uptime_seconds": snapshot.get("uptime_seconds", 0),
            "meta": {
                "config_path": os.path.abspath(config_path),
            },
            "totals": snapshot.get("totals", {}),
            "last_action": snapshot.get("last_action"),
            "recent_actions": snapshot.get("recent_actions", []),
            "cycle": snapshot.get("cycle", {}),
            "services": services,
            "config_summary": config_summary,
            "timeseries": snapshot.get("timeseries", {}),
            "disks_usage": disks_usage,
            "insights": insights,
        })

    return app


def _silence_flask_webserver_output():
    try:
        import flask.cli as flask_cli
        try:
            flask_cli.show_server_banner = lambda *args, **kwargs: None
        except Exception:
            pass
    except Exception:
        pass
    try:
        werkzeug_logger = logging.getLogger("werkzeug")
        werkzeug_logger.setLevel(logging.ERROR)
        werkzeug_logger.propagate = False
    except Exception:
        pass


def start_webpanel_thread(cfg, webhook_url):
    global _webpanel_thread, _webpanel_app
    if _webpanel_thread and _webpanel_thread.is_alive():
        return _webpanel_thread

    cfg = _normalize_config_for_runtime(cfg)
    webpanel = cfg.get('webpanel', {})
    enabled = _coerce_bool(webpanel.get('enabled', True), True)
    if not enabled:
        return None
    host = str(webpanel.get('host', '0.0.0.0'))
    port = _coerce_int(webpanel.get('port', 5000), default=5000, min_value=1, max_value=65535)

    app = _create_webpanel_app()
    _webpanel_app = app

    def _run():
        try:
            _silence_flask_webserver_output()
            try:
                app.logger.disabled = True
            except Exception:
                pass
            print_and_discord(f"Webserver started on {host}:{port}", webhook_url)
            app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
        except Exception as exc:
            _stats_record_error(exc)
            print_and_discord(f"Webpanel error: {exc}", webhook_url)

    t = threading.Thread(target=_run, daemon=True, name="webpanel")
    t.start()
    _webpanel_thread = t
    return t

def send_discord_message(message, webhook_url):
    if not webhook_url:
        return
    try:
        data = {
            "content": message
        }
        requests.post(webhook_url, json=data)
    except Exception as e:
        print(f"Error sending Discord message: {e}")

def print_and_discord(message, webhook_url):
    print(message)
    sys.stdout.flush()
    send_discord_message(message, webhook_url)


def _normalize_positive_int(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number > 0:
        return number
    return None


def _cleanup_log(level, webhook_url, message):
    # Keep output structured so logs are easier to filter in large cleanup runs.
    if level:
        level_name = str(level).upper()
    else:
        level_name = "INFO"
    print_and_discord(f"[SPACE_HUNTER][{level_name}] {message}", webhook_url)

def _is_probably_removable_mount_path(path):
    p = str(path or "")
    return p.startswith("/media/") or p.startswith("/run/media/")


def _disk_path_ready(path):
    p = str(path or "").strip()
    if not p:
        return False, "missing path"
    if not os.path.isdir(p):
        return False, "path does not exist or is not a directory"
    try:
        root_dev = os.stat("/").st_dev
        path_dev = os.stat(p).st_dev
        if _is_probably_removable_mount_path(p) and path_dev == root_dev:
            return False, "path is on root filesystem (disk likely not mounted)"
    except OSError:
        return False, "cannot stat path"
    try:
        shutil.disk_usage(p)
    except OSError as exc:
        return False, f"disk usage failed: {exc}"
    return True, ""


def _filter_available_disks(disks, webhook_url, state_by_key, key_fn, label):
    available = []
    for disk in disks:
        key = key_fn(disk)
        path = None
        if isinstance(disk, dict):
            path = disk.get("path") or disk.get("pad")
        ready, reason = _disk_path_ready(path)
        prev = state_by_key.get(key)
        if prev is None:
            state_by_key[key] = ready
        elif prev != ready:
            state_by_key[key] = ready
            if ready:
                print_and_discord(f"{label} available again: {key} -> {path}", webhook_url)
            else:
                extra = f" ({reason})" if reason else ""
                print_and_discord(f"{label} unavailable: {key} -> {path}{extra}", webhook_url)
        if ready:
            available.append(disk)
    return available


def _parse_lsblk_key_values(output):
    result = {}
    for line in (output or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            result[k] = v
    return result


def _get_block_device_info(device_node):
    if not shutil.which("lsblk"):
        _ensure_binary_available("lsblk", [["util-linux"]], "")
    if not shutil.which("lsblk"):
        return {"FSTYPE": "", "MOUNTPOINT": "", "UUID": "", "LABEL": ""}
    rc, out = _run_capture(["lsblk", "-P", "-o", "FSTYPE,MOUNTPOINT,UUID,LABEL", "-f", device_node], timeout=10)
    if rc != 0 or not out:
        return {"FSTYPE": "", "MOUNTPOINT": "", "UUID": "", "LABEL": ""}
    return _parse_lsblk_key_values(out)


def _is_device_mounted(device_node):
    info = _get_block_device_info(device_node)
    mp = str(info.get("MOUNTPOINT") or "").strip()
    if mp:
        return True, mp
    return False, ""


def _repair_device_if_needed(device_node, fstype, webhook_url):
    fs = str(fstype or "").strip().lower()
    if not fs:
        return True

    cmd = None
    timeout = 120
    if fs in ("ntfs",):
        cmd = ["ntfsfix", device_node]
        timeout = 180
    elif fs in ("exfat",):
        cmd = ["fsck.exfat", "-a", device_node]
    elif fs in ("vfat", "fat", "fat32", "msdos"):
        cmd = ["fsck.vfat", "-a", device_node]
    elif fs in ("ext4",):
        cmd = ["e2fsck", "-p", device_node]
        timeout = 300
    else:
        return True

    if not shutil.which(cmd[0]):
        pkg_options = []
        if cmd[0] == "ntfsfix":
            pkg_options = [["ntfs-3g"]]
        elif cmd[0] == "fsck.exfat":
            pkg_options = [["exfatprogs"], ["exfat-utils"]]
        elif cmd[0] == "fsck.vfat":
            pkg_options = [["dosfstools"]]
        elif cmd[0] == "e2fsck":
            pkg_options = [["e2fsprogs"]]
        ok = _ensure_binary_available(cmd[0], pkg_options, webhook_url)
        if not ok:
            print_and_discord(f"[AUTOMOUNT] Repair tool ontbreekt ({cmd[0]}). Installatie faalde. Skip repair voor {device_node} (fstype={fs}).", webhook_url)
            return False

    print_and_discord(f"[AUTOMOUNT] Repair start: {' '.join(cmd)}", webhook_url)
    try:
        rc, out = _run_capture(_sudo_prefix() + cmd, timeout=timeout)
    except subprocess.TimeoutExpired:
        print_and_discord(f"[AUTOMOUNT] Repair timeout ({timeout}s) voor {device_node} (fstype={fs}).", webhook_url)
        return False
    except Exception as exc:
        print_and_discord(f"[AUTOMOUNT] Repair error for {device_node}: {exc}", webhook_url)
        return False

    if rc != 0:
        print_and_discord(f"[AUTOMOUNT] Repair failed for {device_node} (exit {rc}):\n{out}", webhook_url)
        return False

    if out:
        print_and_discord(f"[AUTOMOUNT] Repair output for {device_node}:\n{out}", webhook_url)
    return True


def _mount_device(device_node, webhook_url):
    if not shutil.which("udisksctl"):
        _ensure_binary_available("udisksctl", [["udisks2"]], webhook_url)
    if not shutil.which("udisksctl"):
        print_and_discord("[AUTOMOUNT] udisksctl is missing. Installation failed. Cannot automount.", webhook_url)
        return False, ""

    mounted, mp = _is_device_mounted(device_node)
    if mounted:
        return True, mp

    print_and_discord(f"[AUTOMOUNT] Mount start: udisksctl mount -b {device_node}", webhook_url)
    try:
        rc, out = _run_capture(_sudo_prefix() + ["udisksctl", "mount", "-b", device_node], timeout=30)
    except subprocess.TimeoutExpired:
        print_and_discord(f"[AUTOMOUNT] Mount timeout for {device_node}.", webhook_url)
        return False, ""
    except Exception as exc:
        print_and_discord(f"[AUTOMOUNT] Mount error for {device_node}: {exc}", webhook_url)
        return False, ""

    if rc != 0:
        mounted_after, mp_after = _is_device_mounted(device_node)
        if mounted_after:
            return True, mp_after
        print_and_discord(f"[AUTOMOUNT] Mount failed for {device_node} (exit {rc}):\n{out}", webhook_url)
        return False, ""

    mounted_after, mp_after = _is_device_mounted(device_node)
    if mounted_after:
        if out:
            print_and_discord(f"[AUTOMOUNT] Mount output:\n{out}", webhook_url)
        return True, mp_after
    return True, ""


def _automount_handle_device(device_node, webhook_url):
    if not device_node or not device_node.startswith("/dev/"):
        return

    mounted, mp = _is_device_mounted(device_node)
    if mounted:
        print_and_discord(f"[AUTOMOUNT] Already mounted: {device_node} -> {mp}", webhook_url)
        return

    info = _get_block_device_info(device_node)
    fs = str(info.get("FSTYPE") or "").strip()
    if not fs:
        return

    ok_repair = _repair_device_if_needed(device_node, fs, webhook_url)
    if not ok_repair:
        return

    ok_mount, mp2 = _mount_device(device_node, webhook_url)
    if ok_mount:
        if mp2:
            print_and_discord(f"[AUTOMOUNT] Mount OK: {device_node} -> {mp2}", webhook_url)
        else:
            print_and_discord(f"[AUTOMOUNT] Mount OK: {device_node}", webhook_url)


def start_automount_thread(webhook_url):
    global _automount_thread
    if _automount_thread and _automount_thread.is_alive():
        return _automount_thread

    def _run():
        try:
            import pyudev
        except Exception as exc:
            print_and_discord(f"[AUTOMOUNT] pyudev not available: {exc}", webhook_url)
            return

        if not shutil.which("udisksctl"):
            _ensure_binary_available("udisksctl", [["udisks2"]], webhook_url)
        if not shutil.which("udisksctl"):
            print_and_discord("[AUTOMOUNT] udisksctl not found and installation failed; automount disabled.", webhook_url)
            return
        if not shutil.which("lsblk"):
            _ensure_binary_available("lsblk", [["util-linux"]], webhook_url)

        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem="block")

        last_attempt = {}
        for dev in monitor:
            try:
                action = getattr(dev, "action", "") or ""
                if action not in ("add", "change"):
                    continue
                if dev.get("DEVTYPE") != "partition":
                    continue

                device_node = getattr(dev, "device_node", None)
                if not device_node:
                    continue

                bus = str(dev.get("ID_BUS") or "").lower()
                is_external = bus in ("usb", "sdio")
                if not is_external:
                    if str(dev.get("ID_DRIVE_FLASH_SD") or "") == "1":
                        is_external = True
                    elif str(dev.get("ID_DRIVE_THUMB") or "") == "1":
                        is_external = True
                    elif str(dev.get("ID_USB_DRIVER") or ""):
                        is_external = True
                if not is_external:
                    continue

                now = time.time()
                last = last_attempt.get(device_node, 0)
                if now - last < 5.0:
                    continue
                last_attempt[device_node] = now

                print_and_discord(f"[AUTOMOUNT] Detectie: action={action} device={device_node}", webhook_url)
                _automount_handle_device(device_node, webhook_url)
            except Exception as exc:
                _stats_record_error(exc)
                print_and_discord(f"[AUTOMOUNT] Handler error: {exc}", webhook_url)

    t = threading.Thread(target=_run, daemon=True, name="automount")
    t.start()
    _automount_thread = t
    return t


def get_next_disk(current_disk, disks):
    current_index = disks.index(current_disk)
    next_index = (current_index + 1) % len(disks)
    return disks[next_index]

def ask_disk_info(disk_number):
    path = input(f"Enter the path for disk {disk_number}: ")
    name = f"disk{disk_number}"
    return {
        'path': path,
        'name': name
    }

def check_files_and_move(src, disks, last_disk, webhook_url, min_file_age_hours, extra_safety_space_gb):
    time_limit = timedelta(hours=min_file_age_hours)
    now = datetime.now()

    files_to_move = []
    for dirpath, _dirnames, filenames in os.walk(src):
        for filename in filenames:
            source_path = os.path.join(dirpath, filename)
            modified_date = get_last_modified_time(source_path)
            if now - modified_date > time_limit:
                rel_path = os.path.relpath(source_path, src)
                files_to_move.append(rel_path)
            else:
                print_and_discord(f"{filename} is too new and will not be moved yet.", webhook_url)

    if not files_to_move:
        print_and_discord("\nNo files to move.", webhook_url)
        return last_disk

    print_and_discord("\nMoving files:", webhook_url)

    if not disks:
        print_and_discord("No disks are configured to move files to.", webhook_url)
        return last_disk

    cfg = {}
    try:
        cfg = _load_config_from_disk()
    except Exception:
        cfg = {}
    settings_cfg = cfg.get("settings") if isinstance(cfg, dict) else {}
    if not isinstance(settings_cfg, dict):
        settings_cfg = {}
    strategy = _normalize_backup_strategy(settings_cfg.get("backup_strategy"))
    raid_mode = _normalize_raid_simulation(settings_cfg.get("raid_simulation"))
    set_vfs_dedupe_duplicate_names(raid_mode in ("raid1", "raid1_all", "raid5", "raid6", "raid10"))

    def _disk_path_of(d):
        if not isinstance(d, dict):
            return ""
        return str(d.get("path") or d.get("pad") or "").strip()

    def _disk_name_of(d, fallback_index):
        if not isinstance(d, dict):
            return f"disk{fallback_index + 1}"
        return str(d.get("name") or d.get("naam") or f"disk{fallback_index + 1}").strip() or f"disk{fallback_index + 1}"

    def _disk_usage(disk_path):
        try:
            total, used, free = shutil.disk_usage(disk_path)
            used_pct = (used / total * 100.0) if total else 0.0
            return int(total), int(used), int(free), float(used_pct)
        except Exception:
            return None

    def _free_bytes(disk_path):
        usage = _disk_usage(disk_path)
        if not usage:
            return -1
        return int(usage[2])

    def _used_pct(disk_path):
        usage = _disk_usage(disk_path)
        if not usage:
            return 101.0
        return float(usage[3])

    def _ordered_candidates(rel_path_for_hash):
        candidates = []
        for i, d in enumerate(disks):
            disk_path = _disk_path_of(d)
            if not disk_path:
                continue
            candidates.append((i, d, _disk_name_of(d, i), disk_path))
        if not candidates:
            return []

        if strategy == "most_free_space":
            return sorted(candidates, key=lambda x: _free_bytes(x[3]), reverse=True)
        if strategy == "least_used_pct":
            return sorted(candidates, key=lambda x: (_used_pct(x[3]), -_free_bytes(x[3])))
        if strategy == "path_hash":
            try:
                h = hashlib.sha1(str(rel_path_for_hash).encode("utf-8", errors="ignore")).hexdigest()
                start = int(h[:8], 16) % len(candidates)
            except Exception:
                start = 0
            return candidates[start:] + candidates[:start]

        start_index = 0
        if last_disk:
            for i, d in enumerate(disks):
                if str(d.get("name") or "").strip() == str(last_disk).strip():
                    start_index = i
                    break
        ordered = []
        for offset in range(len(disks)):
            idx = (start_index + offset) % len(disks)
            d = disks[idx]
            disk_path = _disk_path_of(d)
            if not disk_path:
                continue
            ordered.append((idx, d, _disk_name_of(d, idx), disk_path))
        return ordered

    for rel_path in files_to_move:
        source_path = os.path.join(src, rel_path)
        if not os.path.exists(source_path):
            continue

        file_size_bytes = get_file_size(source_path)
        file_size_gb = file_size_bytes // (2**30)
        required_space = file_size_gb + extra_safety_space_gb

        candidates = _ordered_candidates(rel_path)
        if not candidates:
            print_and_discord(f"No available disks for {rel_path}, skipping file.", webhook_url)
            continue

        def _enough_space_for(disk_name, disk_path):
            try:
                return has_sufficient_free_space(disk_path, required_space)
            except Exception as exc:
                print_and_discord(f"Disk check failed for {disk_name} ({disk_path}): {exc}", webhook_url)
                return False

        def _copy_to(disk_name, disk_path):
            destination_path = os.path.join(disk_path, rel_path)
            destination_folder = os.path.dirname(destination_path)
            if not os.path.exists(destination_folder):
                os.makedirs(destination_folder, exist_ok=True)
            if os.path.exists(destination_path):
                return destination_path, False
            shutil.copy2(source_path, destination_path)
            return destination_path, True

        def _delete_source():
            try:
                if os.path.exists(source_path):
                    os.remove(source_path)
            except Exception as exc:
                _stats_record_error(exc)
                print_and_discord(f"Failed to delete source file ({rel_path}): {exc}", webhook_url)

        def _raid_target_count():
            if raid_mode == "raid1_all":
                return len(candidates)
            if raid_mode in ("raid1", "raid5", "raid10"):
                return 2
            if raid_mode == "raid6":
                return 3
            return 1

        def _raid10_pair_candidates():
            by_name = sorted(candidates, key=lambda x: (x[2] or "", x[3] or ""))
            pairs = []
            i = 0
            while i < len(by_name):
                a = by_name[i]
                b = by_name[i + 1] if (i + 1) < len(by_name) else None
                pairs.append((a, b))
                i += 2
            if not pairs:
                return []
            try:
                h = hashlib.sha1(str(rel_path).encode("utf-8", errors="ignore")).hexdigest()
                pair_idx = int(h[:8], 16) % len(pairs)
            except Exception:
                pair_idx = 0
            a, b = pairs[pair_idx]
            out = []
            if a:
                out.append(a)
            if b:
                out.append(b)
            return out

        if raid_mode in ("raid1", "raid1_all", "raid5", "raid6", "raid10"):
            target_count = _raid_target_count()
            copied_to = []
            print_and_discord(
                f"File: {rel_path}, size: {file_size_gb} GB, required space per disk: {required_space} GB",
                webhook_url,
            )
            with _file_operation_lock:
                raid_candidates = candidates
                if raid_mode == "raid10":
                    raid_candidates = _raid10_pair_candidates()
                for _idx, _disk, disk_name, disk_path in raid_candidates:
                    if len(copied_to) >= target_count:
                        break
                    if not os.path.exists(source_path):
                        break
                    if not _enough_space_for(disk_name, disk_path):
                        continue
                    try:
                        destination_path, did_copy = _copy_to(disk_name, disk_path)
                        _invalidate_vfs_caches()
                        if did_copy:
                            print_and_discord(f"{rel_path} copied to {disk_name}", webhook_url)
                        else:
                            print_and_discord(f"{rel_path} already existed on {disk_name} (skip copy)", webhook_url)
                        _stats_record_move(source_path, destination_path, file_size_bytes, disk_name, f"balancer_{raid_mode}")
                        copied_to.append(disk_name)
                        if not last_disk:
                            last_disk = disk_name
                        elif last_disk and last_disk not in copied_to:
                            pass
                    except Exception as exc:
                        _stats_record_error(exc)
                        print_and_discord(f"Copy failed to {disk_name} ({disk_path}): {exc}", webhook_url)
                        continue

                if copied_to:
                    _delete_source()
                    _invalidate_vfs_caches()
                    last_disk = copied_to[0] or last_disk
                else:
                    print_and_discord(f"No disk could store {rel_path}, skipping file.", webhook_url)
        else:
            moved = False
            for _idx, _disk, disk_name, disk_path in candidates:
                print_and_discord(
                    f"File: {rel_path}, size: {file_size_gb} GB, required space: {required_space} GB",
                    webhook_url,
                )
                print_and_discord(f"Trying to move {rel_path} to {disk_name}.", webhook_url)
                if not os.path.exists(source_path):
                    break
                if not _enough_space_for(disk_name, disk_path):
                    print_and_discord(f"Insufficient space or disk not available for {rel_path} on {disk_name}", webhook_url)
                    continue
                try:
                    with _file_operation_lock:
                        destination_path = os.path.join(disk_path, rel_path)
                        destination_folder = os.path.dirname(destination_path)
                        if not os.path.exists(destination_folder):
                            os.makedirs(destination_folder, exist_ok=True)
                        shutil.move(source_path, destination_path)
                        _invalidate_vfs_caches()
                    print_and_discord(f"{rel_path} moved to {disk_name}", webhook_url)
                    _stats_record_move(source_path, destination_path, file_size_bytes, disk_name, "balancer")
                    last_disk = disk_name
                    moved = True
                    break
                except Exception as exc:
                    _stats_record_error(exc)
                    print_and_discord(f"Move failed to {disk_name} ({disk_path}): {exc}", webhook_url)
                    continue
            if not moved:
                print_and_discord(f"No disk has enough space for {rel_path}, skipping file.", webhook_url)

    print_and_discord("\nMoving files completed.", webhook_url)
    return last_disk

def remove_oldest_file(folder_path, webhook_url, action, move_destination=None):
    # Backwards compatible wrapper: remove one oldest eligible file recursively.
    removed, _result = _cleanup_disk_once(
        disk_path=folder_path,
        webhook_url=webhook_url,
        action=action,
        move_destination=move_destination,
        min_file_age_hours=0,
        exclude_folders=None,
    )
    if not removed:
        print_and_discord("No files found to clean up.", webhook_url)


def _same_or_child_path(path, base_path):
    norm_path = os.path.normcase(os.path.normpath(path))
    norm_base = os.path.normcase(os.path.normpath(base_path))
    return norm_path == norm_base or norm_path.startswith(norm_base + os.sep)


def _path_within_base(path, base_path):
    try:
        real_path = os.path.normcase(os.path.realpath(path))
        real_base = os.path.normcase(os.path.realpath(base_path))
        return _same_or_child_path(real_path, real_base)
    except OSError:
        return False


def _normalize_excluded_folders(base_path, exclude_folders):
    excluded = []
    if exclude_folders is None:
        source_list = []
    else:
        source_list = exclude_folders

    for raw in source_list:
        if not raw:
            continue
        candidate = str(raw).strip()
        if not candidate:
            continue
        if os.path.isabs(candidate):
            abs_path = os.path.normpath(candidate)
        else:
            abs_path = os.path.normpath(os.path.join(base_path, candidate))
        excluded.append(os.path.normcase(abs_path))
    return excluded


def _is_excluded_path(path, excluded_paths):
    norm_path = os.path.normcase(os.path.normpath(path))
    for excluded in excluded_paths:
        if _same_or_child_path(norm_path, excluded):
            return True
    return False


def _iter_files_recursive(base_path, webhook_url, exclude_folders=None):
    base_path = os.path.normpath(base_path)
    if not os.path.isdir(base_path):
        return

    real_base = os.path.normcase(os.path.realpath(base_path))
    excluded_paths = _normalize_excluded_folders(base_path, exclude_folders)
    visited_dirs = {real_base}
    stack = [base_path]

    while stack:
        current_dir = stack.pop()
        if _is_excluded_path(current_dir, excluded_paths):
            continue
        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    try:
                        entry_path = entry.path
                        if _is_excluded_path(entry_path, excluded_paths):
                            continue
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            real_child = os.path.normcase(os.path.realpath(entry_path))
                            if real_child in visited_dirs:
                                continue
                            if not _same_or_child_path(real_child, real_base):
                                continue
                            visited_dirs.add(real_child)
                            stack.append(entry_path)
                        elif entry.is_file(follow_symlinks=False):
                            if _path_within_base(entry_path, base_path):
                                yield entry_path
                    except (PermissionError, OSError) as exc:
                        _cleanup_log("WARNING", webhook_url, f"Skip inaccessible entry {entry.path}: {exc}")
        except (PermissionError, OSError) as exc:
            _cleanup_log("WARNING", webhook_url, f"Cannot scan folder {current_dir}: {exc}")


def _is_file_locked_or_in_use(file_path):
    try:
        fd = os.open(file_path, os.O_RDWR)
    except OSError:
        return True
    try:
        try:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            return True
    finally:
        os.close(fd)
    return False


def _is_file_stable(file_path):
    try:
        st_before = os.stat(file_path)
        time.sleep(0.05)
        st_after = os.stat(file_path)
    except OSError:
        return False
    return (
        st_before.st_size == st_after.st_size
        and st_before.st_mtime == st_after.st_mtime
    )


def _find_oldest_eligible_file(base_path, webhook_url, min_file_age_hours, exclude_folders=None, max_rescans=8):
    blocked_paths = set()
    now_ts = time.time()
    min_age_seconds = max(0, float(min_file_age_hours)) * 3600.0

    for _ in range(max_rescans):
        oldest_path = None
        oldest_mtime = float('inf')
        oldest_size = 0

        for file_path in _iter_files_recursive(base_path, webhook_url, exclude_folders=exclude_folders):
            if file_path in blocked_paths:
                continue
            try:
                st = os.stat(file_path)
            except (PermissionError, OSError) as exc:
                _cleanup_log("WARNING", webhook_url, f"Cannot stat file {file_path}: {exc}")
                continue

            file_age_seconds = now_ts - st.st_mtime
            if file_age_seconds < min_age_seconds:
                continue
            if st.st_mtime < oldest_mtime:
                oldest_mtime = st.st_mtime
                oldest_path = file_path
                oldest_size = st.st_size

        if not oldest_path:
            return None

        if _is_file_locked_or_in_use(oldest_path):
            _cleanup_log("INFO", webhook_url, f"Skip locked or in-use file {oldest_path}")
            blocked_paths.add(oldest_path)
            continue
        if not _is_file_stable(oldest_path):
            _cleanup_log("INFO", webhook_url, f"Skip actively changing file {oldest_path}")
            blocked_paths.add(oldest_path)
            continue
        return {
            'path': oldest_path,
            'mtime': oldest_mtime,
            'size': oldest_size,
        }

    return None


def _cleanup_disk_once(
    disk_path,
    webhook_url,
    action,
    move_destination,
    min_file_age_hours,
    exclude_folders=None,
    dry_run=False,
):
    candidate = _find_oldest_eligible_file(
        disk_path,
        webhook_url,
        min_file_age_hours=min_file_age_hours,
        exclude_folders=exclude_folders,
    )
    if not candidate:
        return False, None

    oldest_file = candidate['path']
    size_bytes = candidate.get('size', 0)
    try:
        with _file_operation_lock:
            if action == 'move' and move_destination:
                os.makedirs(move_destination, exist_ok=True)
                new_path = os.path.join(move_destination, os.path.basename(oldest_file))
                if os.path.exists(new_path):
                    stamp = int(time.time())
                    stem, ext = os.path.splitext(os.path.basename(oldest_file))
                    new_path = os.path.join(move_destination, f"{stem}__{stamp}{ext}")
                if dry_run:
                    _cleanup_log("INFO", webhook_url, f"[dry-run] Move candidate: {oldest_file} -> {new_path}")
                else:
                    shutil.move(oldest_file, new_path)
                    _invalidate_vfs_caches()
                    _cleanup_log("INFO", webhook_url, f"Moved oldest file: {oldest_file} -> {new_path}")
                    _stats_record_cleanup('move', size_bytes)
                return True, {'action': 'move', 'path': oldest_file, 'target': new_path, 'mtime': candidate['mtime']}
            if action == 'delete':
                if dry_run:
                    _cleanup_log("INFO", webhook_url, f"[dry-run] Delete candidate: {oldest_file}")
                else:
                    os.remove(oldest_file)
                    _invalidate_vfs_caches()
                    _cleanup_log("INFO", webhook_url, f"Deleted oldest file: {oldest_file}")
                    _stats_record_cleanup('delete', size_bytes)
                return True, {'action': 'delete', 'path': oldest_file, 'mtime': candidate['mtime']}
    except Exception as exc:
        _stats_record_error(exc)
        _cleanup_log("ERROR", webhook_url, f"Cleanup failed for {oldest_file}: {exc}")
        return False, None

    _cleanup_log("WARNING", webhook_url, f"Invalid cleanup action or missing move destination: {action}")
    return False, None


def _get_free_space_gb(disk_path):
    _total, _used, free = shutil.disk_usage(disk_path)
    return free / (2**30)


def check_free_space(
    disk_path,
    min_free_gb,
    webhook_url,
    action,
    move_destination,
    min_file_age_hours=0,
    exclude_folders=None,
    dry_run=False,
    max_actions=None,
):
    free_gb = _get_free_space_gb(disk_path)
    if free_gb >= min_free_gb:
        _cleanup_log("INFO", webhook_url, f"Sufficient space available: {free_gb:.2f} GB free on {disk_path}.")
        return True, 0

    _cleanup_log("WARNING", webhook_url, f"Insufficient space on {disk_path}: {free_gb:.2f} GB free.")
    progress_made = False
    actions_performed = 0
    max_actions = _normalize_positive_int(max_actions)
    while free_gb < min_free_gb:
        if max_actions is not None and actions_performed >= max_actions:
            _cleanup_log("WARNING", webhook_url, f"Cleanup action limit reached on {disk_path} ({max_actions} per cycle).")
            break
        removed, _details = _cleanup_disk_once(
            disk_path=disk_path,
            webhook_url=webhook_url,
            action=action,
            move_destination=move_destination,
            min_file_age_hours=min_file_age_hours,
            exclude_folders=exclude_folders,
            dry_run=dry_run,
        )
        if not removed:
            break
        progress_made = True
        actions_performed += 1
        if dry_run:
            # Dry run simulates one candidate action to avoid an endless loop.
            break
        free_gb = _get_free_space_gb(disk_path)

    if free_gb < min_free_gb and not progress_made:
        _cleanup_log("WARNING", webhook_url, f"No eligible files found for cleanup on {disk_path}.")
    return free_gb >= min_free_gb, actions_performed


def check_and_cleanup_disks(
    space_hunter_disks,
    webhook_url,
    default_min_free_gb,
    default_min_file_age_hours=0,
    default_exclude_folders=None,
    default_dry_run=False,
    default_max_actions_per_cycle=None,
    allow_global_fallback=False,
):
    pressure = []
    global_limit = _normalize_positive_int(default_max_actions_per_cycle)
    global_actions = 0
    for disk in space_hunter_disks:
        disk_path = disk.get('path')
        if not disk_path:
            disk_path = disk.get('pad')
        if not disk_path:
            continue
        min_free_gb = disk.get('min_free_gb', default_min_free_gb)
        action = disk.get('action', 'delete')
        move_destination = disk.get('move_destination')
        min_file_age_hours = disk.get('min_file_age_hours', default_min_file_age_hours)
        default_excludes = default_exclude_folders
        if default_excludes is None:
            default_excludes = []
        exclude_folders = disk.get('exclude_folders', default_excludes)
        dry_run = bool(disk.get('dry_run', default_dry_run))
        disk_action_limit = _normalize_positive_int(disk.get('max_actions_per_cycle'))
        try:
            free_gb = _get_free_space_gb(disk_path)
        except OSError as exc:
            _cleanup_log("ERROR", webhook_url, f"Cannot read free space for {disk_path}: {exc}")
            continue
        if free_gb < min_free_gb:
            pressure.append({
                'disk_path': disk_path,
                'min_free_gb': min_free_gb,
                'action': action,
                'move_destination': move_destination,
                'min_file_age_hours': min_file_age_hours,
                'exclude_folders': exclude_folders,
                'dry_run': dry_run,
                'disk_action_limit': disk_action_limit,
            })
        else:
            _cleanup_log("INFO", webhook_url, f"Sufficient space available: {free_gb:.2f} GB free on {disk_path}.")

    unresolved = []
    for disk_ctx in pressure:
        if global_limit is not None and global_actions >= global_limit:
            _cleanup_log("WARNING", webhook_url, f"Global cleanup action limit reached ({global_limit} per cycle).")
            unresolved.append(disk_ctx)
            continue

        if global_limit is None:
            remaining_global = None
        else:
            remaining_global = global_limit - global_actions
        limits = []
        if remaining_global is not None:
            limits.append(remaining_global)
        if disk_ctx['disk_action_limit'] is not None:
            limits.append(disk_ctx['disk_action_limit'])

        if limits:
            max_actions = min(limits)
        else:
            max_actions = None

        ok, used_actions = check_free_space(
            disk_path=disk_ctx['disk_path'],
            min_free_gb=disk_ctx['min_free_gb'],
            webhook_url=webhook_url,
            action=disk_ctx['action'],
            move_destination=disk_ctx['move_destination'],
            min_file_age_hours=disk_ctx['min_file_age_hours'],
            exclude_folders=disk_ctx['exclude_folders'],
            dry_run=disk_ctx['dry_run'],
            max_actions=max_actions,
        )
        global_actions += used_actions
        if not ok:
            unresolved.append(disk_ctx)

    if not unresolved:
        return

    if not allow_global_fallback:
        for disk_ctx in unresolved:
            _cleanup_log(
                "WARNING",
                webhook_url,
                f"Disk still below threshold without fallback enabled: {disk_ctx['disk_path']}",
            )
        return

    _cleanup_log("WARNING", webhook_url, "Starting global fallback cleanup across pressured disks.")
    while unresolved:
        if global_limit is not None and global_actions >= global_limit:
            _cleanup_log("WARNING", webhook_url, f"Global cleanup action limit reached ({global_limit} per cycle).")
            break

        candidates = []
        for disk_ctx in unresolved:
            candidate = _find_oldest_eligible_file(
                disk_ctx['disk_path'],
                webhook_url,
                min_file_age_hours=disk_ctx['min_file_age_hours'],
                exclude_folders=disk_ctx['exclude_folders'],
            )
            if candidate:
                candidates.append((disk_ctx, candidate))

        if not candidates:
            for disk_ctx in unresolved:
                _cleanup_log(
                    "WARNING",
                    webhook_url,
                    f"No eligible files left on {disk_ctx['disk_path']} while still under threshold.",
                )
            break

        selected_ctx = None
        selected_candidate = None
        for candidate_item in candidates:
            disk_ctx, candidate_info = candidate_item
            if selected_candidate is None or candidate_info['mtime'] < selected_candidate['mtime']:
                selected_ctx = disk_ctx
                selected_candidate = candidate_info

        removed, _details = _cleanup_disk_once(
            disk_path=selected_ctx['disk_path'],
            webhook_url=webhook_url,
            action=selected_ctx['action'],
            move_destination=selected_ctx['move_destination'],
            min_file_age_hours=selected_ctx['min_file_age_hours'],
            exclude_folders=selected_ctx['exclude_folders'],
            dry_run=selected_ctx['dry_run'],
        )
        if not removed:
            new_unresolved = []
            for ctx in unresolved:
                if ctx is selected_ctx:
                    continue
                new_unresolved.append(ctx)
            unresolved = new_unresolved
            continue

        global_actions += 1
        if selected_ctx['dry_run']:
            break

        try:
            new_free_gb = _get_free_space_gb(selected_ctx['disk_path'])
        except OSError as exc:
            _cleanup_log("ERROR", webhook_url, f"Cannot refresh free space for {selected_ctx['disk_path']}: {exc}")
            new_unresolved = []
            for ctx in unresolved:
                if ctx is selected_ctx:
                    continue
                new_unresolved.append(ctx)
            unresolved = new_unresolved
            continue

        if new_free_gb >= selected_ctx['min_free_gb']:
            _cleanup_log(
                "INFO",
                webhook_url,
                f"Threshold reached on {selected_ctx['disk_path']} ({new_free_gb:.2f} GB free).",
            )
            new_unresolved = []
            for ctx in unresolved:
                if ctx is selected_ctx:
                    continue
                new_unresolved.append(ctx)
            unresolved = new_unresolved

def reverse_move_files(reverse_config, webhook_url):
    destination_path = reverse_config.get('destination_path')
    source_paths = reverse_config.get('source_paths', [])
    min_age_hours = reverse_config.get('min_file_age_hours', 12)

    if not destination_path or not source_paths:
        print_and_discord("Reverse RAID: no valid source_paths or destination_path configured.", webhook_url)
        return

    os.makedirs(destination_path, exist_ok=True)

    total_files = 0
    total_moved = 0
    total_skipped_too_new = 0

    print_and_discord(
        f"Reverse RAID: start moving files (older than {min_age_hours} hours).",
        webhook_url,
    )

    for index, source_folder in enumerate(source_paths):
        if not source_folder:
            continue
        if not os.path.isdir(source_folder):
            print_and_discord(
                f"Reverse RAID: source folder {index + 1} ({source_folder}) does not exist or is not a folder.",
                webhook_url,
            )
            continue

        files_in_folder = 0
        moved_in_folder = 0

        for dirpath, _dirnames, filenames in os.walk(source_folder):
            for filename in filenames:
                source_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(source_path, source_folder)
                destination_file_path = os.path.join(destination_path, rel_path)

                file_time = os.path.getmtime(source_path)
                file_age_hours = (time.time() - file_time) / 3600

                if file_age_hours < min_age_hours:
                    print_and_discord(
                        f"Reverse RAID: skipping {rel_path}, too new ({file_age_hours:.1f} hours).",
                        webhook_url,
                    )
                    total_skipped_too_new += 1
                    continue

                total_files += 1
                files_in_folder += 1

                if os.path.exists(destination_file_path):
                    print_and_discord(
                        f"Reverse RAID: skipping {rel_path}, already exists in destination folder.",
                        webhook_url,
                    )
                    continue

                try:
                    with _file_operation_lock:
                        os.makedirs(os.path.dirname(destination_file_path), exist_ok=True)
                        size_bytes = os.path.getsize(source_path)
                        shutil.move(source_path, destination_file_path)
                        _invalidate_vfs_caches()
                    print_and_discord(f"Reverse RAID: moved {rel_path}", webhook_url)
                    _stats_record_move(source_path, destination_file_path, size_bytes, "", "reverse_raid")
                    total_moved += 1
                    moved_in_folder += 1
                except Exception as e:
                    _stats_record_error(e)
                    print_and_discord(
                        f"Reverse RAID: error while moving {rel_path}: {e}",
                        webhook_url,
                    )

        if files_in_folder > 0:
            print_and_discord(
                f"Reverse RAID: folder {index + 1}: moved {moved_in_folder} of {files_in_folder} files from {source_folder}",
                webhook_url,
            )

    if total_moved > 0 or total_files > 0:
        print_and_discord(
            f"Reverse RAID: finished, moved {total_moved} of {total_files} files to {destination_path}",
            webhook_url,
        )
    else:
        print_and_discord("Reverse RAID: no files moved in this cycle.", webhook_url)

def main():
    _ensure_linux()

    atexit.register(_cleanup_managed_nfs_exports)
    atexit.register(_stop_all_managed_containers)
    _shutdown_called = [False]
    def _shutdown_signal_handler(signum, frame):
        if _shutdown_called[0]:
            return
        _shutdown_called[0] = True
        _cleanup_managed_nfs_exports()
        _stop_all_managed_containers()
        sys.exit(0)
    for _sn in ('SIGINT', 'SIGTERM'):
        _sig = getattr(signal, _sn, None)
        if _sig is not None:
            try:
                signal.signal(_sig, _shutdown_signal_handler)
            except Exception:
                pass

    loaded_config = read_config()
    if loaded_config is None:
        config = {}
    else:
        config = loaded_config
    config_exists = os.path.exists(config_path)

    settings = config.get('settings', {})
    min_file_age_hours = settings.get('min_file_age_hours', 4)
    extra_safety_space_gb = settings.get('extra_safety_space_gb', 5)
    scan_interval_seconds = settings.get('scan_interval_seconds', 120)
    console_clear_interval_hours = settings.get('console_clear_interval_hours', 6)
    backup_strategy = _normalize_backup_strategy(settings.get('backup_strategy'))
    space_check_default_min_free_gb = settings.get('space_check_default_min_free_gb', 40)
    space_hunter_min_file_age_hours = settings.get('space_hunter_min_file_age_hours', min_file_age_hours)
    space_hunter_exclude_folders = settings.get('space_hunter_exclude_folders', [])
    space_hunter_dry_run = bool(settings.get('space_hunter_dry_run', False))
    space_hunter_max_actions_per_cycle = _normalize_positive_int(settings.get('space_hunter_max_actions_per_cycle'))
    space_hunter_global_fallback = bool(settings.get('space_hunter_global_fallback', False))
    if not isinstance(space_hunter_exclude_folders, list):
        space_hunter_exclude_folders = []

    reverse_raid_config = config.get('reverse_raid', {})
    reverse_enabled = reverse_raid_config.get('enabled', False)
    reverse_interval_minutes = reverse_raid_config.get('run_interval_minutes', 10)

    webdav_server_config = config.get('webdav_server', {})
    sftp_server_config = config.get('sftp_server', {})
    nfs_server_config = config.get('nfs_server', {})
    fuse_server_config = config.get('fuse_server', {})

    print("Config loaded from config.yml (or default values used when missing):")

    src_folders_config = config.get('src_folders')
    src_from_config = config.get('src', '')
    src_folders = []

    if src_folders_config:
        src_folders = []
        for path in src_folders_config:
            if path:
                src_folders.append(path)
    elif config_exists and src_from_config:
        src_folders = [src_from_config]
    else:
        try:
            num_input_folders = int(input("How many input folders do you want to configure? "))
        except ValueError:
            num_input_folders = 1
        if num_input_folders < 1:
            num_input_folders = 1
        for i in range(num_input_folders):
            if i == 0 and src_from_config:
                src_path = src_from_config
            else:
                src_path = input(f"Enter the path for input folder {i + 1}: ")
            src_folders.append(src_path)

    if not src_folders:
        if config_exists and src_from_config:
            src_folders = [src_from_config]
        else:
            src_path = input("Enter the path for the input folder: ")
            src_folders = [src_path]

    extra_input_folders = []
    for key in ('input_folders', 'inputs', 'source_folders'):
        value = config.get(key)
        if isinstance(value, list):
            for path in value:
                if path:
                    extra_input_folders.append(path)
    for extra_input in extra_input_folders:
        if extra_input not in src_folders:
            src_folders.append(extra_input)

    extra_output_folders = []
    for key in ('output_folders', 'target_folders', 'dst_folders', 'destination_folders'):
        value = config.get(key)
        if isinstance(value, list):
            for path in value:
                if path:
                    extra_output_folders.append(path)

    src = src_folders[0]
    webhook_url = config.get('webhook_url', '')
    if not config_exists:
        webhook_input = input("Enter the Discord webhook URL (leave empty to disable Discord notifications): ")
        if webhook_input.strip():
            webhook_url = webhook_input
        else:
            webhook_url = ""
    elif webhook_url is None:
        webhook_input = input("Enter the Discord webhook URL (leave empty to disable Discord notifications): ")
        if webhook_input.strip():
            webhook_url = webhook_input
        else:
            webhook_url = ""

    if not config_exists:
        webpanel_cfg = config.get('webpanel')
        if not isinstance(webpanel_cfg, dict):
            webpanel_cfg = {}
        default_webpanel_host = str(webpanel_cfg.get('host', '0.0.0.0'))
        default_webpanel_port = _coerce_int(webpanel_cfg.get('port', 5000), default=5000, min_value=1, max_value=65535)
        host_input = input(f"Webserver host (default {default_webpanel_host}): ").strip()
        port_input = input(f"Webserver port (default {default_webpanel_port}): ").strip()
        selected_host = host_input or default_webpanel_host
        selected_port = _coerce_int(port_input, default=default_webpanel_port, min_value=1, max_value=65535)
        config['webpanel'] = {
            'enabled': True,
            'host': selected_host,
            'port': selected_port,
        }

    disks = config.get('disks', [])
    last_disk = config.get('last_disk', '')
    space_hunter_disks = config.get('space_hunter_disks', [])

    if not disks:
        num_disks = int(input("How many disks do you want to add? "))
        disks = []
        for i in range(num_disks):
            disk_info = ask_disk_info(i + 1)
            disks.append(disk_info)
        last_disk = disks[0]['name']

    if not last_disk and disks:
        last_disk = disks[0]['name']

    if not space_hunter_disks and not config_exists:
        use_space_hunter = input("Do you want to enable automatic disk space checks and cleanup? (yes/no): ").lower() == 'yes'
        if use_space_hunter:
            min_space_input = input(f"Default minimum free space in GB for space hunter (default {space_check_default_min_free_gb}): ").strip()
            if min_space_input.isdigit():
                space_check_default_min_free_gb = int(min_space_input)
            try:
                num_cleanup_disks = int(input("How many disks do you want to monitor for free space? "))
                for i in range(num_cleanup_disks):
                    disk_path = input(f"Enter the path of disk {i + 1} to monitor: ")
                    min_free_gb_input = input(f"Enter the minimum free space in GB (default {space_check_default_min_free_gb}): ")
                    if min_free_gb_input.strip().isdigit():
                        min_free_gb = int(min_free_gb_input)
                    else:
                        min_free_gb = space_check_default_min_free_gb
                    action_input = input("Enter the action (move/delete, default delete): ").lower()
                    if action_input not in ['move', 'delete']:
                        action_input = 'delete'
                    move_destination = None
                    if action_input == 'move':
                        move_destination = input("Enter the move destination path: ")
                        while not os.path.isdir(move_destination):
                            print("Invalid path. Make sure the folder exists.")
                            move_destination = input("Enter the move destination path: ")
                    space_hunter_disks.append({
                        'path': disk_path,
                        'min_free_gb': min_free_gb,
                        'action': action_input,
                        'move_destination': move_destination,
                    })
            except ValueError:
                print("Enter a valid number for the number of disks.")

    if not os.path.exists(config_path):
        print("\nAdvanced settings for file distribution:")
        min_age_input = input(f"Minimum file age in hours (default {min_file_age_hours}): ").strip()
        if min_age_input.isdigit():
            min_file_age_hours = int(min_age_input)
        extra_safety_input = input(f"Extra safety space in GB (default {extra_safety_space_gb}): ").strip()
        if extra_safety_input.isdigit():
            extra_safety_space_gb = int(extra_safety_input)
        scan_interval_input = input(f"Scan interval in seconds (default {scan_interval_seconds}): ").strip()
        if scan_interval_input.isdigit():
            scan_interval_seconds = int(scan_interval_input)
        clear_interval_input = input(f"Console clear interval in hours (default {console_clear_interval_hours}): ").strip()
        if clear_interval_input.isdigit():
            console_clear_interval_hours = int(clear_interval_input)

        shared_upload_src_input = input(f"Shared upload folder for WebDAV/SFTP/NFS/FUSE (default {src}): ").strip()
        shared_upload_src = shared_upload_src_input or src

        webdav_server_cfg = {}
        print("\nWebDAV server:")
        print("- Allows you to mount the virtual disk as a network drive.")
        print("- Requires 'wsgidav' and 'cheroot' to be installed.")
        use_webdav = input("Do you want to enable the WebDAV server? (yes/no): ").strip().lower() == 'yes'
        if use_webdav:
            default_webdav_host = webdav_server_config.get('host', '0.0.0.0')
            default_webdav_port = webdav_server_config.get('port', 8080)
            default_webdav_username = webdav_server_config.get('username', 'admin')
            default_webdav_password = webdav_server_config.get('password', 'admin')
            host_input = input(f"WebDAV host (default {default_webdav_host}): ").strip()
            port_input = input(f"WebDAV port (default {default_webdav_port}): ").strip()
            username_input = input(f"WebDAV username (default {default_webdav_username}): ").strip()
            password_input = input(f"WebDAV password (default {default_webdav_password}): ").strip()
            use_fuse_input = input("Use FUSE mount as WebDAV root? (yes/no, default yes): ").strip().lower() != 'no'
            if port_input.isdigit():
                webdav_port_value = int(port_input)
            else:
                webdav_port_value = default_webdav_port
            webdav_server_cfg = {
                'enabled': True,
                'host': host_input or default_webdav_host,
                'port': webdav_port_value,
                'username': username_input or default_webdav_username,
                'password': password_input or default_webdav_password,
                'upload_src': shared_upload_src,
                'use_fuse_mount_as_root': use_fuse_input,
            }
        else:
            webdav_server_cfg = webdav_server_config or {
                'enabled': False,
                'host': '0.0.0.0',
                'port': 8080,
                'username': 'admin',
                'password': 'admin',
                'upload_src': src,
                'use_fuse_mount_as_root': True,
            }

        sftp_server_cfg = {}
        print("\nSFTP server:")
        print("- Allows you to connect with an SFTP client as if it is a single disk.")
        print("- Uses only username and password (no SSH keys required).")
        print("- The root folder you see in your SFTP client is the configured upload folder.")
        use_sftp = input("Do you want to enable the SFTP server? (yes/no): ").strip().lower() == 'yes'
        if use_sftp:
            default_sftp_host = sftp_server_config.get('host', '0.0.0.0')
            default_sftp_port = sftp_server_config.get('port', 8081)
            default_sftp_username = sftp_server_config.get('username', 'raiduser')
            default_sftp_password = sftp_server_config.get('password', 'changeme')
            host_input = input(f"SFTP host (default {default_sftp_host}): ").strip()
            port_input = input(f"SFTP port (default {default_sftp_port}): ").strip()
            username_input = input(f"SFTP username (default {default_sftp_username}): ").strip()
            password_input = input(f"SFTP password (default {default_sftp_password}): ").strip()
            use_fuse_input_sftp = input("Use FUSE mount as SFTP root? (yes/no, default yes): ").strip().lower() != 'no'
            if port_input.isdigit():
                sftp_port_value = int(port_input)
            else:
                sftp_port_value = default_sftp_port
            sftp_server_cfg = {
                'enabled': True,
                'host': host_input or default_sftp_host,
                'port': sftp_port_value,
                'username': username_input or default_sftp_username,
                'password': password_input or default_sftp_password,
                'upload_src': shared_upload_src,
                'use_fuse_mount_as_root': use_fuse_input_sftp,
            }
        else:
            sftp_server_cfg = sftp_server_config or {
                'enabled': False,
                'host': '0.0.0.0',
                'port': 8081,
                'username': 'raiduser',
                'password': 'changeme',
                'upload_src': src,
                'use_fuse_mount_as_root': True,
            }

        nfs_server_cfg = {}
        print("\nNFS server:")
        print("- Uses the native Linux kernel NFS server (no Docker).")
        print("- Exposes your configured upload folder over NFS.")
        print("- NFSv4 uses only the main NFS port (2049).")
        use_nfs = input("Do you want to enable the NFS server? (yes/no): ").strip().lower() == 'yes'
        if use_nfs:
            default_nfs_host = nfs_server_config.get('host', '0.0.0.0')
            default_nfs_port = nfs_server_config.get('port', 2049)
            default_nfs_permitted = nfs_server_config.get('permitted', '*')
            host_input = input(f"NFS host (default {default_nfs_host}): ").strip()
            port_input = input(f"NFS main port (default {default_nfs_port}): ").strip()
            permitted_input = input(f"NFS permitted clients/CIDR (default {default_nfs_permitted}): ").strip()
            use_fuse_input_nfs = input("Use FUSE mount as NFS export root? (yes/no, default yes): ").strip().lower() != 'no'
            nfs_server_cfg = {
                'enabled': True,
                'host': host_input or default_nfs_host,
                'port': int(port_input) if port_input.isdigit() else default_nfs_port,
                'permitted': permitted_input or default_nfs_permitted,
                'upload_src': shared_upload_src,
                'use_fuse_mount_as_root': use_fuse_input_nfs,
            }
        else:
            nfs_server_cfg = nfs_server_config or {
                'enabled': False,
                'host': '0.0.0.0',
                'port': 2049,
                'permitted': '*',
                'upload_src': src,
                'use_fuse_mount_as_root': True,
            }

        fuse_server_cfg = {}
        print("\nFUSE local mount:")
        print("- Allows you to mount the virtual disk locally.")
        print("- Requires libfuse and 'fusepy' to be installed.")
        if FUSE is None:
            print("- Currently NOT detected. If enabled, an automatic installation attempt will be made.")

        use_fuse = input("Do you want to enable the FUSE local mount? (yes/no): ").strip().lower() == 'yes'

        if use_fuse:
            default_fuse_mount = fuse_server_config.get('mount_point', '')
            while True:
                mount_input = input("FUSE mount point (required, e.g. /mnt/multidisk): ").strip()
                if mount_input:
                    break
            fuse_server_cfg = {
                'enabled': True,
                'mount_point': mount_input or default_fuse_mount,
                'upload_src': shared_upload_src,
            }
        else:
            fuse_server_cfg = fuse_server_config or {
                'enabled': False,
                'mount_point': '',
                'upload_src': src,
            }

        filebrowser_cfg = {}
        if use_fuse:
            default_fb_port = _coerce_int((config.get('filebrowser') or {}).get('port', 8082), default=8082, min_value=1, max_value=65535)
            port_input = input(f"Filebrowser port (default {default_fb_port}): ").strip()
            selected_port = _coerce_int(port_input, default=default_fb_port, min_value=1, max_value=65535)
            default_fb_state_dir = "/var/lib/multidisk-filebalancer/filebrowser" if has_admin_privileges() else os.path.join(os.path.expanduser("~"), ".local", "share", "multidisk-filebalancer", "filebrowser")
            state_dir_input = input(f"Path for Filebrowser data/config (default {default_fb_state_dir}): ").strip()
            fb_username_input = input("Filebrowser username (default admin): ").strip()
            while True:
                p1 = input("Filebrowser password: ").strip()
                p2 = input("Filebrowser password (again): ").strip()
                if p1 != p2:
                    print("Passwords do not match. Try again.")
                    continue
                if not p1:
                    print("Password cannot be empty.")
                    continue
                if len(p1) < 12:
                    print("Password is too short. Minimum length is 12.")
                    continue
                fb_password_input = p1
                break
            filebrowser_cfg = {
                'enabled': True,
                'port': selected_port,
                'state_dir': state_dir_input or default_fb_state_dir,
                'username': fb_username_input or "admin",
                'password': fb_password_input,
                'credentials_initialized': False,
            }
        else:
            filebrowser_cfg = {
                'enabled': False,
                'port': 8082,
                'state_dir': '',
                'username': 'admin',
                'password': '',
                'credentials_initialized': False,
            }

        print("\nReverse RAID configuration:")
        use_reverse = len(src_folders) > 1
        if use_reverse:
            print(f"Reverse RAID will be enabled because you configured {len(src_folders)} input folders.")
        else:
            print("Reverse RAID will not be enabled because you configured only one input folder.")

        reverse_source_paths = []
        reverse_destination_path = src
        reverse_minimum_age_hours = 12
        reverse_interval_minutes = 10
        if use_reverse:
            reverse_source_paths = []
            for disk in disks:
                disk_path = disk.get('path')
                if disk_path:
                    reverse_source_paths.append(disk_path)
            if not reverse_source_paths:
                reverse_source_paths = []
                for folder in src_folders[1:]:
                    if folder:
                        reverse_source_paths.append(folder)
            print(f"Reverse RAID source folders automatically set ({len(reverse_source_paths)}): {reverse_source_paths}")
            dest_input = input(f"Enter the destination folder for reverse RAID (default {src}): ").strip()
            if dest_input:
                reverse_destination_path = dest_input
            min_age_input_rev = input(f"Minimum file age in hours for reverse RAID (default {reverse_minimum_age_hours}): ").strip()
            if min_age_input_rev.isdigit():
                reverse_minimum_age_hours = int(min_age_input_rev)
            interval_input_rev = input(f"Run interval in minutes for reverse RAID (default {reverse_interval_minutes}): ").strip()
            if interval_input_rev.isdigit():
                reverse_interval_minutes = int(interval_input_rev)

        reverse_raid_config = {
            'enabled': use_reverse,
            'source_paths': reverse_source_paths,
            'destination_path': reverse_destination_path,
            'min_file_age_hours': reverse_minimum_age_hours,
            'run_interval_minutes': reverse_interval_minutes,
        }
        reverse_enabled = use_reverse
        reverse_interval_minutes = reverse_raid_config['run_interval_minutes']

        webpanel_cfg_from_runtime = config.get('webpanel')
        if not isinstance(webpanel_cfg_from_runtime, dict):
            webpanel_cfg_from_runtime = {}
        webpanel_cfg_for_save = {
            'enabled': _coerce_bool(webpanel_cfg_from_runtime.get('enabled', True), True),
            'host': str(webpanel_cfg_from_runtime.get('host', '0.0.0.0')),
            'port': _coerce_int(webpanel_cfg_from_runtime.get('port', 5000), default=5000, min_value=1, max_value=65535),
        }

        new_config = {
            'src_folders': src_folders,
            'src': src,
            'webhook_url': webhook_url,
            'disks': disks,
            'last_disk': last_disk,
            'space_hunter_disks': space_hunter_disks,
            'settings': {
                'min_file_age_hours': min_file_age_hours,
                'extra_safety_space_gb': extra_safety_space_gb,
                'scan_interval_seconds': scan_interval_seconds,
                'console_clear_interval_hours': console_clear_interval_hours,
                'space_check_default_min_free_gb': space_check_default_min_free_gb,
                'space_hunter_min_file_age_hours': space_hunter_min_file_age_hours,
                'space_hunter_exclude_folders': list(space_hunter_exclude_folders),
                'space_hunter_dry_run': space_hunter_dry_run,
                'space_hunter_max_actions_per_cycle': space_hunter_max_actions_per_cycle or 0,
                'space_hunter_global_fallback': space_hunter_global_fallback,
            },
            'webdav_server': webdav_server_cfg,
            'sftp_server': sftp_server_cfg,
            'nfs_server': nfs_server_cfg,
            'fuse_server': fuse_server_cfg,
            'filebrowser': filebrowser_cfg,
            'webpanel': webpanel_cfg_for_save,
        }
        if reverse_raid_config:
            new_config['reverse_raid'] = reverse_raid_config
        save_config_if_missing(new_config, config_path=config_path)
        config = new_config
        
        # Update server configs from the newly created config
        webdav_server_config = new_config.get('webdav_server', {})
        sftp_server_config = new_config.get('sftp_server', {})
        nfs_server_config = new_config.get('nfs_server', {})
        fuse_server_config = new_config.get('fuse_server', {})

    # Normalize disks: ensure every disk has both Dutch ('naam', 'pad') and English ('name', 'path') keys.
    for disk in disks:
        if 'name' not in disk and 'naam' in disk:
            disk['name'] = disk['naam']
        if 'naam' not in disk and 'name' in disk:
            disk['naam'] = disk['name']
        if 'path' not in disk and 'pad' in disk:
            disk['path'] = disk['pad']
        if 'pad' not in disk and 'path' in disk:
            disk['pad'] = disk['path']

    # Normalize space_hunter_disks: it uses 'path'/'pad' too.
    for disk in space_hunter_disks:
        if 'path' not in disk and 'pad' in disk:
            disk['path'] = disk['pad']
        if 'pad' not in disk and 'path' in disk:
            disk['pad'] = disk['path']

    webdav_enabled = webdav_server_config.get('enabled', False)
    webdav_upload_src = webdav_server_config.get('upload_src', src)
    if webdav_enabled and webdav_upload_src and webdav_upload_src not in src_folders:
        src_folders.append(webdav_upload_src)

    nfs_enabled = nfs_server_config.get('enabled', False)
    nfs_upload_src = nfs_server_config.get('upload_src', src)
    if nfs_enabled and nfs_upload_src and nfs_upload_src not in src_folders:
        src_folders.append(nfs_upload_src)

    fuse_enabled = fuse_server_config.get('enabled', False)
    fuse_mount_point = fuse_server_config.get('mount_point')
    preflight_sftp_enabled = sftp_server_config.get('enabled', False)
    print_startup_preflight(
        webhook_url,
        fuse_enabled=fuse_enabled,
        webdav_enabled=webdav_enabled,
        sftp_enabled=preflight_sftp_enabled,
        nfs_enabled=nfs_enabled,
        fuse_mount_point=fuse_mount_point,
    )
    if fuse_enabled and FUSE is None:
        print_and_discord("FUSE support requested but libfuse is missing. Attempting automatic installation...", webhook_url)
        install_ok, install_error, needs_admin = install_libfuse()
        if install_ok:
            print_and_discord("FUSE support installed successfully!", webhook_url)
        else:
            if needs_admin and not has_admin_privileges():
                strategy = detect_fuse_install_strategy()
                msg = f"Automatic FUSE installation failed: root privileges are required. Try: {strategy} (or run this program with sudo)."
            else:
                strategy = detect_fuse_install_strategy()
                msg = f"Automatic FUSE installation failed: {install_error}. Install libfuse via your package manager (e.g. {strategy})."
            print_and_discord(msg + " FUSE will be disabled (degraded mode).", webhook_url)
            fuse_enabled = False
            try:
                fuse_server_config["enabled"] = False
            except Exception:
                pass
    if fuse_enabled and FUSE is None:
        print_and_discord("FUSE is enabled but not available on this system. FUSE will be disabled (degraded mode).", webhook_url)
        fuse_enabled = False
        try:
            fuse_server_config["enabled"] = False
        except Exception:
            pass

    fuse_upload_src = fuse_server_config.get('upload_src', src)
    if fuse_enabled and fuse_upload_src and fuse_upload_src not in src_folders:
        src_folders.append(fuse_upload_src)

    sftp_enabled = sftp_server_config.get('enabled', False)
    sftp_upload_src = sftp_server_config.get('upload_src', src)
    if sftp_enabled and sftp_upload_src and sftp_upload_src not in src_folders:
        src_folders.append(sftp_upload_src)

    extra_vfs_paths = list(extra_output_folders)
    reverse_source_paths = reverse_raid_config.get('source_paths', [])
    if isinstance(reverse_source_paths, list):
        for path in reverse_source_paths:
            if path:
                extra_vfs_paths.append(path)
    reverse_destination_path = reverse_raid_config.get('destination_path')
    if reverse_destination_path:
        extra_vfs_paths.append(reverse_destination_path)
    for upload_path in (webdav_upload_src, sftp_upload_src, nfs_upload_src, fuse_upload_src):
        if upload_path:
            extra_vfs_paths.append(upload_path)
    extra_vfs_paths = _normalized_existing_path_entries(extra_vfs_paths)

    initial_vfs_paths = build_vfs_base_paths(src_folders, disks, extra_vfs_paths)
    set_vfs_base_paths(initial_vfs_paths)

    start_webpanel_thread(config, webhook_url)

    fuse_start_status = start_fuse_server_thread(fuse_server_config, fuse_upload_src, webhook_url)

    mount_point = str(fuse_server_config.get('mount_point') or "")
    fuse_runtime_enabled = _coerce_bool(fuse_server_config.get("enabled", False), False)
    if fuse_runtime_enabled:
        time.sleep(2)
        if mount_point:
            waited = 0.0
            while waited < 15.0:
                try:
                    if os.path.ismount(mount_point):
                        break
                except Exception:
                    break
                time.sleep(0.5)
                waited += 0.5
        fuse_failed = bool(fuse_start_status and fuse_start_status.get('failed'))
        fuse_error = (fuse_start_status or {}).get('error', '') if fuse_failed else ""
        fuse_active = _is_mount_active(mount_point)
        if fuse_failed or (mount_point and not fuse_active):
            if fuse_failed:
                if is_privilege_error_text(fuse_error) and not has_admin_privileges():
                    print_and_discord(f"FUSE startup failed due to missing privileges. {admin_restart_instruction()}", webhook_url)
                else:
                    print_and_discord(f"FUSE startup failed: {fuse_error}", webhook_url)
            else:
                print_and_discord(f"FUSE mount does not seem active at {mount_point}. (folder exists, but it is not mounted)", webhook_url)
            print_and_discord("Continuing without FUSE (degraded mode). WebDAV/NFS will use the upload folder as root; SFTP will use the virtual view.", webhook_url)
            try:
                fuse_server_config["enabled"] = False
            except Exception:
                pass
            fuse_runtime_enabled = False
        elif mount_point:
            try:
                entries = os.listdir(mount_point)
                print_and_discord(f"FUSE mount active: {len(entries)} item(s) visible at {mount_point}", webhook_url)
            except Exception as exc:
                print_and_discord(f"FUSE mount active, but folder is not readable for this user: {exc}", webhook_url)

    start_filebrowser_docker(config.get("filebrowser", {}), fuse_server_config.get("mount_point"), webhook_url)

    webdav_serve_root_path = None
    if webdav_enabled and webdav_server_config.get('use_fuse_mount_as_root', True):
        candidate = str(fuse_server_config.get('mount_point') or "")
        if fuse_runtime_enabled and _is_mount_active(candidate):
            webdav_serve_root_path = candidate
        elif candidate:
            print_and_discord("WebDAV: FUSE root requested but FUSE is not active. Falling back to upload_src.", webhook_url)

    start_webdav_server_thread(webdav_server_config, webdav_upload_src, webhook_url, serve_root_path=webdav_serve_root_path)

    sftp_serve_root_path = None
    if sftp_enabled and sftp_server_config.get('use_fuse_mount_as_root', True):
        candidate = str(fuse_server_config.get('mount_point') or "")
        if fuse_runtime_enabled and _is_mount_active(candidate):
            sftp_serve_root_path = candidate

    start_sftp_server_thread(
        sftp_server_config,
        sftp_upload_src,
        webhook_url,
        serve_root_path=sftp_serve_root_path,
    )

    nfs_serve_root_path = None
    if nfs_enabled and nfs_server_config.get('use_fuse_mount_as_root', True):
        candidate = str(fuse_server_config.get('mount_point') or "")
        if fuse_runtime_enabled and _is_mount_active(candidate):
            nfs_serve_root_path = candidate
        elif candidate:
            print_and_discord("NFS: FUSE root requested but FUSE is not active. Falling back to upload_src.", webhook_url)

    start_nfs_server_thread(
        nfs_server_config,
        nfs_upload_src,
        webhook_url,
        serve_root_path=nfs_serve_root_path,
    )

    try:
        start_automount_thread(webhook_url)
        print_and_discord("[AUTOMOUNT] Udev monitor active (block devices).", webhook_url)
    except Exception as exc:
        _stats_record_error(exc)
        print_and_discord(f"[AUTOMOUNT] Could not start automount thread: {exc}", webhook_url)

    while True:
        all_vfs_paths = build_vfs_base_paths(src_folders, disks, extra_vfs_paths)
        set_vfs_base_paths(all_vfs_paths)
        try:
            valid_src_folders = []
            for source_folder in src_folders:
                if os.path.exists(source_folder):
                    valid_src_folders.append(source_folder)
                else:
                    print_and_discord(f"The source folder {source_folder} does not exist.", webhook_url)

            if not valid_src_folders:
                print_and_discord("No valid input folders found. Check the paths in config.yml or at startup.", webhook_url)
                input("Press Enter to try again...")
                continue

            for disk in disks:
                if not isinstance(disk, dict):
                    continue
                disk_path = str(disk.get('path') or disk.get('pad') or "").strip()
                if not disk_path:
                    continue
                if not os.path.isdir(disk_path):
                    if _is_probably_removable_mount_path(disk_path):
                        print_and_discord(f"Disk path missing (probably not mounted): {disk_path}", webhook_url)
                    else:
                        print_and_discord(f"Disk path missing: {disk_path}", webhook_url)

            print_and_discord("\nScript started with the following configuration:", webhook_url)
            for source_folder in valid_src_folders:
                print_and_discord(f"Source folder: {source_folder}", webhook_url)
            for disk in disks:
                name = disk['name']
                path = disk['path']
                print_and_discord(f"Disk {name}: {path}", webhook_url)
            print_and_discord(f"Last used disk: {last_disk}", webhook_url)

            last_clear = datetime.now()
            clear_interval = timedelta(hours=console_clear_interval_hours)
            last_reverse_run = datetime.now()
            reverse_interval = timedelta(minutes=reverse_interval_minutes)
            disk_state_by_name = {}
            disk_state_by_path = {}
            while True:
                _stats_cycle_begin()
                print_and_discord("======================================================", webhook_url)
                available_disks = _filter_available_disks(
                    disks,
                    webhook_url,
                    disk_state_by_name,
                    key_fn=lambda d: (d.get("name") or d.get("path") or ""),
                    label="Disk",
                )
                available_space_hunter_disks = _filter_available_disks(
                    space_hunter_disks or [],
                    webhook_url,
                    disk_state_by_path,
                    key_fn=lambda d: (d.get("path") or d.get("pad") or ""),
                    label="SpaceHunter disk",
                )

                all_vfs_paths = build_vfs_base_paths(valid_src_folders, available_disks, extra_vfs_paths)
                set_vfs_base_paths(all_vfs_paths)
                try:
                    cfg_now = _load_config_from_disk()
                    settings_now = cfg_now.get("settings") if isinstance(cfg_now, dict) else {}
                    if not isinstance(settings_now, dict):
                        settings_now = {}
                    set_vfs_dedupe_duplicate_names(_normalize_raid_simulation(settings_now.get("raid_simulation")) in ("raid1", "raid1_all", "raid5", "raid6", "raid10"))
                except Exception:
                    set_vfs_dedupe_duplicate_names(False)

                if available_disks:
                    disk_names = {d.get("name") for d in available_disks}
                    if last_disk and last_disk not in disk_names:
                        last_disk = available_disks[0].get("name") or last_disk

                for source_folder in valid_src_folders:
                    print_and_discord(f"Checking source folder: {source_folder}", webhook_url)
                    last_disk = check_files_and_move(
                        source_folder,
                        available_disks,
                        last_disk,
                        webhook_url,
                        min_file_age_hours,
                        extra_safety_space_gb,
                    )
                if available_space_hunter_disks:
                    check_and_cleanup_disks(
                        available_space_hunter_disks,
                        webhook_url,
                        space_check_default_min_free_gb,
                        default_min_file_age_hours=space_hunter_min_file_age_hours,
                        default_exclude_folders=space_hunter_exclude_folders,
                        default_dry_run=space_hunter_dry_run,
                        default_max_actions_per_cycle=space_hunter_max_actions_per_cycle,
                        allow_global_fallback=space_hunter_global_fallback,
                    )

                if reverse_enabled and datetime.now() - last_reverse_run >= reverse_interval:
                    reverse_move_files(reverse_raid_config, webhook_url)
                    last_reverse_run = datetime.now()

                print_and_discord("======================================================", webhook_url)
                _stats_cycle_end(scan_interval_seconds)

                if datetime.now() - last_clear > clear_interval:
                    clear_command = 'clear'
                    os.system(clear_command)
                    last_clear = datetime.now()
                    print_and_discord("Console cleared", webhook_url)

                time.sleep(scan_interval_seconds)

        except Exception as e:
            _stats_record_error(e)
            print_and_discord(f"An error occurred: {str(e)}", webhook_url)
            input("Press Enter to restart the program...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("\n========== FATAL ERROR ==========")
        traceback.print_exc()
        print("=================================")
        sys.exit(1)
