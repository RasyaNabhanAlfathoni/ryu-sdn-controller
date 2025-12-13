import requests
import json
from typing import Dict, List, Optional

class ServerAPI:
    name = "AgentClient"  # Ganti nama untuk clarity

    def __init__(self, dev):
        self.agent_ip = dev.get("ip")  # IP agent (contoh: 192.168.221.163)
        self.agent_url = f"http://{self.agent_ip}:8081"  # Agent URL API endpoint
        self.device_id = dev.get("id")
        self.device_data = dev
        print(f"[AgentClient] Initialized for {self.device_id} at {self.agent_url}")

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
        """Get IP info for specific interface from agent"""
        try:
            result = self._call_agent(f"/api/network/interface/{iface}/info", logger=logger)
            
            # DEBUG LOGGING
            if logger:
                logger(f"[DEBUG] Raw get_ip_info response for {iface}: {result}")
            
            # PARSE RESPONSE 
            if isinstance(result, dict) and "ip_addresses" in result:
                # Format: {"ip_addresses": ["192.168.1.101/255.255.255.0"], ...}
                parsed_result = {
                    "interface": result.get("interface", iface),
                    "mac": result.get("mac_address", "unknown")
                }
                
                # Parse IP addresses
                ip_addresses = result.get("ip_addresses", [])
                if ip_addresses and len(ip_addresses) > 0:
                    # Ambil IP pertama
                    ip_with_netmask = ip_addresses[0]
                    if "/" in ip_with_netmask:
                        ip_parts = ip_with_netmask.split("/")
                        parsed_result["address"] = ip_parts[0]
                        parsed_result["netmask"] = ip_parts[1]  # Bisa jadi format 255.255.255.0 atau /24
                        
                        # Hitung broadcast jika perlu
                        try:
                            import ipaddress
                            # Convert netmask ke prefix jika format subnet mask
                            if "." in parsed_result["netmask"]:
                                # Netmask format: 255.255.255.0
                                mask = parsed_result["netmask"]
                                prefix = sum(bin(int(x)).count('1') for x in mask.split('.'))
                                cidr = f"{parsed_result['address']}/{prefix}"
                            else:
                                # Sudah format prefix: /24
                                cidr = f"{parsed_result['address']}/{parsed_result['netmask']}"
                            
                            network = ipaddress.IPv4Network(cidr, strict=False)
                            parsed_result["broadcast"] = str(network.broadcast_address)
                        except Exception as e:
                            if logger:
                                logger(f"[DEBUG] Cannot calculate broadcast: {e}")
                            parsed_result["broadcast"] = ""
                    else:
                        # Format tidak dikenali
                        parsed_result["address"] = ip_with_netmask
                        parsed_result["netmask"] = ""
                        parsed_result["broadcast"] = ""
                else:
                    # Tidak ada IP addresses
                    parsed_result["address"] = ""
                    parsed_result["netmask"] = ""
                    parsed_result["broadcast"] = ""
                
                if logger:
                    logger(f"[DEBUG] Parsed get_ip_info response: {parsed_result}")
                
                return parsed_result
            else:
                # Fallback ke format lama
                if isinstance(result, dict):
                    # Tambahkan field default jika tidak ada
                    if "address" not in result or not result["address"]:
                        result["address"] = ""
                    if "netmask" not in result or not result["netmask"]:
                        result["netmask"] = ""
                    if "broadcast" not in result or not result["broadcast"]:
                        result["broadcast"] = ""
                    if "mac" not in result or not result["mac"]:
                        result["mac"] = result.get("mac_address", "unknown")
                else:
                    # Jika bukan dict, buat dict kosong
                    result = {
                        "address": "",
                        "netmask": "", 
                        "broadcast": "",
                        "mac": "unknown"
                    }
                
                return result
                
        except Exception as e:
            if logger:
                logger(f"[ERROR] get_ip_info failed: {e}")
            return {
                "address": "",
                "netmask": "", 
                "broadcast": "",
                "mac": "unknown",
                "error": str(e)
            }
    

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
    
    
    # === Firewall UFW Management Methods ===
    
    def ufw_status(self, logger=None):
        """Get UFW firewall status from agent"""
        return self._call_agent("/api/firewall/ufw/status", logger=logger)
    
    def ufw_enable(self, logger=None):
        """Enable UFW firewall on agent"""
        try:
            # 1. FIRST: Allow port 8081 for API access
            allow_result = self._call_agent("/api/firewall/ufw/allow", {
                "port_proto": "8081/tcp"
            }, logger=logger)
            
            if logger:
                logger(f"Allow port 8081 result: {allow_result}")
            
            # 2. THEN: Enable UFW
            enable_result = self._call_agent("/api/firewall/ufw/enable", data={}, logger=logger)
            
            return {
                "allow_port_8081": allow_result,
                "enable_ufw": enable_result
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
        return self._call_agent("/api/firewall/ufw/reset", data={}, logger=logger)
    
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
    
    def firewall_status(self, logger=None):
        """Get firewalld status from agent"""
        return self._call_agent("/api/firewall/firewalld/status", logger=logger)

    def firewalld_list_services(self, logger=None):
        """List firewalld services from agent"""
        return self._call_agent("/api/firewall/firewalld/list-services", logger=logger)

    def firewalld_list_ports(self, logger=None):
        """List firewalld ports from agent"""
        return self._call_agent("/api/firewall/firewalld/list-ports", logger=logger)
    
    def firewall_reload(self, logger=None):
        """Reload firewalld on agent"""
        return self._call_agent("/api/firewall/firewalld/reload", logger=logger)
    
    def firewall_add_port(self, port_proto, logger=None):
        """Add port to firewalld on agent"""
        return self._call_agent("/api/firewall/firewalld/add-port", {
            "port_proto": port_proto
        }, logger=logger)
    
    def firewall_remove_port(self, port_proto, logger=None):
        """Remove port from firewalld on agent"""
        return self._call_agent("/api/firewall/firewalld/remove-port", {
            "port_proto": port_proto
        }, logger=logger)
    
    def firewall_enable_masquerade(self, logger=None):
        """Enable masquerade in firewalld on agent"""
        return self._call_agent("/api/firewall/firewalld/enable-masquerade", logger=logger)
    
    def firewall_disable_masquerade(self, logger=None):
        """Disable masquerade in firewalld on agent"""
        return self._call_agent("/api/firewall/firewalld/disable-masquerade", logger=logger)
    
    def firewall_cmd(self, args, logger=None):
        """Run firewall-cmd on agent"""
        return self._call_agent("/api/firewall/firewalld/command", {
            "args": args
        }, logger=logger)

    
    # === NAT Firewall Management Methods ===
    
    def setup_nat(self, interface, logger=None):
        """Setup NAT on agent"""
        return self._call_agent("/api/firewall/nat/setup", {
            "interface": interface
        }, logger=logger)
    
    def clear_nat(self, logger=None):
        """Clear NAT rules on agent"""
        return self._call_agent("/api/firewall/nat/clear", logger=logger)
    
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


    # === System Monitoring Methods ===
    
    def get_logs(self, n=50, logger=None):
        """Get system logs from agent"""
        return self._call_agent(f"/api/system/logs?lines={n}", logger=logger)

    ## === Wazuh Commands ===
    def wazuh_install(self, manager_ip, agent_key, agent_name, logger=None):
        """Trigger Wazuh agent installation via agent API"""
        return self._call_agent("/api/wazuh/install", {
            "manager_ip": manager_ip,
            "agent_key": agent_key, 
            "agent_name": agent_name
        }, logger=logger)

    def wazuh_uninstall(self, logger=None):
        """Trigger Wazuh agent uninstallation via agent API"""
        return self._call_agent("/api/wazuh/uninstall", logger=logger)

    def wazuh_agent_status(self, logger=None):
        """Get Wazuh agent status via agent API"""
        return self._call_agent("/api/wazuh/status", logger=logger)