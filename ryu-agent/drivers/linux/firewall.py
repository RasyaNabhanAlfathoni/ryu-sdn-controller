import subprocess
import json
import re
import os
from utils import detect_os_family, execute_command, execute_on_host, execute_on_ssh

class ServerFirewallDriver:
    def __init__(self, logger=print):
        self.logger = logger
        # Gunakan execute_on_host untuk deteksi OS (untuk host)
        os_info = detect_os_family()
        self.os_family = os_info.get('family', 'unknown')
        self._execute_on_host = execute_on_host  # Untuk perintah
        self._execute_on_ssh = execute_on_ssh    # Untuk apply commands
        self._execute_command = execute_command  # Untuk perintah di container
        self.firewall_type = self.detect_firewall()
        self.logger(f"Detected OS: {self.os_family}, Firewall: {self.firewall_type}")

    def _execute(self, cmd, use_ssh=False):
        """Wrapper untuk execute command dengan fallback"""
        try:
            if use_ssh:
                return self._execute_on_ssh(cmd)
            else:
                return self._execute_on_host(cmd)
        except Exception as e:
            self.logger(f"Error executing command: {e}")
            return {"success": False, "error": str(e)}

    def detect_firewall(self):
        """Detect active firewall system"""
        # Priority berdasarkan OS family
        if self.os_family in ['debian', 'ubuntu']:
            # Debian/Ubuntu: cek UFW dulu
            try:
                result = self._execute_on_host("ufw status")
                if result["success"] and "Status:" in result["stdout"]:
                    self.logger("Detected UFW firewall")
                    return "ufw"
            except Exception:
                pass

        if self.os_family in ['rhel', 'centos', 'fedora']:
            # RHEL/CentOS/Fedora: cek firewalld dulu
            try:
                result = self._execute_on_host("firewall-cmd --state")
                if result["success"] and "running" in result["stdout"]:
                    self.logger("Detected Firewalld")
                    return "firewalld"
            except Exception:
                pass

        if self.os_family == 'suse':
            # openSUSE: cek SuSEfirewall2
            try:
                result = self._execute_on_host("systemctl is-active SuSEfirewall2")
                if result["success"] and result["stdout"].strip() == "active":
                    self.logger("Detected SuSEfirewall2")
                    return "suse"
            except Exception:
                pass

        # Fallback: cek semua yang mungkin
        firewall_checks = [
            ("ufw", "ufw status"),
            ("firewalld", "firewall-cmd --state"),
            ("iptables", "iptables -L"),
        ]

        for fw_name, cmd in firewall_checks:
            try:
                result = self._execute_on_host(cmd)
                if result["success"]:
                    self.logger(f"Detected {fw_name} firewall")
                    return fw_name
            except Exception:
                continue

        self.logger("No firewall detected, using iptables fallback")
        return "iptables"

    # === UFW Section (MENGGUNAKAN HOST) ===
    def ufw(self, *args):
        """Execute UFW command"""
        cmd = "ufw " + " ".join(args)
        result = self._execute_on_host(cmd)
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
        """Get UFW status from HOST"""
        return self.ufw("status", "verbose")

    # === Firewalld Section ===
    def firewalld_enable(self):
        """Enable firewalld service (start on boot)"""
        try:
            # Enable service
            enable_cmd = "systemctl enable firewalld"
            enable_result = self._execute_on_ssh(enable_cmd)
            
            # Start service
            start_cmd = "systemctl start firewalld"
            start_result = self._execute_on_ssh(start_cmd)
            
            # Wait a bit for service to start
            import time
            time.sleep(2)
            
            # Get status
            status_cmd = "systemctl is-active firewalld"
            status_result = self._execute_on_ssh(status_cmd)
            
            # Get firewalld state
            state_cmd = "firewall-cmd --state"
            state_result = self._execute_on_host(state_cmd)
            
            return {
                "success": True,
                "enabled": enable_result["success"],
                "started": start_result["success"],
                "service_status": status_result["stdout"].strip() if status_result["success"] else "unknown",
                "firewalld_state": state_result["stdout"].strip() if state_result["success"] else "unknown",
                "actions": [
                    {"action": "enable", "result": enable_result},
                    {"action": "start", "result": start_result},
                    {"action": "check_status", "result": status_result}
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def firewalld_disable(self):
        """Disable firewalld service (stop and disable on boot)"""
        try:
            # Stop service
            stop_cmd = "systemctl stop firewalld"
            stop_result = self._execute_on_ssh(stop_cmd)
            
            # Disable service
            disable_cmd = "systemctl disable firewalld"
            disable_result = self._execute_on_ssh(disable_cmd)
            
            # Get status
            status_cmd = "systemctl is-active firewalld"
            status_result = self._execute_on_ssh(status_cmd)
            
            return {
                "success": True,
                "stopped": stop_result["success"],
                "disabled": disable_result["success"],
                "service_status": status_result["stdout"].strip() if status_result["success"] else "unknown",
                "actions": [
                    {"action": "stop", "result": stop_result},
                    {"action": "disable", "result": disable_result}
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def firewall_cmd(self, *args, zone=None):
        """Execute firewall-cmd command dengan optional zone"""
        cmd_parts = ["firewall-cmd"]
        
        # Tambah zone jika ada
        if zone:
            cmd_parts.append(f"--zone={zone}")
        
        cmd_parts.extend(args)
        cmd = " ".join(cmd_parts)
        
        result = self._execute_on_host(cmd)
        return result["stdout"] if result["success"] else f"Error: {result.get('error', result['stderr'])}"

    def firewall_offline_cmd(self, *args, zone=None):
        """Execute firewall-offline-cmd command dengan optional zone"""
        cmd_parts = ["firewall-offline-cmd"]
        
        # Tambah zone jika ada
        if zone:
            cmd_parts.append(f"--zone={zone}")

        filtered_args = []
        for arg in args:
            # Skip --permanent flag
            if arg.strip() != "--permanent" and not arg.startswith("--permanent "):
                filtered_args.append(arg)
        
        cmd_parts.extend(args)
        cmd = " ".join(cmd_parts)
        
        result = self._execute_on_host(cmd)
        return result["stdout"] if result["success"] else f"Error: {result.get('error', result['stderr'])}"

    def firewall_reload(self):
        """Reload firewalld"""
        result = self._execute_on_ssh("firewall-cmd --reload")
        return result["stdout"] if result["success"] else f"Error: {result.get('error', result['stderr'])}"

    def firewall_add_port(self, port_proto, zone="public"):
        """Add port to firewalld dengan zone support"""
        # Gunakan SSH untuk apply commands
        result1 = self._execute_on_host(f"firewall-cmd --add-port={port_proto} --permanent --zone={zone}")
        result2 = self._execute_on_ssh("firewall-cmd --reload")
        
        return {
            "zone": zone,
            "add_port": result1["stdout"] if result1["success"] else f"Error: {result1.get('error', result1['stderr'])}",
            "reload": result2["stdout"] if result2["success"] else f"Error: {result2.get('error', result2['stderr'])}",
            "port_proto": port_proto,
            "success": result1["success"] and result2["success"]
        }

    def firewall_remove_port(self, port_proto, zone="public"):
        """Remove port from firewalld dengan zone support"""
        result1 = self._execute_on_host(f"firewall-cmd --remove-port={port_proto} --permanent --zone={zone}")
        result2 = self._execute_on_ssh("firewall-cmd --reload")
        
        return {
            "zone": zone,
            "remove_port": result1["stdout"] if result1["success"] else f"Error: {result1.get('error', result1['stderr'])}",
            "reload": result2["stdout"] if result2["success"] else f"Error: {result2.get('error', result2['stderr'])}",
            "port_proto": port_proto,
            "success": result1["success"] and result2["success"]
        }

    def firewall_enable_masquerade(self, zone="public"):
        """Enable masquerade in firewalld dengan zone support"""
        result1 = self._execute_on_host(f"firewall-cmd --add-masquerade --permanent --zone={zone}")
        result2 = self._execute_on_ssh("firewall-cmd --reload")
        
        return {
            "zone": zone,
            "enable_masquerade": result1["stdout"] if result1["success"] else f"Error: {result1.get('error', result1['stderr'])}",
            "reload": result2["stdout"] if result2["success"] else f"Error: {result2.get('error', result2['stderr'])}",
            "success": result1["success"] and result2["success"]
        }

    def firewall_disable_masquerade(self, zone="public"):
        """Disable masquerade in firewalld dengan zone support"""
        result1 = self._execute_on_host(f"firewall-cmd --remove-masquerade --permanent --zone={zone}")
        result2 = self._execute_on_ssh("firewall-cmd --reload")
        
        return {
            "zone": zone,
            "disable_masquerade": result1["stdout"] if result1["success"] else f"Error: {result1.get('error', result1['stderr'])}",
            "reload": result2["stdout"] if result2["success"] else f"Error: {result2.get('error', result2['stderr'])}",
            "success": result1["success"] and result2["success"]
        }

    def firewall_status(self, zone=None):
        """Get firewalld status dari HOST dengan optional zone"""
        if zone:
            return self.firewall_cmd(f"--zone={zone}", "--list-all")
        else:
            return self.firewall_cmd("--list-all")

    def firewalld_list_services(self, zone=None):
        """List firewalld services dari HOST dengan optional zone"""
        if zone:
            return self.firewall_cmd(f"--zone={zone}", "--list-services")
        else:
            return self.firewall_cmd("--list-services")

    def firewalld_list_ports(self, zone=None):
        """List firewalld ports dari HOST dengan optional zone"""
        if zone:
            return self.firewall_cmd(f"--zone={zone}", "--list-ports")
        else:
            return self.firewall_cmd("--list-ports")

    # === SuSEfirewall2 Section (MENGGUNAKAN HOST) ===
    def suse_firewall(self, *args):
        """Execute SuSEfirewall2 commands"""
        cmd = "SuSEfirewall2 " + " ".join(args)
        result = self._execute_on_host(cmd)
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

    def get_nat_rules(self):
        """Get current NAT rules from iptables dengan parsing yang benar"""
        try:
            # Get NAT rules
            result = self._execute_on_host("iptables -t nat -L -n -v --line-numbers")
            
            if not result["success"]:
                return {"status": "error", "message": f"Failed to get NAT rules: {result.get('error')}"}
            
            rules_output = result["stdout"]
            
            # Parse dengan state machine yang lebih simple
            chains = {}
            current_chain = None
            
            for line in rules_output.split('\n'):
                line = line.strip()
                
                if not line:
                    continue
                
                # Start of a new chain
                if line.startswith('Chain'):
                    # Parse chain info: Chain POSTROUTING (policy ACCEPT 0 packets, 0 bytes)
                    parts = line.split()
                    if len(parts) >= 2:
                        chain_name = parts[1]
                        
                        # Extract policy
                        policy = "ACCEPT"
                        if '(' in line and ')' in line:
                            policy_part = line[line.find('(')+1:line.find(')')]
                            if 'policy' in policy_part:
                                policy = policy_part.split('policy')[1].strip().split()[0]
                        
                        current_chain = chain_name
                        chains[current_chain] = {
                            "policy": policy,
                            "rules": [],
                            "total_rules": 0
                        }
                    continue
                
                # Skip header lines (num, pkts, bytes, target...)
                if line.startswith('num ') or line.startswith('pkts ') or line.startswith('target '):
                    continue
                
                # If we have a current chain and line contains data
                if current_chain and line:
                    parts = re.split(r'\s+', line)
                    
                    if len(parts) < 10:
                        continue

                    rule_data = {
                        "rule_number": parts[0],
                        "packets": parts[1],
                        "bytes": parts[2],
                        "target": parts[3],
                        "protocol": parts[4],
                        "opt": parts[5],
                        "in": parts[6],
                        "out": parts[7],
                        "source": parts[8],
                        "destination": parts[9],
                        "raw_line": line
                    }

                    if len(parts) > 10:
                        rule_data["additional"] = " ".join(parts[10:])

                    chains[current_chain]["rules"].append(rule_data)
            
            # Update total rules untuk setiap chain
            for chain_name, chain_data in chains.items():
                chain_data["total_rules"] = len(chain_data["rules"])
            
            # Extract MASQUERADE rules dari POSTROUTING
            masquerade_rules = []
            if "POSTROUTING" in chains:
                for rule in chains["POSTROUTING"]["rules"]:
                    if "MASQUERADE" in rule.get("target", ""):
                        masquerade_rules.append({
                            "rule_number": rule.get("rule_number"),
                            "interface": rule.get("out", ""),
                            "protocol": rule.get("protocol", ""),
                            "target": rule.get("target", ""),
                            "source": rule.get("source", ""),
                            "destination": rule.get("destination", ""),
                            "packets": rule.get("packets", "0"),
                            "bytes": rule.get("bytes", "0"),
                            "raw_line": rule.get("raw_line", "")
                        })
            
            # Extract DNAT rules dari PREROUTING
            dnat_rules = []
            if "PREROUTING" in chains:
                for rule in chains["PREROUTING"]["rules"]:
                    target = rule.get("target", "")
                    if "DNAT" in target or "REDIRECT" in target:
                        dnat_info = {
                            "rule_number": rule.get("rule_number"),
                            "interface": rule.get("in", ""),
                            "protocol": rule.get("protocol", ""),
                            "target": target,
                            "source": rule.get("source", ""),
                            "destination": rule.get("destination", ""),
                            "additional": rule.get("additional", ""),
                            "raw_line": rule.get("raw_line", "")
                        }
                        
                        # Parse port info dari additional field
                        additional = rule.get("additional", "")
                        if "dpt:" in additional:
                            dnat_info["destination_port"] = additional.split("dpt:")[1].split()[0]
                        if "to:" in additional:
                            dnat_info["redirect_to"] = additional.split("to:")[1].split()[0]
                        
                        dnat_rules.append(dnat_info)
            
            # Check IP forwarding
            ip_forward_result = self._execute_on_host("sysctl net.ipv4.ip_forward")
            ip_forward_enabled = False
            ip_forward_value = "0"
            
            if ip_forward_result["success"]:
                for line in ip_forward_result["stdout"].split('\n'):
                    if "net.ipv4.ip_forward" in line and "=" in line:
                        ip_forward_value = line.split('=')[1].strip()
                        ip_forward_enabled = (ip_forward_value == "1")
                        break
            
            # Calculate totals
            total_chains = len(chains)
            total_masquerade = len(masquerade_rules)
            total_dnat = len(dnat_rules)
            total_rules = sum(len(chain["rules"]) for chain in chains.values())
            
            # Summary info
            interfaces_with_nat = sorted(
                set(rule["interface"] for rule in masquerade_rules if rule["interface"])
            )
            
            return {
                "status": "success",
                "chains": chains,
                "masquerade_rules": masquerade_rules,
                "dnat_rules": dnat_rules,
                "ip_forwarding": {
                    "enabled": ip_forward_enabled,
                    "value": ip_forward_value
                },
                "summary": {
                    "total_chains": total_chains,
                    "total_rules": total_rules,
                    "total_masquerade_rules": total_masquerade,
                    "total_dnat_rules": total_dnat,
                    "ip_forwarding": "enabled" if ip_forward_enabled else "disabled",
                    "interfaces_with_nat": interfaces_with_nat,
                    "nat_enabled_interfaces": len(interfaces_with_nat)
                },
                "raw_output": rules_output  # Keep for debugging
            }
            
        except Exception as e:
            import traceback
            return {
                "status": "error", 
                "message": f"Error parsing NAT rules: {str(e)}",
                "traceback": traceback.format_exc(),
                "raw_output": rules_output  # Include raw output for debugging
            }
        
    def setup_nat(self, out_interface, clear_existing=False):
        """Setup NAT pada interface tertentu tanpa menghapus rules lain"""
        try:
            self.logger(f"Setting up NAT on {out_interface} (clear_existing={clear_existing})")
            
            # Enable IP forwarding jika belum
            ip_forward_result = self._execute_on_host("sysctl net.ipv4.ip_forward")
            if ip_forward_result["success"] and "= 1" not in ip_forward_result["stdout"]:
                self.logger("Enabling IP forwarding...")
                self._execute_on_host("sysctl -w net.ipv4.ip_forward=1")
                
                # Make persistent
                if self.os_family in ['debian', 'ubuntu']:
                    self._execute_on_host("echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-ipforward.conf")
                elif self.os_family in ['rhel', 'centos', 'fedora']:
                    self._execute_on_host("echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf")
            
            # Cek apakah rule untuk interface ini sudah ada
            check_cmd = f"iptables -t nat -L POSTROUTING -n -v | grep -i masquerade | grep {out_interface}"
            check_result = self._execute_on_host(check_cmd)
            
            if check_result["success"] and check_result["stdout"]:
                self.logger(f"NAT rule for {out_interface} already exists")
                return {
                    "status": "success",
                    "message": f"NAT rule for {out_interface} already exists",
                    "interface": out_interface,
                    "already_exists": True
                }
            
            # Hanya clear jika diminta
            clear_results = []
            if clear_existing:
                clear_result = self._execute_on_host("iptables -t nat -F")
                clear_results.append({
                    "action": "flush_nat_table",
                    "success": clear_result["success"]
                })
            
            # Add NAT rule (hanya tambah, tidak replace)
            nat_rule = f"iptables -t nat -A POSTROUTING -o {out_interface} -j MASQUERADE"
            nat_result = self._execute_on_host(nat_rule)
            
            # Verify
            verify_cmd = f"iptables -t nat -L POSTROUTING -n -v --line-numbers | grep -i masquerade"
            verify_result = self._execute_on_host(verify_cmd)
            
            rules = []
            if verify_result["success"]:
                for line in verify_result["stdout"].split('\n'):
                    if line.strip():
                        rules.append(line.strip())
            
            # Save rules
            save_result = None
            if self.os_family in ['debian', 'ubuntu']:
                save_result = self._execute_on_host("iptables-save > /etc/iptables/rules.v4")
            elif self.os_family in ['rhel', 'centos', 'fedora']:
                save_result = self._execute_on_host("service iptables save")
            
            return {
                "status": "success",
                "message": f"NAT added for {out_interface}",
                "interface": out_interface,
                "command": nat_rule,
                "rule_added": nat_result["success"],
                "clear_performed": clear_existing,
                "existing_rules": rules,
                "rules_saved": save_result["success"] if save_result else False,
                "summary": f"Added NAT for {out_interface}. Total MASQUERADE rules: {len(rules)}"
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def clear_nat(self):
        """Clear all NAT rules"""
        try:
            self._execute_on_host("iptables -t nat -F")
            
            # Save cleared rules
            if self.os_family in ['debian', 'ubuntu']:
                self._execute_on_host("iptables-save > /etc/iptables/rules.v4")
            elif self.os_family in ['rhel', 'centos', 'fedora']:
                self._execute_on_host("service iptables save")
                
            return {"status": "success", "message": "All NAT rules cleared"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # === Status Methods - MENGGUNAKAN HOST ===
    def status_all(self):
        """Get complete firewall status dari HOST"""
        result = {
            "os_family": self.os_family,
            "detected_firewall": self.firewall_type
        }
        
        # Get status based on detected firewall dari HOST
        if self.firewall_type == "ufw":
            ufw_result = self.ufw_status()
            result["ufw_status"] = ufw_result if "Error:" not in ufw_result else f"Error getting UFW status"
        elif self.firewall_type == "firewalld":
            fw_result = self.firewall_status()
            result["firewalld_status"] = fw_result if "Error:" not in fw_result else f"Error getting firewalld status"
        elif self.firewall_type == "suse":
            suse_result = self.suse_firewall("status")
            result["suse_status"] = suse_result if "Error:" not in suse_result else f"Error getting SuSEfirewall2 status"
        
        # Get iptables status dari HOST
        try:
            iptables_nat = self._execute_on_host("iptables -t nat -L -n -v")
            iptables_filter = self._execute_on_host("iptables -L -n -v")
            
            result["iptables_nat"] = iptables_nat["stdout"] if iptables_nat["success"] else f"Error: {iptables_nat.get('error')}"
            result["iptables_filter"] = iptables_filter["stdout"] if iptables_filter["success"] else f"Error: {iptables_filter.get('error')}"
        except Exception as e:
            result["iptables_error"] = f"Error: {str(e)}"
            
        return result

    def detect_firewall_type(self):
        """Detect and return firewall type"""
        return self.firewall_type

    def get_status(self):
        """Get firewall status (active/inactive) dari HOST"""
        try:
            if self.firewall_type == "ufw":
                result = self.ufw_status()
                if "Status: active" in result:
                    return "active"
                else:
                    return "inactive"
            elif self.firewall_type == "firewalld":
                result = self._execute_on_host("firewall-cmd --state")
                if result["success"] and "running" in result["stdout"].lower():
                    return "active"
                else:
                    return "inactive"
            elif self.firewall_type == "iptables":
                # Check if iptables has any rules
                result = self._execute_on_host("iptables -L -n")
                if result["success"] and "Chain INPUT" in result["stdout"]:
                    return "active"
                return "inactive"
        except Exception as e:
            self.logger(f"Error getting status: {e}")
        return "unknown"
    
    def get_default_zone(self):
        """Get default zone (for firewalld) dari HOST"""
        if self.firewall_type == "firewalld":
            try:
                result = self._execute_on_host("firewall-cmd --get-default-zone")
                if result["success"]:
                    return result["stdout"].strip()
            except Exception:
                pass
        return "N/A"
    
    def get_active_zones(self):
        """Get active zones (for firewalld) dari HOST"""
        zones = []
        if self.firewall_type == "firewalld":
            try:
                result = self._execute_on_host("firewall-cmd --get-active-zones")
                if result["success"]:
                    for line in result["stdout"].strip().split('\n'):
                        if ':' in line:
                            zone = line.split(':')[0].strip()
                            if zone:
                                zones.append(zone)
            except Exception:
                pass
        return zones
    
    def get_rules_count(self):
        """Get total number of firewall rules"""
        count = 0
        try:
            if self.firewall_type == "ufw":
                result = self._execute_on_host("ufw status numbered")
                if result["success"]:
                    # Count numbered rules like [1], [2], etc.
                    count = len(re.findall(r'\[\s*\d+\s*\]', result["stdout"]))
            
            elif self.firewall_type == "iptables":
                # Count rules in filter table
                result = self._execute_on_host("iptables -L -n --line-numbers")
                if result["success"]:
                    lines = result["stdout"].split('\n')
                    for line in lines:
                        # Count lines that look like rule entries
                        if line and re.match(r'^\s*\d+', line) and not line.startswith('Chain'):
                            count += 1
            
            elif self.firewall_type == "firewalld":
                # Count ports and services
                ports_result = self._execute_on_host("firewall-cmd --list-ports")
                services_result = self._execute_on_host("firewall-cmd --list-services")
                
                if ports_result["success"]:
                    ports = ports_result["stdout"].strip().split()
                    count += len(ports)
                if services_result["success"]:
                    services = services_result["stdout"].strip().split()
                    count += len(services)
                    
        except Exception as e:
            self.logger(f"Error counting rules: {e}")
        
        return count

    # === Helper untuk debugging ===
    def debug_host_connection(self):
        """Debug connection to host"""
        tests = [
            ("Basic host command", "echo 'host test'"),
            ("Check UFW", "which ufw"),
            ("Check firewalld", "which firewall-cmd"),
            ("Check iptables", "which iptables"),
        ]
        
        results = []
        for test_name, cmd in tests:
            result = self._execute_on_host(cmd)
            results.append({
                "test": test_name,
                "command": cmd,
                "success": result["success"],
                "output": result.get("stdout", ""),
                "error": result.get("error", "")
            })
        
        return results