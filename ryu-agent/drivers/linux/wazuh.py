import os
import subprocess
import requests
import tempfile
import platform
import re
from typing import Dict, List, Optional

class WazuhDriver:
    def __init__(self, logger=print):
        self.logger = logger
        self.host_root = "/host-rootfs"

    def _execute_on_host(self, command: str) -> Dict:
        """Execute command on Host system (not container)"""
        try:
            if not os.path.exists("/host-rootfs/bin/sh"):
                return {"success": False, "error": "host-rootfs not mounted properly"}

            # Execute command on host via chroot
            host_command = f"chroot /host-rootfs /bin/bash -c \"{command}\""
            
            self.logger(f"Executing on Host: {command}")
            result = subprocess.run(
                host_command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=300
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "exit_code": result.returncode
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def detect_package_manager(self) -> str:
        """Detect package manager yang tersedia"""
        package_managers = {
            'apt': ['apt', 'apt-get'],
            'yum': ['yum', 'dnf'], 
            'zypper': ['zypper'],
            'pacman': ['pacman'],
            'apk': ['apk']
        }
        
        for pm, commands in package_managers.items():
            for cmd in commands:
                result = self._execute_on_host(f"which {cmd}")
                if result["success"]:
                    self.logger(f"Detected package manager on Host: {pm} ({cmd})")
                    return pm
        
        return "unknown"
    
    def detect_architecture(self) -> str:
        """Detect system architecture"""
        result = self._execute_on_host("uname -m")
        arch = result.get("output", "").strip().lower() if result["success"] else "unknown"
        
        arch_map = {
            'x86_64': 'x86_64',
            'amd64': 'x86_64', 
            'i386': 'i386',
            'i686': 'i386',
            'aarch64': 'aarch64',
            'arm64': 'aarch64',
            'armv7l': 'armhf',
            'armv6l': 'armhf'
        }
        
        detected_arch = arch_map.get(arch, 'x86_64')  # Default ke x86_64
        self.logger(f"Detected Host architecture: {arch} -> {detected_arch}")
        return detected_arch
    
    def detect_os_family(self) -> dict:
        """Detect OS family dan version"""
        try:
            # Read host's os-release
            with open(f'{self.host_root}/etc/os-release', 'r') as f:
                os_info = {}
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        os_info[key] = value.strip('"')
                
                name = os_info.get('NAME', '').lower()
                version_id = os_info.get('VERSION_ID', '')
                
                if 'ubuntu' in name:
                    return {'family': 'ubuntu', 'version': version_id}
                elif 'debian' in name:
                    return {'family': 'debian', 'version': version_id}
                elif 'centos' in name:
                    return {'family': 'centos', 'version': version_id}
                elif 'rhel' in name or 'red hat' in name:
                    return {'family': 'rhel', 'version': version_id}
                elif 'fedora' in name:
                    return {'family': 'fedora', 'version': version_id}
                elif 'suse' in name or 'opensuse' in name:
                    return {'family': 'suse', 'version': version_id}
        
        except Exception as e:
            self.logger(f"Error detecting HOST OS: {e}")
        
        return {'family': 'unknown', 'version': 'unknown'}
    
    def get_wazuh_package_url(self, os_family: str, architecture: str, wazuh_version: str = "4.11.2") -> str:
        """Generate Wazuh package URL berdasarkan OS dan architecture"""
        base_url = "https://packages.wazuh.com/4.x"
        
        package_urls = {
            'debian': {
                'x86_64': f"{base_url}/apt/pool/main/w/wazuh-agent/wazuh-agent_{wazuh_version}-1_amd64.deb",
                'aarch64': f"{base_url}/apt/pool/main/w/wazuh-agent/wazuh-agent_{wazuh_version}-1_arm64.deb",
                'armhf': f"{base_url}/apt/pool/main/w/wazuh-agent/wazuh-agent_{wazuh_version}-1_armhf.deb"
            },
            'rhel': {
                'x86_64': f"{base_url}/yum/wazuh-agent-{wazuh_version}-1.x86_64.rpm",
                'aarch64': f"{base_url}/yum/wazuh-agent-{wazuh_version}-1.aarch64.rpm",
                'i386': f"{base_url}/yum/wazuh-agent-{wazuh_version}-1.i386.rpm"
            },
            'fedora': {
                'x86_64': f"{base_url}/yum/wazuh-agent-{wazuh_version}-1.x86_64.rpm",
                'aarch64': f"{base_url}/yum/wazuh-agent-{wazuh_version}-1.aarch64.rpm"
            },
            'suse': {
                'x86_64': f"{base_url}/yum/wazuh-agent-{wazuh_version}-1.x86_64.rpm",
                'aarch64': f"{base_url}/yum/wazuh-agent-{wazuh_version}-1.aarch64.rpm"
            }
        }
        
        # Default ke Debian/x86_64 jika tidak ditemukan
        url = package_urls.get(os_family, {}).get(architecture)
        if not url:
            url = package_urls['debian']['x86_64']  # Fallback
        
        self.logger(f"Generated package URL: {url}")
        return url
    
    def get_install_commands(self, package_url: str, package_manager: str, manager_ip: str) -> list:
        """Generate install commands berdasarkan package manager"""
        filename = os.path.basename(package_url)
        
        commands = []
        
        # Download command (cek di HOST, bukan container)
        curl_check = self._execute_on_host("command -v curl")
        wget_check = self._execute_on_host("command -v wget")

        if curl_check["success"] and curl_check.get("output"):
            commands.append(f"curl -o {filename} {package_url}")
        elif wget_check["success"] and wget_check.get("output"):
            commands.append(f"wget -O {filename} {package_url}")
        else:
            return {"success": False, "error": "Host has neither curl nor wget installed!"}
        
        # Install commands berdasarkan package manager
        install_commands = {
            'apt': [
                f"WAZUH_MANAGER='{manager_ip}' dpkg -i ./{filename}",
            ],
            'yum': [
                f"WAZUH_MANAGER='{manager_ip}' rpm -ihv {filename}",
            ],
            'dnf': [
                f"WAZUH_MANAGER='{manager_ip}' dnf install -y {filename}",
            ],
            'zypper': [
                f"WAZUH_MANAGER='{manager_ip}' zypper install -y {filename}",
            ]
        }
        
        commands.extend(install_commands.get(package_manager, install_commands['apt']))  # Fallback ke apt
        
        # Cleanup
        commands.append(f"rm -f {filename}")
        
        return commands
        
    def detect_host_capabilities(self) -> dict:
        """Detect capabilities of the Host system before performing operations."""
        capabilities = {}

        # Check host-rootfs existence
        capabilities["host_root_mounted"] = os.path.exists("/host-rootfs")

        # Check systemctl (systemd)
        capabilities["systemd"] = (
            os.path.exists(f"{self.host_root}/bin/systemctl") or
            os.path.exists(f"{self.host_root}/usr/bin/systemctl") or
            os.path.exists(f"{self.host_root}/usr/sbin/systemctl")
        )

        # Check SysV init
        res = self._execute_on_host("test -d /etc/init.d && echo ok")
        capabilities["sysvinit"] = res["success"]

        # Check netplan
        capabilities["netplan"] = os.path.isdir(f"{self.host_root}/etc/netplan")

        # Check systemd-networkd
        capabilities["systemd_networkd"] = os.path.isdir(f"{self.host_root}/etc/systemd/network")

        # Check if legacy /etc/network exists (Debian/Ubuntu classic)
        capabilities["ifupdown"] = os.path.isdir(f"{self.host_root}/etc/network")

        # RHEL network-scripts
        capabilities["network_scripts"] = os.path.isdir(f"{self.host_root}/etc/sysconfig/network-scripts")

        # curl & wget available?
        capabilities["curl"] = (
            os.path.exists(f"{self.host_root}/usr/bin/curl") or
            os.path.exists(f"{self.host_root}/bin/curl")
        )

        capabilities["wget"] = (
            os.path.exists(f"{self.host_root}/usr/bin/wget") or
            os.path.exists(f"{self.host_root}/bin/wget")
        )

        # chroot available?
        capabilities["chroot"] = os.path.exists("/usr/sbin/chroot") or os.path.exists("/bin/chroot")

        return capabilities

    def install_wazuh_agent(self, manager_ip: str, agent_key: str, agent_name: str = None, wazuh_version: str = "4.11.2") -> Dict:
        try:
            cap = self.detect_host_capabilities()
            self.logger(f"Host Capabilities: {cap}")

            if not cap["host_root_mounted"]:
                return {"success": False, "error": "host-rootfs is not mounted — cannot continue"}

            if not cap["curl"] and not cap["wget"]:
                return {"success": False, "error": "Host has neither curl nor wget installed!"}

            self.logger("Starting Wazuh agent installation...")

            # Check if installed
            result = self._execute_on_host("test -f /var/ossec/bin/wazuh-agentd")
            if "installed" in result.get("output", ""):
                self.logger("Wazuh already installed, reconfiguring...")
                key_result = self._register_agent_key(agent_key, agent_name)
                if key_result["success"]:
                    self._start_wazuh_agent_manual()
                    return {"success": True, "message": "Wazuh reconfigured on Host"}

            # Detect hostname
            if not agent_name:
                result = self._execute_on_host("hostname")
                agent_name = result.get("output", "").strip() or "unknown"

            # Detect system
            package_manager = self.detect_package_manager()
            architecture = self.detect_architecture()
            os_info = self.detect_os_family()

            self.logger(f"System info - Package Manager: {package_manager}, Arch: {architecture}, OS: {os_info}")

            # Get package URL
            package_url = self.get_wazuh_package_url(os_info['family'], architecture, wazuh_version)

            # Generate installation commands
            commands = self.get_install_commands(package_url, package_manager, manager_ip)

            # Execute installation commands
            self.logger("Executing installation commands on Host...")
            for cmd in commands:
                result = self._execute_on_host(f"cd /tmp && {cmd}")
                if not result["success"]:
                    return {"success": False, "error": f"Failed at '{cmd}', error: {result.get('error')}"}
                
            # Register agent key
            self.logger("Registering agent key on Host...")
            key_result = self._register_agent_key(agent_key, agent_name)
            if not key_result.get("success"):
                return {"success": False, "error": key_result["error"]}

            # Start wazuh-agent MANUAL (tanpa systemctl)
            self.logger("Starting Wazuh agent manually...")
            start_result = self._start_wazuh_agent_manual()

            # Final verification
            import time
            max_attempts = 5
            status = None

            for attempt in range(max_attempts):
                self.logger(f"Verification attempt {attempt + 1}/{max_attempts}...")
                status = self.get_wazuh_agent_status()
                
                if status.get("running") or status.get("process_count", 0) > 0:
                    self.logger(f"✓ Wazuh agent is running!")
                    break
                
                if attempt < max_attempts - 1:
                    time.sleep(2)  # Tunggu 2 detik sebelum cek lagi
            
            # Jika masih tidak running, coba sekali lagi dengan method berbeda
            if not status.get("running") and status.get("process_count", 0) == 0:
                self.logger("Agent not running, trying emergency start...")
                emergency_cmd = "chroot /host-rootfs /bin/bash -c 'cd /var/ossec && nohup ./bin/wazuh-agentd -d > /dev/null 2>&1 &'"
                subprocess.run(emergency_cmd, shell=True, timeout=10)
                time.sleep(3)
                status = self.get_wazuh_agent_status()

            return {
                "success": True,
                "message": "Wazuh agent installation completed",
                "agent_name": agent_name,
                "agent_id": key_result.get("agent_id", "unknown"),
                "agent_status": status,
                "service_running": status.get("running", False) or status.get("process_count", 0) > 0,
                "system_info": {
                    "package_manager": package_manager,
                    "architecture": architecture,
                    "os_family": os_info['family']
                }
            }

        except Exception as e:
            self.logger(f"Host installation failed: {str(e)}")
            return {"success": False, "error": f"Host installation failed: {str(e)}"}

    def _register_agent_key(self, agent_key: str, agent_name: str) -> Dict:
        """Register agent key dengan format yang benar"""
        try:
            # Debug log input
            self.logger(f"DEBUG: Raw agent_key input: '{agent_key}'")
            self.logger(f"DEBUG: Agent name: '{agent_name}'")
            
            # Parse agent key (format: "id name any hash")
            # Contoh: "066 server-wazuh any 69185e8b6a579bb43e17243e540569424f0c2c1e9d0ac51c032417ca15354425"
            key_parts = agent_key.strip().split()
            
            self.logger(f"DEBUG: Key parts ({len(key_parts)}): {key_parts}")
            
            if len(key_parts) != 4:
                return {
                    "success": False, 
                    "error": f"Invalid agent key format. Expected 4 parts, got {len(key_parts)}: {agent_key}"
                }
            
            agent_id = key_parts[0]      # "066"
            key_name = key_parts[1]      # "server-wazuh" 
            key_type = key_parts[2]      # "any"
            key_hash = key_parts[3]      # "69185e8b6a579bb43e17243e540569424f0c2c1e9d0ac51c032417ca15354425"
            
            # Format yang benar untuk client.keys
            key_content = f"{agent_id} {agent_name} {key_type} {key_hash}\n"
            
            self.logger(f"Writing client.keys: {key_content.strip()}")
            
            # Write to temporary file first
            temp_file = "/tmp/client.keys.tmp"
            write_temp = f"echo '{key_content.strip()}' > {temp_file}"
            temp_result = self._execute_on_host(write_temp)
            
            if not temp_result["success"]:
                return {"success": False, "error": f"Failed to write temp file: {temp_result.get('error')}"}
            
            # Copy to final location with proper permissions
            copy_cmd = f"mkdir -p /var/ossec/etc && cp {temp_file} /var/ossec/etc/client.keys && chmod 644 /var/ossec/etc/client.keys && chown root:wazuh /var/ossec/etc/client.keys"
            copy_result = self._execute_on_host(copy_cmd)
            
            # Cleanup
            self._execute_on_host(f"rm -f {temp_file}")
            
            if not copy_result["success"]:
                return {"success": False, "error": f"Failed to copy client.keys: {copy_result.get('error')}"}
            
            # Verify
            verify_cmd = "cat /var/ossec/etc/client.keys && echo '---' && wc -l /var/ossec/etc/client.keys"
            verify_result = self._execute_on_host(verify_cmd)
            
            self.logger(f"Verified client.keys: {verify_result.get('output', '').strip()}")
            
            return {
                "success": True, 
                "agent_id": agent_id,
                "key_written": key_content.strip()
            }
            
        except Exception as e:
            self.logger(f"Key registration error: {str(e)}")
            return {"success": False, "error": f"Key registration failed: {str(e)}"}
        
    def _start_wazuh_agent_manual(self) -> Dict:
        """Start wazuh-agent secara manual dengan debugging"""
        try:
            self.logger("Starting Wazuh agent manually...")
            
            # Cek dulu apakah wazuh-agent binary ada
            check_cmd = "chroot /host-rootfs /bin/bash -c 'test -f /var/ossec/bin/wazuh-agentd && echo \"EXISTS\" || echo \"NOT_FOUND\"'"
            check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            
            if "NOT_FOUND" in check_result.stdout:
                self.logger("ERROR: wazuh-agent binary not found!")
                return {"success": False, "error": "wazuh-agent binary not found"}
            
            self.logger("✓ wazuh-agent binary exists")
            
            # Cek apakah client.keys sudah ada
            check_keys = "chroot /host-rootfs /bin/bash -c 'test -f /var/ossec/etc/client.keys && echo \"KEYS_EXIST\" || echo \"NO_KEYS\"'"
            keys_result = subprocess.run(check_keys, shell=True, capture_output=True, text=True)
            
            if "NO_KEYS" in keys_result.stdout:
                self.logger("WARNING: client.keys not found yet")
            
            # Method 1: Coba start dengan wazuh-control
            self.logger("Trying wazuh-control...")
            method1 = "chroot /host-rootfs /bin/bash -c 'cd /var/ossec && ./bin/wazuh-control start'"
            result1 = subprocess.run(method1, shell=True, capture_output=True, text=True, timeout=15)
            
            self.logger(f"wazuh-control result: exit={result1.returncode}, stdout={result1.stdout[:100]}, stderr={result1.stderr[:100]}")
            
            if result1.returncode == 0:
                self.logger("✓ Started with wazuh-control")
                return {"success": True, "output": result1.stdout, "error": result1.stderr}
            
            # Method 2: Start binary langsung
            self.logger("Trying direct binary start...")
            method2 = "chroot /host-rootfs /bin/bash -c 'cd /var/ossec && ./bin/wazuh-agentd -d'"
            result2 = subprocess.run(method2, shell=True, capture_output=True, text=True, timeout=15)
            
            self.logger(f"Direct start result: exit={result2.returncode}, stdout={result2.stdout[:100]}, stderr={result2.stderr[:100]}")
            
            # Cek apakah process berjalan setelah start attempt
            check_process = "chroot /host-rootfs /bin/bash -c 'pgrep -f wazuh-agentd 2>/dev/null | wc -l'"
            process_check = subprocess.run(check_process, shell=True, capture_output=True, text=True)
            
            process_count = int(process_check.stdout.strip()) if process_check.stdout.strip().isdigit() else 0
            self.logger(f"Process count after start attempts: {process_count}")
            
            if process_count > 0:
                self.logger(f"✓ Wazuh agent is running ({process_count} processes)")
                return {"success": True, "output": f"Process running: {process_count}", "error": ""}
            
            # Method 3: Coba dengan init.d
            self.logger("Trying init.d script...")
            method3 = "chroot /host-rootfs /bin/bash -c '/etc/init.d/wazuh-agentd start'"
            result3 = subprocess.run(method3, shell=True, capture_output=True, text=True, timeout=15)
            
            self.logger(f"init.d result: exit={result3.returncode}, stdout={result3.stdout[:100]}, stderr={result3.stderr[:100]}")
            
            # Final process check
            final_check = "chroot /host-rootfs /bin/bash -c 'pgrep -f wazuh-agentd 2>/dev/null && echo \"RUNNING\" || echo \"NOT_RUNNING\"'"
            final_result = subprocess.run(final_check, shell=True, capture_output=True, text=True)
            
            if "RUNNING" in final_result.stdout:
                self.logger("✓ Wazuh agent is finally running")
                return {"success": True, "output": "Agent started successfully", "error": ""}
            
            self.logger("✗ All start methods failed")
            return {
                "success": False, 
                "error": f"All start methods failed. Last check: {final_result.stdout}",
                "output": f"wazuh-control: {result1.stderr}, direct: {result2.stderr}, init.d: {result3.stderr}"
            }
                
        except Exception as e:
            self.logger(f"Start error: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_wazuh_agent_status(self) -> Dict:
        """Get comprehensive Wazuh agent status - specifically check wazuh-agentd"""
        try:
            # FIX: Cari "wazuh-agentd" bukan "wazuh-agent"
            cmd = "chroot /host-rootfs /bin/bash -c 'pgrep -f \"wazuh-agentd\" 2>/dev/null | wc -l'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            agent_process_count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            
            # Juga cek dengan nama tanpa 'd' untuk kompatibilitas
            cmd2 = "chroot /host-rootfs /bin/bash -c 'pgrep -f \"wazuh-agent$\" 2>/dev/null | wc -l'"
            result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
            agent_process_count2 = int(result2.stdout.strip()) if result2.stdout.strip().isdigit() else 0
            
            # Gunakan yang terdeteksi
            total_agent_processes = agent_process_count + agent_process_count2
            
            # Get agent ID dari client.keys
            agent_id = "unknown"
            cmd = "chroot /host-rootfs /bin/bash -c 'cat /var/ossec/etc/client.keys 2>/dev/null | head -1 | cut -d\" \" -f1'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                agent_id = result.stdout.strip()
            
            # Cek process detail
            detailed_cmd = "chroot /host-rootfs /bin/bash -c 'ps aux | grep -E \"wazuh-agent[d]?\" | grep -v grep'"
            detailed_result = subprocess.run(detailed_cmd, shell=True, capture_output=True, text=True)
            agent_processes = detailed_result.stdout.strip().split('\n') if detailed_result.stdout else []
            
            return {
                "agent_running": total_agent_processes > 0,
                "agent_process_count": total_agent_processes,
                "agent_id": agent_id,
                "status": "active" if total_agent_processes > 0 else "inactive",
                "agent_processes": agent_processes,
                "note": f"Looking for wazuh-agentd processes, found {total_agent_processes}"
            }
            
        except Exception as e:
            return {
                "agent_running": False,
                "status": "error",
                "error": str(e)
            }
        
    def uninstall_wazuh_agent(self) -> Dict:
        """Wazuh agent uninstaller manual"""
        try:
            # Stop wazuh-agent dengan manual methods
            self.logger("Stopping Wazuh agent...")
            stop_methods = [
                "chroot /host-rootfs /bin/bash -c 'cd /var/ossec && ./bin/wazuh-control stop 2>/dev/null'",
                "chroot /host-rootfs /bin/bash -c '/etc/init.d/wazuh-agent stop 2>/dev/null'",
                "chroot /host-rootfs /bin/bash -c 'service wazuh-agent stop 2>/dev/null'",
                "chroot /host-rootfs /bin/bash -c 'pkill -f wazuh-agent 2>/dev/null'",
                "chroot /host-rootfs /bin/bash -c 'killall wazuh-agent 2>/dev/null'"
            ]
            
            for method in stop_methods:
                result = subprocess.run(method, shell=True, capture_output=True, text=True, timeout=15)
                if result.returncode == 0 or "stopped" in result.stdout.lower():
                    self.logger("Wazuh agent stopped")
                    break
            
            # Tunggu sebentar
            import time
            time.sleep(2)
            
            # Uninstall berdasarkan package manager
            package_manager = self.detect_package_manager()
            
            uninstall_commands = {
                'apt': "dpkg --purge wazuh-agent",
                'yum': "rpm -e wazuh-agent", 
                'dnf': "dnf remove -y wazuh-agent",
                'zypper': "zypper remove -y wazuh-agent"
            }
            
            cmd = uninstall_commands.get(package_manager, uninstall_commands['apt'])
            self.logger(f"Uninstalling with: {cmd}")
            
            result = self._execute_on_host(cmd)
            
            # Jika uninstall gagal (mungkin karena sudah di-uninstall), tetap lanjut cleanup
            if not result["success"]:
                self.logger(f"Uninstall command failed (may already be uninstalled): {result.get('error')}")
            
            # Cleanup files dan directories
            self.logger("Cleaning up Wazuh files...")
            cleanup_items = [
                # Directories
                "/var/ossec",
                "/etc/wazuh",
                "/usr/share/wazuh",
                "/var/lib/wazuh",
                # Files
                "/etc/init.d/wazuh-agent",
                "/usr/lib/systemd/system/wazuh-agent.service",
                "/etc/systemd/system/wazuh-agent.service",
                # Logs
                "/var/log/wazuh",
                # Config backup
                "/etc/wazuh-agent.conf.rpmsave",
                "/etc/wazuh-agent.conf.dpkg-old"
            ]
            
            for item in cleanup_items:
                cleanup_cmd = f"rm -rf {item} 2>/dev/null || true"
                self._execute_on_host(cleanup_cmd)
            
            # Juga hapus user/group jika ada
            cleanup_users = [
                "chroot /host-rootfs /bin/bash -c 'userdel wazuh 2>/dev/null || true'",
                "chroot /host-rootfs /bin/bash -c 'groupdel wazuh 2>/dev/null || true'"
            ]
            
            for cmd in cleanup_users:
                subprocess.run(cmd, shell=True, capture_output=True)
            
            # Verify uninstall
            verify_cmd = "chroot /host-rootfs /bin/bash -c 'test -f /var/ossec/bin/wazuh-agentd && echo \"still_exists\" || echo \"removed\"'"
            verify_result = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
            
            still_exists = "still_exists" in verify_result.stdout
            
            return {
                "success": not still_exists,
                "message": "Wazuh agent uninstallation completed" if not still_exists else "Wazuh agent may not be fully removed",
                "package_manager": package_manager,
                "files_removed": not still_exists,
                "verification": "removed" if not still_exists else "may_still_exist"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        
    def get_security_overview(self, agent_id: str) -> Dict:
        """Get security overview dari Wazuh manager"""
        if not self.wazuh_api:
            return {"status": "error", "error": "Wazuh API client not available"}
        
        try:
            self.logger(f"Getting security overview for agent {agent_id}...")
            
            # Use existing method dari wazuh_api
            result = self.wazuh_api.get_security_overview(agent_id)
            self.logger(f"Security overview retrieved for {agent_id}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to get security overview: {str(e)}"
            self.logger(f"{error_msg}")
            return {"status": "error", "error": error_msg}
    
    def get_vulnerabilities(self, agent_id: str, limit: int = 50) -> Dict:
        """Get vulnerabilities dari Wazuh manager"""
        if not self.wazuh_api:
            return {"status": "error", "error": "Wazuh API client not available"}
        
        try:
            self.logger(f"Getting vulnerabilities for agent {agent_id}...")
            
            vulnerabilities = self.wazuh_api.get_vulnerabilities(agent_id)
            result = {
                "status": "success",
                "agent_id": agent_id,
                "total_vulnerabilities": len(vulnerabilities),
                "vulnerabilities": vulnerabilities[:limit],
                "summary": {
                    "critical": len([v for v in vulnerabilities if v.get('severity') == 'critical']),
                    "high": len([v for v in vulnerabilities if v.get('severity') == 'high']),
                    "medium": len([v for v in vulnerabilities if v.get('severity') == 'medium']),
                    "low": len([v for v in vulnerabilities if v.get('severity') == 'low'])
                }
            }
            
            self.logger(f"Found {len(vulnerabilities)} vulnerabilities for {agent_id}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to get vulnerabilities: {str(e)}"
            self.logger(f"{error_msg}")
            return {"status": "error", "error": error_msg}
    
    def get_fim_data(self, agent_id: str) -> Dict:
        """Get FIM data dari Wazuh manager"""
        if not self.wazuh_api:
            return {"status": "error", "error": "Wazuh API client not available"}
        
        try:
            self.logger(f"Getting FIM data for agent {agent_id}...")
            
            fim_data = self.wazuh_api.get_fim_data(agent_id)
            result = {
                "status": "success",
                "agent_id": agent_id,
                "total_files": len(fim_data),
                "fim_data": fim_data[:50],  # Limit to 50 items
                "summary": {
                    "alerts": len([f for f in fim_data if f.get('alert')]),
                    "changes": len([f for f in fim_data if f.get('type') == 'modified']),
                    "additions": len([f for f in fim_data if f.get('type') == 'added']),
                    "deletions": len([f for f in fim_data if f.get('type') == 'deleted'])
                }
            }
            
            self.logger(f"FIM data: {len(fim_data)} files monitored")
            return result
            
        except Exception as e:
            error_msg = f"Failed to get FIM data: {str(e)}"
            self.logger(f"{error_msg}")
            return {"status": "error", "error": error_msg}
    
    def get_agent_security_events(self, agent_id: str, limit: int = 50) -> Dict:
        """Get security events dari Wazuh manager"""
        if not self.wazuh_api:
            return {"status": "error", "error": "Wazuh API client not available"}
        
        try:
            self.logger(f"Getting security events for agent {agent_id}...")
            
            events = self.wazuh_api.get_agent_security_events(agent_id, limit=limit)
            result = {
                "status": "success",
                "agent_id": agent_id,
                "total_events": len(events),
                "events": events,
                "summary": {
                    "high_severity": len([e for e in events if e.get('level', 0) >= 10]),
                    "recent_events": len(events)
                }
            }
            
            self.logger(f"Found {len(events)} security events for {agent_id}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to get security events: {str(e)}"
            self.logger(f"{error_msg}")
            return {"status": "error", "error": error_msg}
    
    def get_agents(self) -> Dict:
        """Get semua agents dari Wazuh manager"""
        if not self.wazuh_api:
            return {"status": "error", "error": "Wazuh API client not available"}
        
        try:
            self.logger("Getting all Wazuh agents...")
            
            agents = self.wazuh_api.get_agents()
            result = {
                "status": "success",
                "total_agents": len(agents),
                "agents": agents,
                "summary": {
                    "active": len([a for a in agents if a.get('status') == 'active']),
                    "disconnected": len([a for a in agents if a.get('status') == 'disconnected']),
                    "pending": len([a for a in agents if a.get('status') == 'pending'])
                }
            }
            
            self.logger(f"Found {len(agents)} Wazuh agents")
            return result
            
        except Exception as e:
            error_msg = f"Failed to get agents: {str(e)}"
            self.logger(f"{error_msg}")
            return {"status": "error", "error": error_msg}