"""
network_info.py — Phase 7: Local Network Information Module

Collects local hostname, IP, subnet mask, default gateway, and DNS servers.
Uses cross-platform approaches (socket + subprocess fallbacks).
"""

from __future__ import annotations

import platform
import re
import socket
import subprocess
from typing import Any, Dict, List, Optional


def run_network_info() -> Dict[str, Any]:
    """
    Gather local network configuration.

    Returns:
    {
        "hostname":        str,
        "local_ip":        str,
        "subnet_mask":     str | None,
        "default_gateway": str | None,
        "dns_servers":     list[str],
    }
    """
    hostname = socket.gethostname()
    local_ip = _get_local_ip()
    subnet_mask, gateway = _get_subnet_gateway()
    dns_servers = _get_dns_servers()

    return {
        "hostname":        hostname,
        "local_ip":        local_ip,
        "subnet_mask":     subnet_mask,
        "default_gateway": gateway,
        "dns_servers":     dns_servers,
    }


def _get_local_ip() -> str:
    """Best-effort local IP by connecting a UDP socket (no packet sent)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return socket.gethostbyname(socket.gethostname())


def _get_subnet_gateway() -> tuple[Optional[str], Optional[str]]:
    """Return (subnet_mask, default_gateway) from OS routing info."""
    system = platform.system().lower()
    subnet: Optional[str] = None
    gateway: Optional[str] = None

    try:
        if system == "windows":
            output = subprocess.check_output(
                ["ipconfig"], text=True, timeout=5
            )
            for line in output.splitlines():
                if "Subnet Mask" in line and not subnet:
                    m = re.search(r":\s*(\d{1,3}(?:\.\d{1,3}){3})", line)
                    if m:
                        subnet = m.group(1)
                if "Default Gateway" in line and not gateway:
                    m = re.search(r":\s*(\d{1,3}(?:\.\d{1,3}){3})", line)
                    if m:
                        gateway = m.group(1)
        else:
            # Linux / macOS
            output = subprocess.check_output(["ip", "route"], text=True, timeout=5)
            m = re.search(r"default via (\d{1,3}(?:\.\d{1,3}){3})", output)
            if m:
                gateway = m.group(1)
            # subnet from ip addr
            addr_out = subprocess.check_output(["ip", "addr"], text=True, timeout=5)
            m = re.search(r"inet (\d{1,3}(?:\.\d{1,3}){3})/(\d+)", addr_out)
            if m:
                prefix = int(m.group(2))
                subnet = _cidr_to_mask(prefix)
    except Exception:
        pass

    return subnet, gateway


def _get_dns_servers() -> List[str]:
    """Read DNS server IPs from the OS resolver configuration."""
    system = platform.system().lower()
    servers: List[str] = []

    try:
        if system == "windows":
            output = subprocess.check_output(
                ["ipconfig", "/all"], text=True, timeout=5
            )
            for line in output.splitlines():
                if "DNS Servers" in line or (servers and re.match(r"^\s+\d", line)):
                    m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", line)
                    if m and m.group(1) not in servers:
                        servers.append(m.group(1))
        else:
            with open("/etc/resolv.conf") as f:
                for line in f:
                    if line.startswith("nameserver"):
                        ip = line.split()[1]
                        if ip not in servers:
                            servers.append(ip)
    except Exception:
        pass

    return servers or ["(unavailable)"]


def _cidr_to_mask(prefix: int) -> str:
    """Convert CIDR prefix length to dotted-decimal subnet mask."""
    bits = (0xFFFFFFFF >> (32 - prefix)) << (32 - prefix)
    return ".".join(str((bits >> (8 * i)) & 0xFF) for i in reversed(range(4)))
