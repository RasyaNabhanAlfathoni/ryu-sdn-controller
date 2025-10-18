#!/usr/bin/env python3
# Script untuk automasi registrasi agent devices server pada Ryu Controller 

import os
import time
import socket
import netifaces
import requests
import json
import sys
import threading
import getpass
import uuid
import platform
import subprocess

CONTROLLER_URL = os.environ.get("RYU_CONTROLLER_URL", "http://192.168.221.133:8080")
API_KEY = os.environ.get("RYU_API_KEY", "agent-secret-token-1")
REGISTER_ENDPOINT = "/devices"
HEARTBEAT_ENDPOINT = "/devices/{device_id}/heartbeat"
AGENT_IP = os.environ.get("AGENT_IP")
RETRY_INTERVAL = 5
MAX_RETRIES = 12
HEARTBEAT_INTERVAL = 10

# Test apakah ada process ryu manager
def is_ryu_controller_running():
    """Check if Ryu controller is running on this machine"""
    try:
        # Cek process Ryu
        result = subprocess.run(['pgrep', '-f', 'ryu-manager'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            return True

        # Cek port 8080 (Ryu API)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 8080))
        sock.close()
        return result == 0

    except Exception:
        return False

# Jika ada process ryu manager, maka role adalah "manager" jika tidak "agent"
def detect_role():
    """Auto-detect role: manager or agent"""
    if is_ryu_controller_running():
        return "manager"
    else:
        return "agent"

def get_connected_ip(controller_url):
    # Dapatkan IP yang sebenarnya digunakan untuk koneksi ke controller
    try:
        # Extract hostname dari controller URL
        from urllib.parse import urlparse
        parsed = urlparse(controller_url)
        controller_host = parsed.hostname

        # Buat koneksi socket untuk melihat source IP yang digunakan
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((controller_host, 80))  # Port tidak penting, yang penting connect
        local_ip = s.getsockname()[0]
        s.close()

        # Jangan gunakan localhost IP
        if local_ip and not local_ip.startswith("127."):
            return local_ip

    except Exception as e:
        print(f"[AGENT] Cannot detect connected IP: {e}")

    # Fallback: cari IP dari interface yang terhubung ke network
    return find_best_ip(controller_host)

def find_best_ip(controller_host):
    # Cari IP terbaik berdasarkan routing ke controller
    try:
        # Resolve controller IP untuk mengetahui network destination
        controller_ip = socket.gethostbyname(controller_host)

        # Cari interface yang memiliki route ke controller
        gateways = netifaces.gateways()
        default_gateway = gateways.get('default', {})

        for family, (gateway_ip, interface, _) in default_gateway.items():
            if family == socket.AF_INET:
                addrs = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
                for addr in addrs:
                    ip = addr.get('addr')
                    if ip and not ip.startswith("127."):
                        return ip
    except Exception as e:
        print(f"[AGENT] Route-based IP detection failed: {e}")

    # Final fallback: ambil IP non-local pertama
    for iface in netifaces.interfaces():
        if iface.startswith(('lo', 'docker', 'br-', 'virbr')):
            continue
        addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
        for addr in addrs:
            ip = addr.get("addr")
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip

    return "127.0.0.1"  # Ultimate fallback

def get_mac_address():
    # Get physical MAC address
    macs = {}
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_LINK in addrs:
            mac = addrs[netifaces.AF_LINK][0].get('addr', 'unknown')
            macs[iface] = mac
    return macs

def get_os_info():
    # Get operating system info
    try:
        # Coba baca dari /etc/os-release
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=")[1].strip().strip('"')
    except Exception:
        pass

    # Fallback ke platform
    try:
        return platform.system()
    except Exception:
        return "UnknownOS"

def build_payload(controller_url):
    hostname = socket.gethostname()

    # Gunakan IP yang terhubung ke controller, bukan interface pertama
    ip = get_connected_ip(controller_url)

    print(f"[AGENT] Using IP: {ip} for registration")

    payload = {
        "role": detect_role(), # panggil fungsi deteksi role otomatis
        "ip": ip, # info IP
        "username": getpass.getuser(), # info user
        "southbound": "server_api",  # lebih deskriptif
        "os": get_os_info(),         # info OS
        "meta": {
            "hostname": hostname, # info Hostname server
            "interfaces": netifaces.interfaces(), # info interface
            "detected_ips": get_all_ips(),  # Untuk debugging
            "interface_details": get_interface_details()  # Detail lengkap dengan MAC atau bisa juga pakai get_mac_address()
        }
    }
    return payload

def get_interface_details():
    # Get detailed interface information including MAC addresses
    interface_details = {}

    for iface in netifaces.interfaces():
        details = {}
        addrs = netifaces.ifaddresses(iface)

        # MAC Address (AF_LINK)
        if netifaces.AF_LINK in addrs:
            mac_info = addrs[netifaces.AF_LINK][0]
            details['mac_address'] = mac_info.get('addr', 'unknown')
            details['mac_broadcast'] = mac_info.get('broadcast', 'unknown')

        # IPv4 Addresses
        if netifaces.AF_INET in addrs:
            ipv4_addresses = []
            for addr in addrs[netifaces.AF_INET]:
                ip_info = {
                    'address': addr.get('addr', 'unknown'),
                    'netmask': addr.get('netmask', 'unknown'),
                    'broadcast': addr.get('broadcast', 'unknown')
                }
                ipv4_addresses.append(ip_info)
            details['ipv4'] = ipv4_addresses

        # IPv6 Addresses (optional)
        if netifaces.AF_INET6 in addrs:
            ipv6_addresses = []
            for addr in addrs[netifaces.AF_INET6]:
                ipv6_info = {
                    'address': addr.get('addr', 'unknown'),
                    'netmask': addr.get('netmask', 'unknown')
                }
                ipv6_addresses.append(ipv6_info)
            details['ipv6'] = ipv6_addresses

        interface_details[iface] = details

    return interface_details

def get_all_ips():
    # Get all IP addresses for debugging
    ips = {}
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        ipv4 = addrs.get(netifaces.AF_INET, [])
        if ipv4:
            ips[iface] = [addr['addr'] for addr in ipv4]
    return ips

def register_once():
    url = CONTROLLER_URL.rstrip('/') + REGISTER_ENDPOINT
    headers = {"Content-Type": "application/json", "X-API-KEY": API_KEY}

    # FIX: Pass controller URL untuk IP detection
    payload = build_payload(CONTROLLER_URL)

    print(f"[AGENT] Registering with payload: {json.dumps(payload, indent=2)}")

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=8)
    except Exception as e:
        print(f"[AGENT] Register request failed: {e}")
        return None

    if r.status_code not in (200, 201):
        print(f"[AGENT] Register HTTP {r.status_code}: {r.text}")
        return None

    try:
        data = r.json()
    except Exception as e:
        print("[AGENT] Invalid JSON response:", e, r.text)
        return None

    if data.get("status") != "ok":
        print("[AGENT] Controller error:", data)
        return None

    dev = data.get("device")
    print(f"[AGENT] Registered successfully. Device ID: {dev.get('id')}, IP: {dev.get('ip')}")
    return dev

def heartbeat_loop(device_id):
    url = CONTROLLER_URL.rstrip('/') + HEARTBEAT_ENDPOINT.format(device_id=device_id)
    headers = {"X-API-KEY": API_KEY}
    while True:
        try:
            r = requests.post(url, headers=headers, timeout=6)
            if r.status_code != 200:
                print(f"[AGENT] Heartbeat HTTP {r.status_code}: {r.text}")
        except Exception as e:
            print("[AGENT] Heartbeat error:", e)
        time.sleep(HEARTBEAT_INTERVAL)

def main():
    print(f"[AGENT] Starting registration to {CONTROLLER_URL}")

    # Retry registration
    dev = None
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[AGENT] Registration attempt {attempt}/{MAX_RETRIES}")
        dev = register_once()
        if dev:
            break
        print(f"[AGENT] Retry register in {RETRY_INTERVAL}s")
        time.sleep(RETRY_INTERVAL)

    if not dev:
        print("[AGENT] Could not register to controller after retries. Exiting.")
        sys.exit(1)

    device_id = dev.get("id")
    if device_id:
        print(f"[AGENT] Starting heartbeat for device {device_id}")
        t = threading.Thread(target=heartbeat_loop, args=(device_id,), daemon=True)
        t.start()

    # Keep running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("[AGENT] Stopped by user")

if __name__ == "__main__":
    main()
