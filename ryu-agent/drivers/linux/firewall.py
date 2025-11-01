import subprocess
import json
import re
import os
from utils import detect_os_family, execute_command

class ServerFirewallDriver:
    def __init__(self, logger=print):
        self.logger = logger
        self.os_family = detect_os_family()
        self._execute_command = execute_command
        self.firewall_type = self.detect_firewall()
        self.logger(f"Detected OS: {self.os_family}, Firewall: {self.firewall_type}")

    def detect_firewall(self):
        """Detect active firewall system dengan priority berdasarkan OS"""
        # Priority berdasarkan OS family
        if self.os_family in ['debian', 'ubuntu']:
            # Debian/Ubuntu: cek UFW dulu
            try:
                result = subprocess.run(["ufw", "status"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.logger("Detected UFW firewall")
                    return "ufw"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        if self.os_family in ['rhel', 'centos', 'fedora']:
            # RHEL/CentOS/Fedora: cek firewalld dulu
            try:
                result = subprocess.run(["firewall-cmd", "--state"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and "running" in result.stdout:
                    self.logger("Detected Firewalld")
                    return "firewalld"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        if self.os_family == 'suse':
            # openSUSE: cek SuSEfirewall2
            try:
                result = subprocess.run(["systemctl", "is-active", "SuSEfirewall2"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.logger("Detected SuSEfirewall2")
                    return "suse"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        # Fallback: cek semua yang mungkin
        firewall_checks = [
            ("ufw", ["ufw", "status"]),
            ("firewalld", ["firewall-cmd", "--state"]),
            ("iptables", ["iptables", "-L"]),
        ]

        for fw_name, cmd in firewall_checks:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.logger(f"Detected {fw_name} firewall")
                    return fw_name
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        self.logger("No firewall detected, using iptables fallback")
        return "iptables"

    # === UFW Section ===
    def ufw(self, *args):
        """Execute UFW command"""
        cmd = ["ufw"] + list(args)
        result = self._execute_command(cmd)
        return result["stdout"] if result["success"] else f"Error: {result.get('error', result['stderr'])}"

    def ufw_enable(self):
        """Enable UFW firewall"""
        return self.ufw("--force", "enable")

    def ufw_disable(self):
        """Disable UFW firewall"""
        return self.ufw("--force", "disable")

    def ufw_reload(self):
        """Reload UFW firewall"""
        return self.ufw("reload")

    def ufw_reset(self):
        """Reset UFW firewall"""
        return self.ufw("--force", "reset")

    def ufw_allow(self, port_proto):
        """Allow port/protocol in UFW"""
        return self.ufw("allow", port_proto)

    def ufw_deny(self, port_proto):
        """Deny port/protocol in UFW"""
        return self.ufw("deny", port_proto)

    def ufw_delete(self, rule):
        """Delete UFW rule by number or specification"""
        return self.ufw("delete", rule)

    def ufw_status(self):
        """Get UFW status"""
        return self.ufw("status", "verbose")

    # === Firewalld Section ===
    def firewall_cmd(self, *args):
        """Execute firewall-cmd command"""
        cmd = ["firewall-cmd"] + list(args)
        result = self._execute_command(cmd)
        return result["stdout"] if result["success"] else f"Error: {result.get('error', result['stderr'])}"

    def firewall_reload(self):
        """Reload firewalld"""
        return self.firewall_cmd("--reload")

    def firewall_add_port(self, port_proto):
        """Add port to firewalld"""
        result1 = self.firewall_cmd(f"--add-port={port_proto}", "--permanent")
        result2 = self.firewall_cmd("--reload")
        return f"Add port: {result1}\nReload: {result2}"

    def firewall_remove_port(self, port_proto):
        """Remove port from firewalld"""
        result1 = self.firewall_cmd(f"--remove-port={port_proto}", "--permanent")
        result2 = self.firewall_cmd("--reload")
        return f"Remove port: {result1}\nReload: {result2}"

    def firewall_enable_masquerade(self):
        """Enable masquerade in firewalld"""
        result1 = self.firewall_cmd("--add-masquerade", "--permanent")
        result2 = self.firewall_cmd("--reload")
        return f"Enable masquerade: {result1}\nReload: {result2}"

    def firewall_disable_masquerade(self):
        """Disable masquerade in firewalld"""
        result1 = self.firewall_cmd("--remove-masquerade", "--permanent")
        result2 = self.firewall_cmd("--reload")
        return f"Disable masquerade: {result1}\nReload: {result2}"

    def firewall_status(self):
        """Get firewalld status"""
        return self.firewall_cmd("--list-all")

    def firewalld_list_services(self):
        """List firewalld services"""
        return self.firewall_cmd("--list-services")

    def firewalld_list_ports(self):
        """List firewalld ports"""
        return self.firewall_cmd("--list-ports")

    # === SuSEfirewall2 Section ===
    def suse_firewall(self, *args):
        """Execute SuSEfirewall2 commands"""
        cmd = ["SuSEfirewall2"] + list(args)
        result = self._execute_command(cmd)
        return result["stdout"] if result["success"] else f"Error: {result.get('error', result['stderr'])}"

    def suse_start(self):
        """Start SuSEfirewall2"""
        return self.suse_firewall("start")

    def suse_stop(self):
        """Stop SuSEfirewall2"""
        return self.suse_firewall("stop")

    def suse_restart(self):
        """Restart SuSEfirewall2"""
        return self.suse_firewall("restart")

    # === NAT Section (Cross-distro) ===
    def setup_nat(self, out_interface):
        """Setup NAT menggunakan iptables (works on all distros)"""
        try:
            self.logger(f"Setting up NAT on {out_interface}")
            
            # Enable IP forwarding (persistent based on OS)
            if self.os_family in ['debian', 'ubuntu']:
                subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], check=True)
                # Make persistent
                with open("/etc/sysctl.d/99-ipforward.conf", "w") as f:
                    f.write("net.ipv4.ip_forward=1\n")
            elif self.os_family in ['rhel', 'centos', 'fedora']:
                subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], check=True)
                # For RHEL/CentOS, also update sysctl.conf
                subprocess.run(["echo", "net.ipv4.ip_forward=1", ">>", "/etc/sysctl.conf"], shell=True, check=True)
            
            # Clear existing NAT rules
            subprocess.run(["iptables", "-t", "nat", "-F"], check=True)
            
            # Add NAT rule
            subprocess.run([
                "iptables", "-t", "nat", "-A", "POSTROUTING", 
                "-o", out_interface, "-j", "MASQUERADE"
            ], check=True)
            
            # Save rules based on OS
            if self.os_family in ['debian', 'ubuntu']:
                subprocess.run(["iptables-save", ">", "/etc/iptables/rules.v4"], shell=True, check=True)
            elif self.os_family in ['rhel', 'centos', 'fedora']:
                subprocess.run(["service", "iptables", "save"], check=True)
            
            return {"status": "success", "message": f"NAT enabled on {out_interface}"}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def clear_nat(self):
        """Clear all NAT rules"""
        try:
            subprocess.run(["iptables", "-t", "nat", "-F"], check=True)
            
            # Save cleared rules
            if self.os_family in ['debian', 'ubuntu']:
                subprocess.run(["iptables-save", ">", "/etc/iptables/rules.v4"], shell=True, check=True)
            elif self.os_family in ['rhel', 'centos', 'fedora']:
                subprocess.run(["service", "iptables", "save"], check=True)
                
            return {"status": "success", "message": "All NAT rules cleared"}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # === Status Methods ===
    def status_all(self):
        """Get complete firewall status"""
        result = {
            "os_family": self.os_family,
            "detected_firewall": self.firewall_type
        }
        
        # Get status based on detected firewall
        if self.firewall_type == "ufw":
            result["ufw_status"] = self.ufw_status()
        elif self.firewall_type == "firewalld":
            result["firewalld_status"] = self.firewall_status()
        elif self.firewall_type == "suse":
            result["suse_status"] = self.suse_firewall("status")
        
        # Get iptables status (available on all)
        try:
            result["iptables_nat"] = subprocess.getoutput("iptables -t nat -L -n -v")
            result["iptables_filter"] = subprocess.getoutput("iptables -L -n -v")
        except Exception as e:
            result["iptables_error"] = f"Error: {str(e)}"
            
        return result

    def detect_firewall_type(self):
        """Detect and return firewall type"""
        return self.firewall_type