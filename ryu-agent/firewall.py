import subprocess
import json
import re

class FirewallDriver:
    def __init__(self, logger=print):
        self.logger = logger
        self.firewall_type = self.detect_firewall()

    def detect_firewall(self):
        """Detect active firewall system"""
        try:
            # Check if UFW is available and active
            result = subprocess.run(["ufw", "status"], capture_output=True, text=True)
            if result.returncode == 0:
                self.logger("Detected UFW firewall")
                return "ufw"
        except FileNotFoundError:
            pass

        try:
            # Check if firewalld is available and active
            result = subprocess.run(["firewall-cmd", "--state"], capture_output=True, text=True)
            if result.returncode == 0 and "running" in result.stdout:
                self.logger("Detected Firewalld")
                return "firewalld"
        except FileNotFoundError:
            pass

        self.logger("No firewall detected, using iptables fallback")
        return "iptables"

    # === UFW Section ===
    def ufw(self, *args):
        """Execute UFW command"""
        cmd = ["ufw"] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Error: {result.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return "Error: Command timeout"
        except Exception as e:
            return f"Error: {str(e)}"

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
        return self.ufw("status")

    # === Firewalld Section ===
    def firewall_cmd(self, *args):
        """Execute firewall-cmd command"""
        cmd = ["firewall-cmd"] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Error: {result.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return "Error: Command timeout"
        except Exception as e:
            return f"Error: {str(e)}"

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

    # === NAT Section ===
    def setup_nat(self, out_interface):
        """Setup NAT using iptables"""
        try:
            self.logger(f"Setting up NAT on {out_interface}")
            
            # Enable IP forwarding
            with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
                f.write("1")
            
            # Clear existing rules
            subprocess.run(["iptables", "-t", "nat", "-F"], check=True)
            
            # Add NAT rule
            subprocess.run([
                "iptables", "-t", "nat", "-A", "POSTROUTING", 
                "-o", out_interface, "-j", "MASQUERADE"
            ], check=True)
            
            # Save rules
            subprocess.run(["iptables-save"], check=True)
            
            return {"status": "success", "message": f"NAT enabled on {out_interface}"}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def clear_nat(self):
        """Clear all NAT rules"""
        try:
            subprocess.run(["iptables", "-t", "nat", "-F"], check=True)
            subprocess.run(["iptables-save"], check=True)
            return {"status": "success", "message": "All NAT rules cleared"}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # === Status Methods ===
    def status_all(self):
        """Get complete firewall status"""
        result = {}
        
        if self.firewall_type == "ufw":
            result["ufw"] = self.ufw_status()
        elif self.firewall_type == "firewalld":
            result["firewalld"] = self.firewall_status()
        
        # Get iptables NAT rules
        try:
            result["nat_rules"] = subprocess.getoutput("iptables -t nat -L -n -v")
        except Exception as e:
            result["nat_rules"] = f"Error: {str(e)}"
            
        return result

    def detect_firewall_type(self):
        """Detect and return firewall type"""
        return self.firewall_type