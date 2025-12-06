import os
import subprocess
import requests
import tempfile
import platform
import re
import traceback
from typing import Dict, List, Optional
from utils import detect_os_family, execute_on_ssh, execute_on_host

class WazuhDriver:
    def __init__(self, logger=print):
        self.logger = logger
        self.host_root = "/host-rootfs"

    def _execute_on_host(self, command: str) -> Dict:
        """Execute command on Host system (not container) - Using utils"""
        try:
            # Untuk systemctl commands, gunakan SSH bukan chroot
            if command.startswith("systemctl") or command.startswith("service "):
                self.logger(f"[DEBUG] Using SSH for system command: {command}")
                return self._execute_ssh(command)
            
            # Untuk lainnya gunakan execute_on_host biasa
            result = execute_on_host(command)
            return result
        except Exception as e:
            return {"success": False, "error": str(e), "stdout": "", "stderr": ""}

    def _execute_ssh(self, command: str, timeout: int = 300) -> Dict:
        """Execute command via SSH - Using utils"""
        try:
            result = execute_on_ssh(command, timeout=timeout)
            return result
        except Exception as e:
            return {"success": False, "error": str(e), "stdout": "", "stderr": ""}
        
    def _get_service_command(self, systemctl_command: str) -> str:
        """Convert systemctl command to sysvinit/service command"""
        command_map = {
            "start wazuh-agent": "service wazuh-agent start || /etc/init.d/wazuh-agent start",
            "stop wazuh-agent": "service wazuh-agent stop || /etc/init.d/wazuh-agent stop",
            "restart wazuh-agent": "service wazuh-agent restart || /etc/init.d/wazuh-agent restart",
            "enable wazuh-agent": "update-rc.d wazuh-agent defaults || chkconfig wazuh-agent on",
            "status wazuh-agent": "service wazuh-agent status || /etc/init.d/wazuh-agent status"
        }
        
        return command_map.get(systemctl_command, systemctl_command)

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
        arch = result.get("stdout", "").strip().lower() if result["success"] else "unknown"
        
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
        return detect_os_family()
    
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
        curl_check = self._execute_ssh("command -v curl")
        wget_check = self._execute_ssh("command -v wget")

        if curl_check["success"] and curl_check.get("stdout"):
            commands.append(f"curl -o {filename} {package_url}")
        elif wget_check["success"] and wget_check.get("stdout"):
            commands.append(f"wget -O {filename} {package_url}")
        else:
            self.logger("error: Host has neither curl nor wget installed!")
            return []
        
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
    
    def verify_agent_connection(self, manager_ip: str, timeout: int = 30) -> Dict:
        """Verify agent can connect to Wazuh manager"""
        import socket
        import time
        
        try:
            self.logger(f"Verifying connection to Wazuh manager: {manager_ip}:1514")
            
            # Test TCP connection to manager
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            result = sock.connect_ex((manager_ip, 1514))
            sock.close()
            
            if result == 0:
                return {"success": True, "message": "Connection to Wazuh manager successful"}
            else:
                return {"success": False, "error": f"Cannot connect to {manager_ip}:1514"}
                
        except Exception as e:
            return {"success": False, "error": f"Connection test failed: {str(e)}"}
        
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

        # Check systemctl via SSH
        systemctl_check = self._execute_ssh("which systemctl 2>/dev/null || echo 'not-found'")
        capabilities["systemd"] = systemctl_check["success"] and "not-found" not in systemctl_check.get("stdout", "")
        
        # Check SysV init via SSH
        initd_check = self._execute_ssh("test -d /etc/init.d && echo ok || echo 'not-found'")
        capabilities["sysvinit"] = initd_check["success"] and "ok" in initd_check.get("stdout", "")
        
        # Check curl & wget via SSH
        curl_check = self._execute_ssh("which curl 2>/dev/null || echo 'not-found'")
        capabilities["curl"] = curl_check["success"] and "not-found" not in curl_check.get("stdout", "")
        
        wget_check = self._execute_ssh("which wget 2>/dev/null || echo 'not-found'")
        capabilities["wget"] = wget_check["success"] and "not-found" not in wget_check.get("stdout", "")

        # Check netplan
        capabilities["netplan"] = os.path.isdir(f"{self.host_root}/etc/netplan")

        # Check systemd-networkd
        capabilities["systemd_networkd"] = os.path.isdir(f"{self.host_root}/etc/systemd/network")

        # Check if legacy /etc/network exists (Debian/Ubuntu classic)
        capabilities["ifupdown"] = os.path.isdir(f"{self.host_root}/etc/network")

        # RHEL network-scripts
        capabilities["network_scripts"] = os.path.isdir(f"{self.host_root}/etc/sysconfig/network-scripts")

        # chroot available?
        capabilities["chroot"] = os.path.exists("/usr/sbin/chroot") or os.path.exists("/bin/chroot")

        return capabilities
    
    def _cleanup_existing_installation(self):
        """Cleanup existing wazuh installation"""
        cleanup_commands = [
            # Stop service
            "service wazuh-agent stop 2>/dev/null || true",
            "/etc/init.d/wazuh-agent stop 2>/dev/null || true",
            "pkill -9 wazuh-agent 2>/dev/null || true",
            "pkill -9 wazuh-agentd 2>/dev/null || true",
            
            # Uninstall package
            "apt-get remove --purge -y wazuh-agent 2>/dev/null || true",
            "yum remove -y wazuh-agent 2>/dev/null || true",
            "rpm -e wazuh-agent 2>/dev/null || true",
            
            # Cleanup directories
            "rm -rf /var/ossec 2>/dev/null || true",
            "rm -rf /etc/wazuh 2>/dev/null || true",
            "rm -f /etc/init.d/wazuh-agent 2>/dev/null || true",
            "rm -f /usr/lib/systemd/system/wazuh-agent.service 2>/dev/null || true"
        ]
        
        for cmd in cleanup_commands:
            self._execute_ssh(cmd)
        
        import time
        time.sleep(2)

    def install_wazuh_agent(self, manager_ip: str, agent_key: str, agent_name: str = None, wazuh_version: str = "4.11.2") -> Dict:
        try:
            cap = self.detect_host_capabilities()
            self.logger(f"Host Capabilities: {cap}")

            if not cap["host_root_mounted"]:
                return {"success": False, "error": "host-rootfs is not mounted — cannot continue"}

            if not cap["systemd"] and not cap["sysvinit"]:
                return {"success": False, "error": "No supported init system (systemd/SysV) detected on host!"}

            if not cap["curl"] and not cap["wget"]:
                return {"success": False, "error": "Host has neither curl nor wget installed!"}

            self.logger("Starting Wazuh agent installation...")

            # Check if installed
            result = self._execute_ssh("test -f /var/ossec/bin/wazuh-agent")
            if "installed" in result.get("stdout", ""):
                self.logger("Wazuh already installed, reconfiguring...")
                key_result = self._register_agent_key(agent_key, agent_name)
                if key_result["success"]:
                    self._execute_ssh("systemctl restart wazuh-agent")
                    return {"success": True, "message": "Wazuh reconfigured on Host"}

            # Cleanup existing installation
            self._cleanup_existing_installation()
            import time
            time.sleep(3)

            # Detect hostname
            if not agent_name:
                result = self._execute_on_host("hostname")
                agent_name = result.get("stdout", "").strip() or "unknown"

            # Detect system
            package_manager = self.detect_package_manager()
            architecture = self.detect_architecture()
            os_info = self.detect_os_family()

            self.logger(f"System info - Package Manager: {package_manager}, Arch: {architecture}, OS: {os_info}")

            # Get package URL
            package_url = self.get_wazuh_package_url(os_info['family'], architecture, wazuh_version)

            # Generate installation commands
            commands = self.get_install_commands(package_url, package_manager, manager_ip)
            if not commands:
                return {"success": False, "error": "Host has neither curl nor wget installed!"}

            # Execute installation commands
            self.logger("Executing installation commands on Host...")
            for cmd in commands:
                result = self._execute_ssh(f"cd /tmp && {cmd}")
                if not result["success"]:
                    error_msg = result.get("stderr") or result.get("error") or "Unknown error"
                    return {"success": False, "error": f"Failed at '{cmd}', error: {error_msg}"}
                
            # Update ossec.conf dengan IP manager yang benar
            config_result = self._update_ossec_config(manager_ip)
            if not config_result["success"]:
                self.logger(f"Warning: Config update failed: {config_result.get('error')}")
                
            # Register agent key
            self.logger("Registering agent key on Host...")
            key_result = self._register_agent_key(agent_key, agent_name)
            if not key_result.get("success"):
                return {"success": False, "error": key_result["error"]}
            
            # Cek client.keys
            check_keys = self._execute_ssh("cat /var/ossec/etc/client.keys")
            if check_keys["success"] and check_keys.get("stdout", "").strip():
                self.logger(f"client.keys exists: {check_keys.get('stdout', '').strip()}")
            else:
                self.logger("client.keys is empty or missing!")

            # Restart service to apply key
            self.logger("Starting Wazuh agent...")
            # List metode start dengan prioritas
            start_methods = [
                "systemctl daemon-reload && systemctl enable wazuh-agent && systemctl start wazuh-agent",
                "service wazuh-agent start",
                "/etc/init.d/wazuh-agent start",
                "/var/ossec/bin/wazuh-control start",
                "cd /var/ossec && ./bin/wazuh-agentd -d"
            ]

            start_success = False
            start_method_used = None
            for method in start_methods:
                self.logger(f"Trying: {method}")
                
                # Tentukan apakah method ini butuh SSH atau chroot
                if method.startswith("systemctl") or method.startswith("service "):
                    result = self._execute_ssh(method)
                else:
                    result = self._execute_on_host(method)
                    
                if result["success"]:
                    self.logger(f"Started with: {method}")
                    start_success = True
                    start_method_used = method
                    break
                else:
                    error_msg = result.get("stderr", "").strip()
                    if error_msg:
                        self.logger(f"Failed: {method}, Error: {error_msg}")

            # Final verification
            time.sleep(5)
            final_status = self.get_wazuh_agent_status()

            return {
                "success": True,
                "message": "Wazuh agent installation completed",
                "agent_name": agent_name,
                "agent_id": key_result.get("agent_id", "unknown"),
                "agent_status": final_status,
                "service_running": final_status.get("active", False),
                "system_info": {
                    "package_manager": package_manager,
                    "architecture": architecture,
                    "os_family": os_info['family']
                }
            }

        except Exception as e:
            self.logger(f"Installation failed: {str(e)}")
            self.logger(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "error": f"Installation failed: {str(e)}"}


    def _register_agent_key(self, agent_key: str, agent_name: str) -> Dict:
        """Register agent key dengan IP yang benar"""
        try:
            # Format dari Wazuh: "094 server-wazuh any b74ccda754d087250c3cd28e6aef37794fd3f1eeca5697bcdd6de8fb3905a40f"
            # 4 bagian: ID, NAME, ANY, KEY_HASH
            
            key_parts = agent_key.strip().split()
            
            if len(key_parts) != 4:
                return {
                    "success": False, 
                    "error": f"Invalid agent key format. Expected 4 parts, got {len(key_parts)}: {agent_key}"
                }
            
            # Format untuk client.keys: "ID NAME ANY KEY_HASH"
            # Contoh: "094 server-wazuh any b74ccda754d087250c3cd28e6aef37794fd3f1eeca5697bcdd6de8fb3905a40f"
            key_content = f"{key_parts[0]} {key_parts[1]} {key_parts[2]} {key_parts[3]}\n"
            
            self.logger(f"Writing client.keys content: {key_content.strip()}")
            
            # Write ke client.keys
            temp_file = "/tmp/client.keys.tmp"
            write_cmd = f"echo '{key_content.strip()}' > {temp_file}"
            write_result = self._execute_on_host(write_cmd)
            
            if not write_result["success"]:
                error_msg = write_result.get("stderr") or write_result.get("error") or "Unknown error"
                return {"success": False, "error": f"Failed to write temp key file: {error_msg}"}
            
            # Copy ke lokasi final dengan permissions yang benar
            final_path = "/var/ossec/etc/client.keys"
            copy_cmd = f"mkdir -p /var/ossec/etc && cp {temp_file} {final_path} && chmod 640 {final_path} && chown root:wazuh {final_path}"
            copy_result = self._execute_on_host(copy_cmd)
            
            # Cleanup
            self._execute_on_host(f"rm -f {temp_file}")
            
            # Verifikasi
            verify_cmd = f"cat {final_path} && echo '--- Lines:' && wc -l {final_path}"
            verify_result = self._execute_on_host(verify_cmd)
            
            self.logger(f"Client.keys verification: {verify_result.get('stdout', '')}")
            
            return {
                "success": True,
                "agent_id": key_parts[0],
                "key_written": key_content.strip(),
                "message": f"Agent key registered for {agent_name} (ID: {key_parts[0]})"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Key registration failed: {str(e)}"}
        
    def _update_ossec_config(self, manager_ip: str) -> Dict:
        """Update ossec.conf dengan IP manager yang benar - FIX XML structure"""
        try:
            ossec_conf_path = "/var/ossec/etc/ossec.conf"
            
            # Backup original
            self._execute_on_host(f"cp {ossec_conf_path} {ossec_conf_path}.backup.$(date +%s)")
            
            # Baca original config (sebelum kita modif)
            read_cmd = f"cat {ossec_conf_path}"
            result = self._execute_on_host(read_cmd)
            
            if not result["success"]:
                error_msg = result.get("stderr") or result.get("error") or "Cannot read ossec.conf"
                return {"success": False, "error": error_msg}
            
            original_content = result["stdout"]
            
            # Debug: lihat struktur asli
            self.logger(f"DEBUG: Original config length: {len(original_content)} chars")
            
            # Method 1: Simple replace manager IP
            # Cari tag <address> dan ganti isinya
            import re
            
            # Pattern untuk mencari <address> tag
            address_pattern = r'<address>[^<]+</address>'
            
            # Replace dengan IP baru
            updated_content = re.sub(
                address_pattern, 
                f'<address>{manager_ip}</address>', 
                original_content,
                count=1  # Hanya ganti yang pertama
            )
            
            # Cek apakah replacement berhasil
            if f'<address>{manager_ip}</address>' not in updated_content:
                # Method 2: Jika regex gagal, coba replace string sederhana
                if '<address>MANAGER_IP</address>' in original_content:
                    updated_content = original_content.replace(
                        '<address>MANAGER_IP</address>',
                        f'<address>{manager_ip}</address>'
                    )
                elif '<address>0.0.0.0</address>' in original_content:
                    updated_content = original_content.replace(
                        '<address>0.0.0.0</address>',
                        f'<address>{manager_ip}</address>'
                    )
                else:
                    # Method 3: Insert manual
                    lines = original_content.split('\n')
                    updated_lines = []
                    for line in lines:
                        if '<address>' in line and '</address>' in line:
                            updated_lines.append(f'      <address>{manager_ip}</address>')
                        else:
                            updated_lines.append(line)
                    updated_content = '\n'.join(updated_lines)
            
            # VALIDASI: Cek XML structure
            # Pastikan hanya ada satu <ossec_config> tag pembuka dan penutup
            opening_tags = updated_content.count('<ossec_config>')
            closing_tags = updated_content.count('</ossec_config>')
            
            if opening_tags != 1 or closing_tags != 1:
                self.logger(f"WARNING: XML structure issue - opening: {opening_tags}, closing: {closing_tags}")
                
                # Fix: Ambil hanya bagian dalam ossec_config yang pertama
                if '<ossec_config>' in updated_content and '</ossec_config>' in updated_content:
                    start = updated_content.find('<ossec_config>')
                    end = updated_content.find('</ossec_config>', start) + len('</ossec_config>')
                    updated_content = updated_content[start:end]
                    self.logger("Fixed XML structure - took first ossec_config block")
            
            # Tulis ke file temporary
            temp_file = "/tmp/ossec.conf.fixed"
            # Gunakan base64 untuk menghindari escaping issues
            import base64
            encoded_content = base64.b64encode(updated_content.encode()).decode()
            write_cmd = f"echo '{encoded_content}' | base64 -d > {temp_file}"
            
            write_result = self._execute_on_host(write_cmd)
            if not write_result["success"]:
                error_msg = write_result.get("stderr") or write_result.get("error") or "Failed to write temp file"
                return {"success": False, "error": error_msg}
            
            # Copy ke final location
            copy_cmd = f"cp {temp_file} {ossec_conf_path} && chmod 640 {ossec_conf_path} && chown root:wazuh {ossec_conf_path}"
            copy_result = self._execute_on_host(copy_cmd)
            
            if not copy_result["success"]:
                error_msg = copy_result.get("stderr") or copy_result.get("error") or "Failed to copy config"
                return {"success": False, "error": error_msg}
            
            # Cleanup
            self._execute_on_host(f"rm -f {temp_file}")
            
            # Verifikasi final
            verify_cmd = f"cat {ossec_conf_path} | grep -c '<address>{manager_ip}</address>'"
            verify_result = self._execute_on_host(verify_cmd)
            
            if verify_result["success"] and verify_result.get("stdout", "").strip() == "1":
                self.logger(f"✓ Updated ossec.conf with manager IP: {manager_ip}")
                
                # Cek XML structure akhir
                final_check = f"grep -c '^<ossec_config>$' {ossec_conf_path} || true"
                final_result = self._execute_on_host(final_check)
                self.logger(f"Final structure check: {final_result.get('stdout', '')}")
                
                return {"success": True, "message": f"Config updated with {manager_ip}"}
            else:
                return {"success": False, "error": "Failed to verify config update"}
                
        except Exception as e:
            self.logger(f"Config update failed: {str(e)}")
            import traceback
            self.logger(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "error": f"Config update failed: {str(e)}"}

    def get_wazuh_agent_status(self) -> Dict:
        """Get comprehensive Wazuh agent status"""
        try:
            # Check service status on Host
            service_result = self._execute_ssh("systemctl is-active wazuh-agent")
            service_status = service_result.get("stdout", "").strip() if service_result["success"] else "unknown"
            
            # Check process on Host
            process_result = self._execute_on_host("pgrep -f wazuh-agent")
            process_running = bool(process_result["success"] and process_result.get("stdout", "").strip())
            
            # Get agent ID dari Host
            agent_id = "unknown"
            result = self._execute_on_host("cat /var/ossec/etc/client.keys 2>/dev/null | head -1")
            if result["success"]:
                key_line = result.get("stdout", "").strip()
                if key_line:
                    parts = key_line.split()
                    if len(parts) >= 1:
                        agent_id = parts[0]
            
            return {
                "service_status": service_status,
                "process_running": process_running,
                "agent_id": agent_id,
                "active": service_status == "active"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def uninstall_wazuh_agent(self) -> Dict:
        """Wazuh agent uninstaller"""
        try:
            package_manager = self.detect_package_manager()
            
            # Stop service
            self._execute_ssh("systemctl stop wazuh-agent")
            
            # Uninstall berdasarkan package manager
            uninstall_commands = {
                'apt': "dpkg --purge wazuh-agent",
                'yum': "rpm -e wazuh-agent", 
                'dnf': "dnf remove -y wazuh-agent",
                'zypper': "zypper remove -y wazuh-agent"
            }
            
            cmd = uninstall_commands.get(package_manager, uninstall_commands['apt'])
            result = self._execute_on_host(cmd)
            
            # Cleanup files
            cleanup_dirs = [
                "/var/ossec",
                "/etc/wazuh",
                "/usr/share/wazuh"
            ]
            
            for directory in cleanup_dirs:
                self._execute_on_host(f"rm -rf {directory}")
        
            return {
                "success": True,
                "message": "Wazuh agent uninstalled successfully",
                "package_manager": package_manager
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