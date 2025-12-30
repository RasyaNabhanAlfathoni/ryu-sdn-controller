#!/usr/bin/env python3
"""
Agent auto-register script for Ryu Controller northbound /devices.
"""

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
import datetime

CONTROLLER_URL = os.environ.get("RYU_CONTROLLER_URL", "http://127.0.0.1:8080")
API_KEY = os.environ.get("RYU_API_KEY", "agent-secret-token-1")
REGISTER_ENDPOINT = "/devices"
HEARTBEAT_ENDPOINT = "/devices/{device_id}/heartbeat"
AGENT_IP = os.environ.get("AGENT_IP", "127.0.0.1")
RETRY_INTERVAL = 5
MAX_RETRIES = 12
HEARTBEAT_INTERVAL = 10

def find_best_ip(controller_url):
    """Cari IP dan interface terbaik - return (ip, interface)"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(controller_url)
        controller_host = parsed.hostname

        # Method 1: Try socket connection untuk detect source IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((controller_host, 80))
            local_ip = s.getsockname()[0]
            s.close()

            if local_ip and not local_ip.startswith("127."):
                # Cari interface untuk IP ini
                for iface in netifaces.interfaces():
                    addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
                    for addr in addrs:
                        if addr.get('addr') == local_ip:
                            return local_ip, iface
        except Exception:
            pass

        # Method 2: Cari melalui gateway
        gateways = netifaces.gateways()
        default_gateway = gateways.get('default', {})

        if socket.AF_INET in default_gateway:
            gateway_info = default_gateway[socket.AF_INET]
            
            # Handle different gateway info formats
            if isinstance(gateway_info, tuple):
                gateway_ip, interface, is_default = gateway_info
            elif isinstance(gateway_info, list):
                gateway_ip, interface, is_default = gateway_info[0]
            else:
                interface = None
                
            if interface:
                addrs = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
                for addr in addrs:
                    ip = addr.get('addr')
                    if ip and not ip.startswith("127."):
                        return ip, interface
                        
    except Exception as e:
        print(f"[AGENT] Route-based IP detection failed: {e}")

    # Method 3: Fallback - first non-loopback interface
    for iface in netifaces.interfaces():
        if iface.startswith(('lo', 'docker', 'br-', 'virbr')):
            continue
        addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
        for addr in addrs:
            ip = addr.get("addr")
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip, iface

    # Ultimate fallback
    return "127.0.0.1", "lo"

def get_main_interface_info(controller_url):
    # Get main interface, IP, dan MAC address yang terhubung ke controller
    main_ip, main_interface = find_best_ip(controller_url)
    
    # Get MAC address untuk main interface
    main_mac = "unknown"
    try:
        addrs = netifaces.ifaddresses(main_interface)
        if netifaces.AF_LINK in addrs:
            main_mac = addrs[netifaces.AF_LINK][0].get('addr', 'unknown')
    except Exception as e:
        print(f"[AGENT] Cannot get MAC for {main_interface}: {e}")
    
    return main_ip, main_interface, main_mac

def get_architecture():
    # Get system architecture detail
    try:
        arch = platform.machine()
        bits = 64 if '64' in platform.architecture()[0] else 32
        
        # More detailed architecture info
        arch_details = {
            "architecture": arch,
            "bits": bits,
            "processor_type": get_processor_info()
        }
        
        return arch_details
    except Exception as e:
        print(f"[AGENT] Error getting architecture: {e}")
        return {"architecture": "unknown", "bits": 0, "processor_type": "unknown"}

def get_processor_info():
    """Get processor information from host"""
    try:
        # Try to read from host proc if mounted
        if os.path.exists("/host/proc/cpuinfo"):
            with open("/host/proc/cpuinfo", "r") as f:
                content = f.read()
                # Extract processor model
                for line in content.splitlines():
                    if "model name" in line.lower():
                        return line.split(":")[1].strip()
        
        # Fallback to container cpuinfo
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r") as f:
                content = f.read()
                for line in content.splitlines():
                    if "model name" in line.lower():
                        return line.split(":")[1].strip()
        
        # Try lscpu command
        result = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "model name" in line.lower():
                    return line.split(":")[1].strip()
        
        return platform.processor() or "Unknown"
        
    except Exception as e:
        print(f"[AGENT] Error getting processor info: {e}")
        return platform.processor() or "Unknown"

def detect_virtualization():
    # Detect virtualization platform
    try:
        # Check if we're in a container first
        if os.path.exists("/.dockerenv"):
            container_type = "docker"
        elif os.path.exists("/run/.containerenv"):
            container_type = "podman"
        else:
            container_type = None

        # Check virtual devices first (more reliable for some hypervisors)
        virtual_devices = {
            # VMware
            "/dev/vmmon": "vmware",
            "/dev/vmci": "vmware", 
            "/dev/vmware": "vmware",
            "/proc/vmware": "vmware",
            
            # VirtualBox
            "/dev/vboxguest": "virtualbox",
            "/dev/vboxuser": "virtualbox",
            "/proc/vbox": "virtualbox",
            
            # Xen
            "/dev/xen": "xen",
            "/proc/xen": "xen",
            "/sys/hypervisor/uuid": "xen",
            "/proc/xen/capabilities": "xen",
            
            # Hyper-V
            "/sys/bus/vmbus": "hyperv",
            "/sys/class/hv_util": "hyperv",
            "/sys/class/hv_vmbus": "hyperv",
            "/sys/class/uio/uio_hv_util": "hyperv",
            
            # KVM/QEMU
            "/dev/kvm": "kvm",
            "/dev/rtc": "qemu",
            "/dev/ppdev": "qemu",
            
            # Parallels
            "/dev/prl_fs": "parallels",
            "/dev/prl_frozen": "parallels",
            "/dev/prl_tg": "parallels",
            
            # Virtuozzo/OpenVZ
            "/proc/vz": "virtuozzo",
            "/proc/bc": "virtuozzo",
            
            # LXC/LXD
            "/proc/1/environ": "lxc",  # Might contain lxc info
            
            # Docker (though we already check containers above)
            "/.dockerinit": "docker",
            
            # User-mode Linux
            "/proc/mm": "uml",
            
            # IBM PowerVM
            "/proc/ppc64/lparcfg": "powervm",
            "/proc/device-tree/rtas/ibm,hypertas-functions": "powervm",
            
            # IBM z/VM
            "/proc/sysinfo": "zvm",
        }
        
        for device, hypervisor in virtual_devices.items():
            if os.path.exists(device):
                return {
                    "type": "virtual",
                    "hypervisor": hypervisor,
                    "container": container_type
                }

        # Try to detect underlying hypervisor from host
        if os.path.exists("/sys/class/dmi/id/product_name"):
            with open("/sys/class/dmi/id/product_name", "r") as f:
                product_name = f.read().strip().lower()
                
                if "vmware" in product_name:
                    return {
                        "type": "virtual",
                        "hypervisor": "vmware",
                        "container": container_type
                    }
                elif "virtualbox" in product_name:
                    return {
                        "type": "virtual", 
                        "hypervisor": "virtualbox",
                        "container": container_type
                    }
                elif "kvm" in product_name:
                    return {
                        "type": "virtual",
                        "hypervisor": "kvm", 
                        "container": container_type
                    }
                elif "qemu" in product_name:
                    return {
                        "type": "virtual",
                        "hypervisor": "qemu",
                        "container": container_type
                    }
                elif "hyper-v" in product_name:
                    return {
                        "type": "virtual",
                        "hypervisor": "hyperv",
                        "container": container_type
                    }
                elif "proxmox" in product_name:
                    return {
                        "type": "virtual",
                        "hypervisor": "proxmox",
                        "container": container_type
                    }

        # Check CPU flags for virtualization
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r") as f:
                content = f.read()
                if "hypervisor" in content.lower():
                    return {
                        "type": "virtual",
                        "hypervisor": "unknown_hypervisor",
                        "container": container_type
                    }

        # Check systemd-detect-virt for additional info
        try:
            result = subprocess.run(
                ["systemd-detect-virt"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                virt = result.stdout.strip()
                if virt != "none":
                    return {
                        "type": "virtual",
                        "hypervisor": virt,
                        "container": container_type
                    }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # If no virtualization detected
        return {
            "type": "physical",
            "hypervisor": "none",
            "container": container_type
        }
        
    except Exception as e:
        print(f"[AGENT] Error detecting virtualization: {e}")
        return {
            "type": "unknown",
            "hypervisor": "unknown", 
            "container": None
        }

def get_hardware_vendor():
    # Detect hardware vendor atau virtualization platform"""
    try:
        # Try to read from host DMI if mounted
        if os.path.exists("/sys/class/dmi/id/sys_vendor"):
            with open("/sys/class/dmi/id/sys_vendor", "r") as f:
                vendor = f.read().strip()
                if vendor and vendor not in ["", "Not Specified"]:
                    return vendor

        # Try dmidecode
        try:
            result = subprocess.run(
                ["dmidecode", "-s", "system-manufacturer"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                vendor = result.stdout.strip()
                if vendor not in ["", "Not Specified", "Default string"]:
                    return vendor
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass

        # Try lshw
        try:
            result = subprocess.run(
                ["lshw", "-class", "system", "-quiet"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "vendor:" in line.lower() and ":" in line:
                        vendor = line.split(":")[1].strip()
                        if vendor and vendor not in ["", "Not Specified"]:
                            return vendor
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass

        return "Unknown"
        
    except Exception as e:
        print(f"[AGENT] Error detecting hardware vendor: {e}")
        return "Unknown"

def get_mac_address():
    # Get MAC address
    macs = {}
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_LINK in addrs:
            mac = addrs[netifaces.AF_LINK][0].get('addr', 'unknown')
            macs[iface] = mac
    return macs

def get_os_info():
    # Get detailed OS information compatible dengan berbagai distro
    try:
        # Coba baca dari /etc/os-release (standard across distros)
        with open("/etc/host-os-release") as f:
            os_release = {}
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os_release[key] = value.strip('"')
            
            name = os_release.get('NAME', 'Unknown')
            version = os_release.get('VERSION', '')
            pretty_name = os_release.get('PRETTY_NAME', f"{name} {version}")
            
            return pretty_name
            
    except Exception:
        pass

    # Try host LSB release
    try:
        with open("/etc/host-lsb-release") as f:
            lsb_release = {}
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    lsb_release[key] = value.strip('"')
            
            description = lsb_release.get('DISTRIB_DESCRIPTION', '')  
            return description
    except Exception:
        pass
    
    # Try Fallback to container OS (with warning)
    try:
        with open("/etc/os-release") as f:
            os_release = {}
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os_release[key] = value.strip('"')
            
            name = os_release.get('NAME', 'Unknown')
            version = os_release.get('VERSION', '')
            pretty_name = os_release.get('PRETTY_NAME', f"{name} {version}")
            
            print(f"[AGENT] WARNING: Using container OS: {pretty_name}")
            return f"{pretty_name}"
    except Exception:
        pass

    # Final fallback
    try:
        return f"{platform.system()} {platform.release()}"
    except Exception:
        return "UnknownOS"
    
def get_os_family():
    # Detect OS family untuk compatibility checking
    try:
        with open("/etc/os-release") as f:
            content = f.read().lower()
            if 'ubuntu' in content or 'debian' in content:
                return 'debian'
            elif 'centos' in content or 'rhel' in content or 'redhat' in content:
                return 'rhel'
            elif 'fedora' in content:
                return 'fedora'
            elif 'suse' in content or 'opensuse' in content:
                return 'suse'
            elif 'arch' in content:
                return 'arch'
    except Exception:
        pass    
    return 'unknown'
    
def build_payload(controller_url):
    hostname = socket.gethostname()
    username = getpass.getuser()

    # Get main connection info
    main_ip, main_interface, main_mac = get_main_interface_info(controller_url)
    architecture = get_architecture()
    vendor = get_hardware_vendor()

    print(f"[AGENT] Using IP: {main_ip} for registration")

    payload = {
        "hostname": hostname,
        "main_ip_address": main_ip,
        "main_interface": main_interface,
        "main_mac_address": main_mac,
        "southbound": "server_api",
        "status": "active",
        "main_username": username,
        "os": get_os_info(),
        "architecture": architecture["architecture"],
        "architecture_bits": architecture["bits"],
        "processor_type": architecture["processor_type"],
        "vendor": vendor,
        "last_seen": datetime.datetime.now().isoformat(),
        "meta": {
            "virtualization": detect_virtualization(),
        }
    }

    # Tambahkan firewall info jika berhasil didapat
    interface_details = get_interface_details()
    if interface_details:
        payload["interfaces"] = interface_details
    
    # Tambahkan firewall info jika berhasil didapat
    firewall_info = get_firewall_info_safe()
    if firewall_info:
        payload["firewall"] = firewall_info
        
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

        # Interface status (up/down)
        details['status'] = get_interface_status(iface)

        interface_details[iface] = details

    return interface_details

def get_interface_status(iface):
    """Check if interface is up or down"""
    try:
        # Method 1: Check via sysfs
        operstate_path = f"/sys/class/net/{iface}/operstate"
        if os.path.exists(operstate_path):
            with open(operstate_path, 'r') as f:
                status = f.read().strip().lower()
                if status == 'up':
                    return 'up'
                else:
                    return 'down'
        
        # Method 2: Check via ip command
        import subprocess
        result = subprocess.run(['ip', 'link', 'show', iface], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout.lower()
            if 'state up' in output or '<up>' in output:
                return 'up'
            elif 'state down' in output or '<down>' in output:
                return 'down'
        
        return 'unknown'
    except Exception as e:
        print(f"[AGENT] Error getting interface status for {iface}: {e}")
        return 'unknown'

def get_firewall_info_safe():
    """Get firewall info safely - don't crash registration if fails"""
    try:
       
        # Import firewall module
        from drivers.linux.firewall import ServerFirewallDriver
        
        # Create firewall driver
        firewall_driver = ServerFirewallDriver(logger=lambda msg: print(f"[FIREWALL] {msg}"))
        
        # Get firewall info
        info = {
            "firewall_type": firewall_driver.firewall_type,
            "status": firewall_driver.get_status(),
            "default_zone": firewall_driver.get_default_zone(),
            "active_zones": firewall_driver.get_active_zones(),
            "rules_count": firewall_driver.get_rules_count(),
            "last_checked": datetime.datetime.now().isoformat()
        }
        
        print(f"[AGENT] Firewall info collected: {info['firewall_type']} ({info['status']})")
        return info
        
    except Exception as e:
        print(f"[AGENT] Warning: Could not collect firewall info: {e}")
        return None

def register_once():
    url = CONTROLLER_URL.rstrip('/') + REGISTER_ENDPOINT
    headers = {"Content-Type": "application/json", "X-API-KEY": API_KEY}

    # Pass controller URL untuk IP detection
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
            # Bangun payload dengan data terkini
            payload = {
                "hostname": socket.gethostname(),
                "main_ip_address": get_main_interface_info(CONTROLLER_URL)[0],
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            r = requests.post(url, headers=headers, json=payload, timeout=6)
            
            if r.status_code == 404:
                # Device tidak ditemukan, coba register ulang
                print(f"[AGENT] Device {device_id} not found, re-registering...")
                register_once()
            elif r.status_code != 200:
                print(f"[AGENT] Heartbeat HTTP {r.status_code}: {r.text}")
                
        except Exception as e:
            print("[AGENT] Heartbeat error:", e)
        
        time.sleep(HEARTBEAT_INTERVAL)

def start_periodic_refresh(device_id):
    """Background thread untuk periodic refresh"""
    import threading
    import random
    
    def refresh_worker():
        # Initial random delay
        time.sleep(random.randint(60, 300))  # 1-5 menit
        
        while True:
            try:
                # Simple refresh dengan data terkini
                payload = build_payload(CONTROLLER_URL)
                url = CONTROLLER_URL.rstrip('/') + REGISTER_ENDPOINT
                headers = {"Content-Type": "application/json", "X-API-KEY": API_KEY}
                
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                
                if response.status_code in (200, 201):
                    print(f"[AGENT-AUTO] Refreshed data to controller")
                else:
                    print(f"[AGENT-AUTO] Refresh failed: {response.status_code}")
                
                # Refresh setiap 10 menit
                time.sleep(600)
                
            except Exception as e:
                print(f"[AGENT-AUTO-ERROR] {e}")
                time.sleep(60)
    
    # Start thread
    thread = threading.Thread(target=refresh_worker, daemon=True)
    thread.start()
    print(f"[AGENT-AUTO] Started periodic refresh for {device_id}")

def main():
    print(f"[AGENT] Starting registration to {CONTROLLER_URL}")

    # Retry registration
    dev = None
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[AGENT] Registration attempt {attempt}/{MAX_RETRIES}")
        dev = register_once()
        if dev:
            break
        time.sleep(RETRY_INTERVAL)

    if not dev:
        print("[AGENT] Could not register. Exiting.")
        sys.exit(1)

    device_id = dev.get("id") or dev.get("device_id")
    
    if device_id:
        # Start heartbeat
        t = threading.Thread(target=heartbeat_loop, args=(device_id,), daemon=True)
        t.start()
        
        # Start auto-refresh (OPTIONAL)
        start_periodic_refresh(device_id)

    # Keep running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("[AGENT] Stopped")

if __name__ == "__main__":
    main()
