"""Cross-platform helpers for enabling and disabling internet connectivity."""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Literal

SystemName = Literal["Windows", "Linux", "Darwin", "Unknown"]


@dataclass
class NetworkStatus:
    online: bool
    system: SystemName
    method: str
    detail: str
    adapters: list[str]


@dataclass
class ToggleResult:
    ok: bool
    online: bool
    message: str
    needs_admin: bool = False


def detect_system() -> SystemName:
    name = platform.system()
    if name in ("Windows", "Linux", "Darwin"):
        return name  # type: ignore[return-value]
    return "Unknown"


def _run(cmd: list[str], *, shell: bool = False, timeout: float = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        shell=shell,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _which(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for prefix in ("/usr/sbin", "/sbin", "/usr/bin", "/bin"):
        candidate = f"{prefix}/{name}"
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None



def _windows_adapters() -> list[str]:
    """Return physical Ethernet/Wi-Fi adapter names via PowerShell."""
    ps = (
        "Get-NetAdapter | "
        "Where-Object { $_.HardwareInterface -eq $true -and "
        "($_.MediaType -eq '802.3' -or $_.MediaType -eq 'Native 802.11' "
        "-or $_.InterfaceDescription -match 'Wi-?Fi|Wireless|Ethernet|LAN') } | "
        "Select-Object -ExpandProperty Name"
    )
    result = _run(["powershell", "-NoProfile", "-Command", ps])
    if result.returncode != 0:
        # Fallback: all up/down adapters that look like NIC names
        result = _run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetAdapter | Select-Object -ExpandProperty Name",
            ]
        )
    names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return names


def _windows_online(adapters: list[str] | None = None) -> tuple[bool, list[str]]:
    adapters = adapters if adapters is not None else _windows_adapters()
    if not adapters:
        return False, []
    names_ps = ", ".join(f"'{a}'" for a in adapters)
    ps = (
        f"$names = @({names_ps}); "
        "Get-NetAdapter | Where-Object { $names -contains $_.Name } | "
        "Select-Object Name, Status | ConvertTo-Csv -NoTypeInformation"
    )
    result = _run(["powershell", "-NoProfile", "-Command", ps])
    up = False
    for line in result.stdout.splitlines()[1:]:
        if re.search(r'"?Up"?', line, re.I):
            up = True
            break
    return up, adapters


def _windows_set(enable: bool) -> ToggleResult:
    adapters = _windows_adapters()
    if not adapters:
        return ToggleResult(
            ok=False,
            online=False,
            message="Не найдены сетевые адаптеры Ethernet/Wi‑Fi.",
        )

    verb = "Enable-NetAdapter" if enable else "Disable-NetAdapter"
    failures: list[str] = []
    for name in adapters:
        ps = f"{verb} -Name '{name.replace(chr(39), chr(39)+chr(39))}' -Confirm:$false"
        result = _run(["powershell", "-NoProfile", "-Command", ps])
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            if "Access is denied" in err or "требуется" in err.lower() or "administrator" in err.lower():
                return ToggleResult(
                    ok=False,
                    online=not enable,
                    message="Нужны права администратора. Запустите Nexora от имени администратора.",
                    needs_admin=True,
                )
            failures.append(f"{name}: {err or 'ошибка'}")

    online, _ = _windows_online(adapters)
    if failures and online == (not enable):
        return ToggleResult(ok=False, online=online, message="; ".join(failures))
    action = "включён" if online else "отключён"
    return ToggleResult(ok=True, online=online, message=f"Интернет {action}.")


def _linux_method() -> str:
    if _which("nmcli"):
        return "nmcli"
    if _which("ip"):
        return "ip"
    return "none"


def _linux_online() -> tuple[bool, str, list[str]]:
    method = _linux_method()
    if method == "nmcli":
        result = _run(["nmcli", "-t", "-f", "NETWORKING", "general"])
        networking = result.stdout.strip().upper()
        online = networking == "ENABLED"
        adapters_r = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"])
        adapters = []
        for line in adapters_r.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[1] in ("wifi", "ethernet"):
                adapters.append(f"{parts[0]} ({parts[1]}: {parts[2]})")
        return online, method, adapters
    if method == "ip":
        result = _run(["ip", "-o", "link", "show", "up"])
        adapters = []
        online = False
        for line in result.stdout.splitlines():
            # skip loopback
            if " lo:" in f" {line}" or line.split(":")[1].strip().startswith("lo"):
                continue
            name = line.split(":")[1].strip().split("@")[0]
            if any(x in name for x in ("eth", "en", "wl", "wwan", "usb")):
                adapters.append(name)
                online = True
        return online, method, adapters
    return False, method, []


def _linux_set(enable: bool) -> ToggleResult:
    method = _linux_method()
    if method == "nmcli":
        arg = "on" if enable else "off"
        result = _run(["nmcli", "networking", arg])
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            needs_admin = "Permission" in err or "not authorized" in err.lower() or result.returncode == 4
            return ToggleResult(
                ok=False,
                online=not enable,
                message=err or "Не удалось изменить сеть через nmcli.",
                needs_admin=needs_admin,
            )
        online, _, _ = _linux_online()
        return ToggleResult(
            ok=True,
            online=online,
            message="Интернет включён." if online else "Интернет отключён.",
        )

    if method == "ip":
        # Toggle common interface names that are currently known
        list_r = _run(["ip", "-o", "link", "show"])
        targets: list[str] = []
        for line in list_r.stdout.splitlines():
            name = line.split(":")[1].strip().split("@")[0]
            if name == "lo":
                continue
            if any(name.startswith(p) for p in ("eth", "en", "wl", "ww", "usb")):
                targets.append(name)
        if not targets:
            return ToggleResult(ok=False, online=False, message="Сетевые интерфейсы не найдены.")
        action = "up" if enable else "down"
        failures = []
        for name in targets:
            result = _run(["ip", "link", "set", name, action])
            if result.returncode != 0:
                err = (result.stderr or "").strip()
                if "Operation not permitted" in err or "permission" in err.lower():
                    return ToggleResult(
                        ok=False,
                        online=not enable,
                        message="Нужны права root. Запустите: sudo python -m nexora",
                        needs_admin=True,
                    )
                failures.append(f"{name}: {err or 'ошибка'}")
        online, _, _ = _linux_online()
        if failures:
            return ToggleResult(ok=False, online=online, message="; ".join(failures))
        return ToggleResult(
            ok=True,
            online=online,
            message="Интернет включён." if online else "Интернет отключён.",
        )

    return ToggleResult(
        ok=False,
        online=False,
        message="Нужен NetworkManager (nmcli) или утилита ip.",
    )


def _darwin_services() -> list[str]:
    result = _run(["networksetup", "-listallnetworkservices"])
    services = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("An asterisk"):
            continue
        # Skip disabled marker prefix
        if line.startswith("*"):
            line = line[1:].strip()
        if any(k in line for k in ("Wi-Fi", "Ethernet", "USB", "Thunderbolt", "iPhone", "WLAN")):
            services.append(line)
    return services


def _darwin_online(services: list[str] | None = None) -> tuple[bool, list[str]]:
    services = services if services is not None else _darwin_services()
    online = False
    details = []
    for svc in services:
        # networksetup -getnetworkserviceenabled "Wi-Fi"
        result = _run(["networksetup", "-getnetworkserviceenabled", svc])
        enabled = result.stdout.strip().lower() == "enabled"
        details.append(f"{svc}: {'on' if enabled else 'off'}")
        if enabled:
            online = True
    return online, details


def _darwin_set(enable: bool) -> ToggleResult:
    services = _darwin_services()
    if not services:
        return ToggleResult(ok=False, online=False, message="Сетевые службы не найдены.")
    flag = "on" if enable else "off"
    failures = []
    for svc in services:
        result = _run(["networksetup", "-setnetworkserviceenabled", svc, flag])
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            if "authorization" in err.lower() or "permission" in err.lower():
                return ToggleResult(
                    ok=False,
                    online=not enable,
                    message="Нужны права администратора. Запустите Nexora с sudo.",
                    needs_admin=True,
                )
            failures.append(f"{svc}: {err or 'ошибка'}")
    online, _ = _darwin_online(services)
    if failures and online == (not enable):
        return ToggleResult(ok=False, online=online, message="; ".join(failures))
    return ToggleResult(
        ok=True,
        online=online,
        message="Интернет включён." if online else "Интернет отключён.",
    )


def get_status() -> NetworkStatus:
    system = detect_system()
    if system == "Windows":
        online, adapters = _windows_online()
        return NetworkStatus(
            online=online,
            system=system,
            method="Get-NetAdapter",
            detail="Управление адаптерами Ethernet/Wi‑Fi через PowerShell",
            adapters=adapters,
        )
    if system == "Linux":
        online, method, adapters = _linux_online()
        detail = {
            "nmcli": "NetworkManager (nmcli)",
            "ip": "ip link",
            "none": "Нужен nmcli или утилита ip",
        }.get(method, method)
        return NetworkStatus(
            online=online,
            system=system,
            method=method,
            detail=detail,
            adapters=adapters,
        )
    if system == "Darwin":
        online, adapters = _darwin_online()
        return NetworkStatus(
            online=online,
            system=system,
            method="networksetup",
            detail="Службы сети macOS",
            adapters=adapters,
        )
    return NetworkStatus(
        online=False,
        system="Unknown",
        method="none",
        detail=f"Система {platform.system()} не поддерживается",
        adapters=[],
    )


def set_online(enable: bool) -> ToggleResult:
    system = detect_system()
    if system == "Windows":
        return _windows_set(enable)
    if system == "Linux":
        return _linux_set(enable)
    if system == "Darwin":
        return _darwin_set(enable)
    return ToggleResult(
        ok=False,
        online=False,
        message=f"Система {platform.system()} не поддерживается.",
    )


def is_elevated() -> bool:
    system = detect_system()
    if system == "Windows":
        result = _run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole("
                "[Security.Principal.WindowsBuiltInRole]::Administrator)",
            ]
        )
        return result.stdout.strip().lower() == "true"
    try:
        return hasattr(os, "geteuid") and os.geteuid() == 0
    except Exception:
        return False
