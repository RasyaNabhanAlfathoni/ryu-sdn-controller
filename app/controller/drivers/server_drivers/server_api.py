import requests
import json
import os
from typing import Dict, List, Optional

class ServerAPI:
    name = "AgentClient"  # Ganti nama untuk clarity

    def __init__(self, dev):
        self.agent_ip = dev.get("main_ip_address")  # IP agent (contoh: 192.168.221.163)
        self.controller_port = int(os.environ.get("CONTROLLER_PORT", 9090))
        self.agent_port = (dev.get("api_port") or int(os.environ.get("SERVER_AGENT_API_PORT", 8081))) # Port Agent
        self.agent_url = f"http://{self.agent_ip}:{self.agent_port}"  # Agent URL API endpoint
        self.device_id = dev.get("id")
        self.device_data = dev

        # === DEBUG LOG (PENTING) ===
        print(
            f"[AgentClient] Initialized\n"
            f"  device_id : {self.device_id}\n"
            f"  agent_ip  : {self.agent_ip}\n"
            f"  agent_port: {self.agent_port}\n"
            f"  agent_url : {self.agent_url}"
        )


    def _call_agent(self, endpoint, data=None, logger=None, method=None):
        """Call agent HTTP API"""
        try:
            url = f"{self.agent_url}{endpoint}"
            if logger:
                logger(f"Calling agent API: {url}")
            
            headers = {'Content-Type': 'application/json'}
            timeout = 300
            
            # Debug: Determine method
            if method:
                http_method = method
            elif data is not None:
                http_method = 'POST'
            else:
                http_method = 'GET'
                
            if logger:
                logger(f"Using HTTP method: {http_method}")
            
            if http_method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            else:  # GET
                response = requests.get(url, headers=headers, timeout=timeout)
                    
            if response.status_code == 200:
                result = response.json()
                if logger:
                    logger(f"Agent response: {result}")
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                if logger:
                    logger(f"Agent error: {error_msg}")
                return {"error": error_msg}
                    
        except requests.exceptions.Timeout:
            error_msg = "Request timeout - agent not responding"
            if logger:
                logger(f"Agent timeout: {error_msg}")
            return {"error": error_msg}
        except requests.exceptions.ConnectionError:
            error_msg = "Connection refused - agent API not available"
            if logger:
                logger(f"Agent connection error: {error_msg}")
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            if logger:
                logger(f"Agent unexpected error: {error_msg}")
            return {"error": error_msg}


    # === IP Management Methods ===
    
    def add_ip(self, iface, ip_cidr, logger=None):
        """Add IP address to interface on agent"""
        return self._call_agent("/api/network/ip/add", {
            "interface": iface,
            "ip_cidr": ip_cidr
        }, logger=logger)
    
    def del_ip(self, iface, ip_cidr, logger=None):
        """Remove IP address from interface on agent"""
        return self._call_agent("/api/network/ip/remove", {
            "interface": iface,
            "ip_cidr": ip_cidr
        }, logger=logger)
    
    def configure_interface(self, iface, ip_cidr, gateway=None, dns_servers=None, onboot=True, logger=None, dhcp=False):
        """Network interface configuration on agent"""
        return self._call_agent("/api/network/interface/configure", {
            "interface": iface,
            "ip_cidr": ip_cidr,
            "gateway": gateway,
            "dns_servers": dns_servers,
            "onboot": onboot,
            "dhcp": dhcp
        }, logger=logger)
        
    def enable_interface(self, iface, logger=None):
        """Enable network interface on agent"""
        return self._call_agent("/api/network/interface/enable", {
            "interface": iface
        }, logger=logger)
    
    def disable_interface(self, iface, logger=None):
        """Disable network interface on agent"""
        return self._call_agent("/api/network/interface/disable", {
            "interface": iface
        }, logger=logger)

    def get_ip_info(self, iface, logger=None):
        try:
            result = self._call_agent(f"/api/network/interface/{iface}/info", logger=logger)

            if logger:
                logger(f"[DEBUG] Raw get_ip_info response for {iface}: {result}")

            if not isinstance(result, dict):
                return {
                    "interface": iface,
                    "address": "",
                    "netmask": "",
                    "network": "",
                    "broadcast": "",
                    "mac": "unknown",
                    "ip_addresses": [],
                    "status": "unknown",
                    "error": "Invalid response type from agent"
                }

            parsed_result = {
                "interface": result.get("interface", iface),
                "mac": result.get("mac_address", "unknown"),
                "ip_addresses": [],
                "status": result.get("status", "unknown")
            }

            if isinstance(result.get("ip_addresses"), list):
                parsed_result["ip_addresses"] = result["ip_addresses"]

                if result["ip_addresses"]:
                    first = result["ip_addresses"][0]
                    if isinstance(first, dict):
                        parsed_result["primary_ip"] = {
                            "address": first.get("address", ""),
                            "netmask": first.get("netmask", ""),
                            "cidr": first.get("cidr", ""),
                            "network": first.get("network", ""),
                            "broadcast": first.get("broadcast", "")
                        }

                        parsed_result["address"] = first.get("address", "")
                        parsed_result["netmask"] = first.get("netmask", "")
                        parsed_result["network"] = first.get("network", "")
                        parsed_result["broadcast"] = first.get("broadcast", "")
            else:
                parsed_result["address"] = result.get("address", "")
                parsed_result["netmask"] = result.get("netmask", "")
                parsed_result["network"] = result.get("network", "")
                parsed_result["broadcast"] = result.get("broadcast", "")

                if parsed_result["address"]:
                    if parsed_result["netmask"]:
                        parsed_result["ip_addresses"] = [
                            f"{parsed_result['address']}/{parsed_result['netmask']}"
                        ]
                    else:
                        parsed_result["ip_addresses"] = [parsed_result["address"]]

            import ipaddress

            if parsed_result.get("ip_addresses"):
                first = parsed_result["ip_addresses"][0]

                if isinstance(first, str) and "/" in first:
                    addr, mask = first.split("/", 1)

                    parsed_result["address"] = addr
                    parsed_result["netmask"] = mask

                    prefix = sum(bin(int(x)).count("1") for x in mask.split("."))
                    net = ipaddress.IPv4Network(f"{addr}/{prefix}", strict=False)

                    parsed_result["network"] = str(net.network_address)
                    parsed_result["broadcast"] = str(net.broadcast_address)

                    parsed_result["primary_ip"] = {
                        "address": addr,
                        "netmask": mask,
                        "cidr": f"{addr}/{prefix}",
                        "network": parsed_result["network"],
                        "broadcast": parsed_result["broadcast"]
                    }

            if logger:
                logger(f"[DEBUG] Parsed get_ip_info response: {parsed_result}")

            return parsed_result

        except Exception as e:
            if logger:
                logger(f"[ERROR] get_ip_info failed: {e}")
            return {
                "interface": iface,
                "address": "",
                "netmask": "",
                "network": "",
                "broadcast": "",
                "mac": "unknown",
                "ip_addresses": [],
                "status": "unknown",
                "error": str(e)
            }
    
    def list_interfaces(self, logger=None):
        """List all network interfaces"""
        return self._call_agent("/api/network/interfaces", logger=logger)

    # === Advanced Network Management Methods ===
    
    def port_scan(self, target, ports=None, logger=None):
        """Port scanning"""
        return self._call_agent("/api/network/portscan", {
            "target": target,
            "ports": ports
        }, logger=logger)
    
    def get_routing_table(self, logger=None):
        """Get routing table"""
        return self._call_agent("/api/network/routing", logger=logger)

    def add_route(self, network, gateway=None, interface=None, logger=None):
        """Add static route"""
        data = {"network": network}
        if gateway:
            data["gateway"] = gateway
        if interface:
            data["interface"] = interface
        
        return self._call_agent(
            "/api/network/routing/add", 
            method="POST", 
            data=data,
            logger=logger
        )

    def delete_route(self, network, gateway=None, interface=None, logger=None):
        """Delete static route"""
        data = {"network": network}
        if gateway:
            data["gateway"] = gateway
        if interface:
            data["interface"] = interface
        
        return self._call_agent(
            "/api/network/routing/delete", 
            method="POST", 
            data=data,
            logger=logger
        )
    
    
    # === Firewall UFW Management Methods ===
    
    def ufw_status(self, logger=None):
        """Get UFW firewall status from agent"""
        return self._call_agent("/api/firewall/ufw/status", logger=logger)
    
    def ufw_enable(self, logger=None):
        """Enable UFW firewall on agent with essential ports"""
        try:
            # List port yang harus di-allow sebelum enable UFW
            essential_ports = [
                "22/tcp",                        # SSH
                "514/tcp", "1514/tcp", "1515/tcp", "1516/tcp", # Logging
                "55000", "9200",                 # Wazuh
                "9100", "3000",                  # Logging Tools
                f"{self.agent_port}/tcp",        # Agent API
                f"{self.controller_port}/tcp",   # Controller
            ]
            
            allow_results = {}
            
            # Allow semua port penting
            for port_proto in essential_ports:
                if logger:
                    logger(f"Allowing port {port_proto} before enabling UFW")
                
                allow_result = self._call_agent("/api/firewall/ufw/allow", {
                    "port_proto": port_proto
                }, logger=logger)
                
                allow_results[f"allow_{port_proto.replace('/', '_')}"] = allow_result
                
                if logger:
                    logger(f"Allow port {port_proto} result: {allow_result}")
            
            # Enable UFW
            enable_result = self._call_agent("/api/firewall/ufw/enable", data={}, logger=logger)
            
            return {
                **allow_results,  # Include semua allow results
                "enable_ufw": enable_result,
                "essential_ports_allowed": essential_ports
            }
        except Exception as e:
            return {"error": str(e)}
    
    def ufw_disable(self, logger=None):
        """Disable UFW firewall on agent"""
        return self._call_agent("/api/firewall/ufw/disable", data={}, logger=logger)
    
    def ufw_reload(self, logger=None):
        """Reload UFW firewall on agent"""
        return self._call_agent("/api/firewall/ufw/reload", data={}, logger=logger)
    
    def ufw_reset(self, logger=None):
        """Reset UFW firewall on agent"""
        try:
            # Reset UFW dulu
            reset_result = self._call_agent("/api/firewall/ufw/reset", data={}, logger=logger)
            
            if logger:
                logger(f"UFW reset result: {reset_result}")
            
            # List port yang harus di-allow setelah reset
            essential_ports = [
                "22/tcp",                        # SSH
                "514/tcp", "1514/tcp", "1515/tcp", "1516/tcp", # Logging
                "55000", "9200",                 # Wazuh
                "9100", "3000",                  # Logging Tools
                f"{self.agent_port}/tcp",        # Agent API
                f"{self.controller_port}/tcp",   # Controller
            ]
            
            allow_results = {}
            
            # Allow semua port penting setelah reset
            for port_proto in essential_ports:
                allow_result = self._call_agent("/api/firewall/ufw/allow", {
                    "port_proto": port_proto
                }, logger=logger)
                
                allow_results[f"allow_{port_proto.replace('/', '_')}"] = allow_result
                
                if logger:
                    logger(f"Allow agent port {port_proto} after reset: {allow_result}")
            
            return {
                "reset_ufw": reset_result,
                **allow_results,  # Include semua allow results
                "essential_ports_allowed": essential_ports
            }
        except Exception as e:
            return {"error": str(e)}
    
    def ufw_allow(self, port_proto, logger=None):
        """Allow port/protocol in UFW on agent"""
        return self._call_agent("/api/firewall/ufw/allow", {
            "port_proto": port_proto
        }, logger=logger)
    
    def ufw_deny(self, port_proto, logger=None):
        """Deny port/protocol in UFW on agent"""
        return self._call_agent("/api/firewall/ufw/deny", {
            "port_proto": port_proto
        }, logger=logger)
    
    def ufw_delete(self, rule, logger=None):
        """Delete UFW rule on agent"""
        return self._call_agent("/api/firewall/ufw/delete", {
            "rule": rule
        }, logger=logger)

    def ufw(self, action, direction=None, port_proto=None, logger=None):
        """Generic UFW command on agent"""
        # Ini POST request dengan data
        data = {"action": action}
        if direction:
            data["direction"] = direction
        if port_proto:
            data["port_proto"] = port_proto
            
        return self._call_agent("/api/firewall/ufw/command", data, logger=logger)

    
    # === Firewalld Management Methods ===
    def firewalld_enable(self, logger=None):
        """Enable firewalld"""
        try:
            essential_ports = [
                "22/tcp",                        # SSH
                "514/tcp", "1514/tcp", "1515/tcp", "1516/tcp", # Logging
                "55000", "9200",                 # Wazuh
                "9100", "3000",                  # Logging Tools
                f"{self.agent_port}/tcp",        # Agent API
                f"{self.controller_port}/tcp",   # Controller
            ]
            
            if logger:
                logger(f"Essential ports: {essential_ports}")
            
            # 1. Pre-configure firewalld rules SEBELUM start
            pre_config_results = {}
            
            for port_proto in essential_ports:
                if logger:
                    logger(f"Pre-configuring port {port_proto}...")
                
                # Gunakan direct command ke agent untuk tambah port
                result = self.firewall_offline_cmd(
                    f"--add-port={port_proto} --zone=public",
                    logger=logger
                )
                pre_config_results[f"pre_config_{port_proto.replace('/', '_')}"] = result
            
            # Juga pre-configure ssh service
            ssh_result = self.firewall_offline_cmd(
                "--add-service=ssh --zone=public",
                logger=logger
            )
            pre_config_results["pre_config_ssh_service"] = ssh_result
            
            # 2. SEKARANG enable firewalld
            if logger:
                logger("Enabling firewalld service...")
            
            enable_result = self._call_agent("/api/firewall/firewalld/enable", logger=logger, method='POST')
            
            # 3. Reload untuk apply pre-configured rules
            reload_result = self._call_agent("/api/firewall/firewalld/reload", logger=logger, method='POST')
            
            return {
                "pre_configuration": pre_config_results,
                "enable_firewalld": enable_result,
                "reload_firewalld": reload_result,
                "essential_ports": essential_ports,
                "message": "Firewalld enabled with pre-configured essential ports"
            }
        except Exception as e:
            return {"error": str(e)}

    def firewalld_disable(self, logger=None):
        """Disable and stop firewalld service"""
        return self._call_agent("/api/firewall/firewalld/disable", logger=logger, method='POST')
    
    def firewalld_list_services(self, zone=None, logger=None):
        """List firewalld services dari agent dengan optional zone"""
        if zone:
            return self.firewall_cmd(f"--list-services --zone={zone}", logger=logger)
        else:
            return self._call_agent("/api/firewall/firewalld/list-services", logger=logger)

    def firewalld_list_ports(self, zone=None, logger=None):
        """List firewalld ports dari agent dengan optional zone"""
        if zone:
            return self.firewall_cmd(f"--list-ports --zone={zone}", logger=logger)
        else:
            return self._call_agent("/api/firewall/firewalld/list-ports", logger=logger)

    def firewall_status(self, zone=None, logger=None):
        """Get firewalld status dari agent dengan optional zone"""    
        return self.firewall_cmd(f"--list-all --zone=zone", logger=logger)
    
    def firewall_reload(self, logger=None):
        """Reload firewalld on agent with essential ports"""
        try:
            # List port yang harus di-allow sebelum reload
            essential_ports = [
                "22/tcp",                        # SSH
                "514/tcp", "1514/tcp", "1515/tcp", "1516/tcp", # Logging
                "55000", "9200",                 # Wazuh
                "9100", "3000",                  # Logging Tools
                f"{self.agent_port}/tcp",        # Agent API
                f"{self.controller_port}/tcp",   # Controller
            ]
            
            ensure_results = {}
            
            # Ensure semua port penting di-allow
            for port_proto in essential_ports:
                if logger:
                    logger(f"Ensuring port {port_proto} is allowed in firewalld")
                
                ensure_result = self._call_agent("/api/firewall/firewalld/add-port", {
                    "port_proto": port_proto
                }, logger=logger)
                
                ensure_results[f"ensure_{port_proto.replace('/', '_')}"] = ensure_result
                
                if logger:
                    logger(f"Ensure port {port_proto} result: {ensure_result}")
            
            # Reload firewalld
            reload_result = self._call_agent("/api/firewall/firewalld/reload", logger=logger, method='POST')
            
            return {
                **ensure_results,  # Include semua ensure results
                "reload_firewalld": reload_result,
                "essential_ports_ensured": essential_ports
            }
        except Exception as e:
            return {"error": str(e)}
    
    def firewall_add_port(self, port_proto, zone="public", logger=None):
        """Add port to firewalld on agent dengan zone support"""
        # Jika port_proto adalah string kosong atau None, gunakan agent port
        if not port_proto:
            port_proto = f"{self.agent_port}/tcp"
            if logger:
                logger(f"No port specified, using agent port: {port_proto}")
        
        return self._call_agent("/api/firewall/firewalld/add-port", {
            "port_proto": port_proto,
            "zone": zone
        }, logger=logger)

    def firewall_remove_port(self, port_proto, zone="public", logger=None):
        """Remove port from firewalld on agent dengan zone support"""
        # Jangan izinkan remove port penting (agent, controller, ssh)
        essential_ports = [
            f"{self.agent_port}/tcp",
            f"{self.controller_port}/tcp",
            "22/tcp"
        ]
        
        if port_proto in essential_ports and zone == "public":
            warning_msg = f"Cannot remove essential port from public zone: {port_proto}"
            if logger:
                logger(f"WARNING: {warning_msg}")
            return {"warning": warning_msg, "port_proto": port_proto, "zone": zone, "essential": True}
        
        return self._call_agent("/api/firewall/firewalld/remove-port", {
            "port_proto": port_proto,
            "zone": zone
        }, logger=logger)
    
    def firewall_enable_masquerade(self, zone="public", logger=None):
        """Enable masquerade in firewalld dengan zone support"""
        try:
            # Ensure port penting sebelum enable masquerade
            essential_ports = [
                "22/tcp",                        # SSH
                "514/tcp", "1514/tcp", "1515/tcp", "1516/tcp", # Logging
                "55000", "9200",                 # Wazuh
                "9100", "3000",                  # Logging Tools
                f"{self.agent_port}/tcp",        # Agent API
                f"{self.controller_port}/tcp",   # Controller
            ]
            
            ensure_results = {}
            for port_proto in essential_ports:
                ensure_result = self._call_agent("/api/firewall/firewalld/add-port", {
                    "port_proto": port_proto,
                    "zone": zone
                }, logger=logger)
                ensure_results[f"ensure_{port_proto.replace('/', '_')}"] = ensure_result
            
            # Enable masquerade dengan zone
            masquerade_result = self._call_agent("/api/firewall/firewalld/enable-masquerade", {
                "zone": zone
            }, logger=logger)
            
            return {
                **ensure_results,
                "enable_masquerade": masquerade_result,
                "zone": zone,
                "essential_ports_ensured": essential_ports
            }
        except Exception as e:
            return {"error": str(e)}

    def firewall_disable_masquerade(self, zone="public", logger=None):
        """Disable masquerade in firewalld dengan zone support"""
        try:
            # Ensure port penting sebelum disable masquerade
            essential_ports = [
                "22/tcp",                        # SSH
                "514/tcp", "1514/tcp", "1515/tcp", "1516/tcp", # Logging
                "55000", "9200",                 # Wazuh
                "9100", "3000",                  # Logging Tools
                f"{self.agent_port}/tcp",        # Agent API
                f"{self.controller_port}/tcp",   # Controller
            ]
            
            ensure_results = {}
            for port_proto in essential_ports:
                ensure_result = self._call_agent("/api/firewall/firewalld/add-port", {
                    "port_proto": port_proto,
                    "zone": zone
                }, logger=logger)
                ensure_results[f"ensure_{port_proto.replace('/', '_')}"] = ensure_result
            
            # Disable masquerade dengan zone
            masquerade_result = self._call_agent("/api/firewall/firewalld/disable-masquerade", {
                "zone": zone
            }, logger=logger)
            
            return {
                **ensure_results,
                "disable_masquerade": masquerade_result,
                "zone": zone,
                "essential_ports_ensured": essential_ports
            }
        except Exception as e:
            return {"error": str(e)}

    def firewall_cmd(self, args, zone=None, logger=None):
        """Run firewall-cmd on agent dengan optional zone"""
        data = {"args": args}
        if zone:
            data["zone"] = zone
        
        return self._call_agent("/api/firewall/firewalld/command", data, logger=logger)

    def firewall_offline_cmd(self, args, zone=None, logger=None):
        """Run firewall-offline-cmd on agent dengan optional zone"""
        data = {"args": args}
        if zone:
            data["zone"] = zone
        
        return self._call_agent("/api/firewall/firewalld/offline-command", data, logger=logger)
    
    # === NAT Firewall Management Methods ===

    def get_nat_rules(self, logger=None):
        """Get current NAT rules from agent"""
        return self._call_agent("/api/firewall/nat/list", logger=logger)
    
    def setup_nat(self, interface, logger=None):
        """Setup NAT on agent"""
        return self._call_agent("/api/firewall/nat/setup", {
            "interface": interface
        }, logger=logger)
    
    def clear_nat(self, logger=None):
        """Clear NAT rules on agent"""
        return self._call_agent("/api/firewall/nat/clear", data={}, logger=logger, method='POST')
    
    def status_all(self, logger=None):
        """Get complete firewall status from agent"""
        return self._call_agent("/api/firewall/status", logger=logger)
    
    def detect_firewall(self, logger=None):
        """Detect firewall type on agent"""
        return self._call_agent("/api/firewall/detect", logger=logger)

    
    # === System Services Methods ===
    
    def list_services(self, logger=None):
        """List all system services"""
        return self._call_agent("/api/system/services", logger=logger)

    def service_control(self, service, action, logger=None):
        """Control system services (start/stop/restart/enable/disable)"""
        return self._call_agent("/api/system/service/control", {
            "service": service,
            "action": action
        }, logger=logger)

    def service_status(self, service, logger=None):
        """Get service status"""
        return self._call_agent(f"/api/system/service/{service}/status", logger=logger)
    

    # ===  LLDPD Methods

    def get_lldp_neighbors(self, iface: str = None, logger=None) -> Dict:
        """Get LLDP neighbors from server agent"""
        endpoint = "/api/network/lldp/neighbors"
        
        payload = {}
        if iface:
            payload['iface'] = iface
            
        try:
            if logger:
                logger(f"Fetching LLDP neighbors from agent: {endpoint}")
                
            result = self._call_agent(endpoint, payload, logger=logger)
            return result
        except Exception as e:
            error_msg = f"LLDP neighbors error: {str(e)}"
            if logger:
                logger(error_msg)
            return {"status": "error", "error": error_msg}
    
    def get_lldp_statistics(self, logger=None) -> Dict:
        """Get LLDP statistics from server agent"""
        try:
            if logger:
                logger("Fetching LLDP statistics from agent")
                
            result = self._call_agent("/api/network/lldp/statistics", logger=logger)
            return result
        except Exception as e:
            error_msg = f"LLDP statistics error: {str(e)}"
            if logger:
                logger(error_msg)
            return {"status": "error", "error": error_msg}
    
    def get_lldp_status(self, logger=None) -> Dict:
        """Get LLDP daemon status from server agent"""
        try:
            if logger:
                logger("Fetching LLDP status from agent")
                
            result = self._call_agent("/api/network/lldp/status", logger=logger)
            return result
        except Exception as e:
            error_msg = f"LLDP status error: {str(e)}"
            if logger:
                logger(error_msg)
            return {"status": "error", "error": error_msg}


    # === System Users & Group Management ===
    def get_users(self, logger=None):
        """Get list of system users"""
        return self._call_agent("/api/system/users", logger=logger)

    def get_user_info(self, username, logger=None):
        """Get detailed information about a specific user"""
        return self._call_agent(f"/api/system/users/{username}", logger=logger)

    def create_user(self, username, password=None, shell="/bin/bash", home_dir=None, logger=None):
        """Create a new system user"""
        data = {
            "username": username,
            "password": password,
            "shell": shell,
            "home_dir": home_dir
        }
        return self._call_agent("/api/system/users/create", data=data, logger=logger)

    def delete_user(self, username, remove_home=False, logger=None):
        """Delete a system user"""
        data = {
            "username": username,
            "remove_home": remove_home
        }
        return self._call_agent("/api/system/users/delete", data=data, logger=logger)

    def modify_user(self, username, shell=None, home_dir=None, logger=None):
        """Modify user properties"""
        data = {
            "username": username,
            "shell": shell,
            "home_dir": home_dir
        }
        return self._call_agent("/api/system/users/modify", data=data, logger=logger)

    def change_user_password(self, username, password, logger=None):
        """Change user password"""
        data = {
            "username": username,
            "password": password
        }
        return self._call_agent("/api/system/users/change-password", data=data, logger=logger)

    def add_user_to_group(self, username, group, logger=None):
        """Add user to group"""
        data = {
            "username": username,
            "group": group
        }
        return self._call_agent("/api/system/users/add-to-group", data=data, logger=logger)

    def remove_user_from_group(self, username, group, logger=None):
        """Remove user from group"""
        data = {
            "username": username,
            "group": group
        }
        return self._call_agent("/api/system/users/remove-from-group", data=data, logger=logger)

    def get_groups(self, logger=None):
        """Get list of system groups"""
        return self._call_agent("/api/system/groups", logger=logger)

    def create_group(self, group_name, logger=None):
        """Create a new system group"""
        data = {
            "group_name": group_name
        }
        return self._call_agent("/api/system/groups/create", data=data, logger=logger)

    def delete_group(self, group_name, logger=None):
        """Delete a system group"""
        data = {
            "group_name": group_name
        }
        return self._call_agent("/api/system/groups/delete", data=data, logger=logger)


    # === System Monitoring Methods ===
    def get_logs(self, n=50, logger=None):
        """Get system logs from agent"""
        return self._call_agent(f"/api/system/logs?lines={n}", logger=logger)
    
    def get_hostname(self, logger=None):
        """Get current hostname"""
        return self._call_agent("/api/system/hostname", logger=logger)

    def set_hostname(self, hostname, logger=None):
        """Set new hostname"""
        data = {
            "hostname": hostname
        }
        return self._call_agent("/api/system/hostname/set", data=data, logger=logger)

    def reboot(self, delay_seconds=0, logger=None):
        """Reboot the system"""
        data = {
            "delay_seconds": delay_seconds
        }
        return self._call_agent("/api/system/reboot", data=data, logger=logger)


    ## === Wazuh Commands ===
    def wazuh_install(self, manager_ip, agent_key, agent_name, logger=None):
        """Trigger Wazuh agent installation via agent API (FIXED)"""

        payload = {
            "manager_ip": manager_ip,
            "agent_key": agent_key,
            "agent_name": agent_name
        }

        if logger:
            logger(f"[WAZUH-INSTALL] Payload: {payload}")
            logger(f"[WAZUH-INSTALL] URL: {self.agent_url}/api/wazuh/install")

        try:
            response = requests.post(
                f"{self.agent_url}/api/wazuh/install",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=300
            )

            if response.status_code == 200:
                return response.json()

            return {
                "error": f"HTTP {response.status_code}: {response.text}"
            }

        except Exception as e:
            return {
                "error": f"Request failed: {str(e)}"
            }

    def wazuh_uninstall(self, logger=None):
        """Trigger Wazuh agent uninstallation via agent API"""
        return self._call_agent("/api/wazuh/uninstall", logger=logger)

    def wazuh_agent_status(self, logger=None):
        """Get Wazuh agent status via agent API"""
        return self._call_agent("/api/wazuh/status", logger=logger)
    
    def wazuh_agent_start(self, logger=None):
        """Get Wazuh agent status via agent API"""
        return self._call_agent("/api/wazuh/start", logger=logger)
    
    def wazuh_agent_stop(self, logger=None):
        """Get Wazuh agent status via agent API"""
        return self._call_agent("/api/wazuh/stop", logger=logger)
    
    def wazuh_get_config(self, logger=None) -> Dict:
        """Get Wazuh agent config remotely"""
        return self._call_agent("/api/wazuh/config", method='GET', logger=logger)

    def wazuh_update_config(self, config_content: str, logger=None) -> Dict:
        """Update Wazuh agent config remotely"""
        try:            
            # Validate config content
            if not config_content or not isinstance(config_content, str):
                return {"success": False, "error": "config_content must be a non-empty string"}
            
            # Prepare request data
            data = {"config_content": config_content}
            
            # Use requests.put directly instead of _call_agent
            url = f"{self.agent_url}/api/wazuh/config"
            headers = {'Content-Type': 'application/json'}
            
            try:
                # Send PUT request directly
                response = requests.put(
                    url,
                    json=data,
                    headers=headers,
                    timeout=30
                )
                
                # Parse response
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, dict):
                        if result.get("success") or result.get("status") == "success":
                            return {
                                "success": True,
                                "message": "Configuration updated successfully",
                                "details": result
                            }
                        else:
                            return {
                                "success": False,
                                "error": result.get("error", "Unknown error from agent"),
                                "details": result
                            }
                    else:
                        return {"success": False, "error": f"Unexpected response: {result}"}
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "status_code": response.status_code
                    }
                    
            except requests.exceptions.Timeout:
                return {"success": False, "error": "Request timeout - agent not responding"}
            except requests.exceptions.ConnectionError:
                return {"success": False, "error": "Connection refused - agent API not available"}
            except Exception as e:
                return {"success": False, "error": f"Request failed: {str(e)}"}
                
        except Exception as e:
            if logger:
                logger(f"[ERROR] wazuh_update_config failed: {str(e)}")
            return {"success": False, "error": str(e)}