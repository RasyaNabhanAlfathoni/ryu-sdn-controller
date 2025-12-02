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

    def _execute_systemctl(self, command: str) -> Dict:
        """Untuk eksekusi systemctl menggunakan nsenter"""
        try:
            host_cmd = f"nsenter --target 1 --mount --uts --ipc --net --pid {command}"
            self.logger(f"Executing systemctl on Host: {host_cmd}")

            result = subprocess.run(
                host_cmd,
                shell=True,
                capture_output=True,
                text=True
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
                "systemctl daemon-reload",
                "systemctl enable wazuh-agent",
                "systemctl start wazuh-agent"
            ],
            'yum': [
                f"WAZUH_MANAGER='{manager_ip}' rpm -ihv {filename}",
                "systemctl daemon-reload", 
                "systemctl enable wazuh-agent",
                "systemctl start wazuh-agent"
            ],
            'dnf': [
                f"WAZUH_MANAGER='{manager_ip}' dnf install -y {filename}",
                "systemctl daemon-reload",
                "systemctl enable wazuh-agent", 
                "systemctl start wazuh-agent"
            ],
            'zypper': [
                f"WAZUH_MANAGER='{manager_ip}' zypper install -y {filename}",
                "systemctl daemon-reload",
                "systemctl enable wazuh-agent",
                "systemctl start wazuh-agent"
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

            if not cap["systemd"] and not cap["sysvinit"]:
                return {"success": False, "error": "No supported init system (systemd/SysV) detected on host!"}

            if not cap["curl"] and not cap["wget"]:
                return {"success": False, "error": "Host has neither curl nor wget installed!"}

            self.logger("Starting Wazuh agent installation...")

            # Check if installed
            result = self._execute_on_host("test -f /var/ossec/bin/wazuh-agent")
            if "installed" in result.get("output", ""):
                self.logger("Wazuh already installed, reconfiguring...")
                key_result = self._register_agent_key(agent_key, agent_name)
                if key_result["success"]:
                    self._execute_systemctl("systemctl restart wazuh-agent")
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

            # Restart service to apply key
            self.logger("Restarting Wazuh agent...")
            self._execute_systemctl("systemctl restart wazuh-agent")

            # Final verification
            import time
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
            self.logger(f"Host installation failed: {str(e)}")
            return {"success": False, "error": f"Host installation failed: {str(e)}"}


    def _register_agent_key(self, agent_key: str, agent_name: str) -> Dict:
        """Register agent key dengan IP yang benar"""
        try:
            key_parts = agent_key.strip().split()
            if len(key_parts) < 2:
                return {"success": False, "error": f"Invalid agent key format: {agent_key}"}
            
            agent_id = key_parts[0]
            actual_key = key_parts[1]
            
            # Get HOST IP
            result = self._execute_on_host("hostname -I | awk '{print $1}'")
            local_ip = result.get("output", "").strip()
            
            # Format key file
            key_content = f"{agent_id} {actual_key} {agent_name} {local_ip}\n"
            
            # Write to Host's /var/ossec/etc/client.keys
            temp_key = f"/tmp/agent_key_{agent_id}"
            write_cmd = f"echo '{key_content}' > {temp_key}"
            self._execute_on_host(write_cmd)
            
            # Copy to final location on Host
            copy_cmd = f"mkdir -p /var/ossec/etc && cp {temp_key} /var/ossec/etc/client.keys && chmod 644 /var/ossec/etc/client.keys"
            self._execute_on_host(copy_cmd)
            
            # Cleanup
            self._execute_on_host(f"rm -f {temp_key}")
            
            self.logger(f"Agent key registered on Host: {agent_name} -> {local_ip}")
            return {"success": True, "agent_id": agent_id}
            
        except Exception as e:
            return {"success": False, "error": f"Key registration failed: {str(e)}"}

    def get_wazuh_agent_status(self) -> Dict:
        """Get comprehensive Wazuh agent status"""
        try:
            # Check service status on Host
            service_result = self._execute_systemctl("systemctl is-active wazuh-agent")
            service_status = service_result.get("output", "").strip() if service_result["success"] else "unknown"
            
            # Check process on Host
            process_result = self._execute_on_host("pgrep -f wazuh-agent")
            process_running = bool(process_result["success"] and process_result.get("output", "").strip())
            
            # Get agent ID dari Host
            agent_id = "unknown"
            result = self._execute_on_host("cat /var/ossec/etc/client.keys 2>/dev/null | head -1")
            if result["success"]:
                key_line = result.get("output", "").strip()
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
            self._execute_systemctl("systemctl stop wazuh-agent")
            
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