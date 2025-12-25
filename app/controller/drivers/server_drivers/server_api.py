import requests
import json
import os
from typing import Dict, List, Optional

class ServerAPI:
    name = "AgentClient"  # Ganti nama untuk clarity

    def __init__(self, dev):
        # === VALIDASI DEVICE OBJECT ===
        if not isinstance(dev, dict):
            raise ValueError("dev must be a dict")

        # === IP AGENT (WAJIB ADA) ===
        self.agent_ip = dev.get("main_ip_address")
        if not self.agent_ip:
            raise ValueError("main_ip_address is missing in device data")

        # === PORT AGENT (URUTAN PRIORITAS JELAS) ===
        # 1. dari dev (database / memory)
        # 2. dari ENV
        # 3. fallback HARDCODED
        raw_port = (
            dev.get("api_port")
            or os.environ.get("SERVER_AGENT_API_PORT")
            or 8081
        )

        try:
            self.agent_port = int(raw_port)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid agent port value: {raw_port}")

        # === FINAL AGENT URL ===
        self.agent_url = f"http://{self.agent_ip}:{self.agent_port}"

        # === IDENTITAS DEVICE ===
        self.device_id = dev.get("id") or dev.get("device_id") or "unknown"
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
        """Get IP info for specific interface from agent"""
        try:
            result = self._call_agent(f"/api/network/interface/{iface}/info", logger=logger)
            
            # DEBUG LOGGING
            if logger:
                logger(f"[DEBUG] Raw get_ip_info response for {iface}: {result}")
            
            # PARSE RESPONSE 
            if isinstance(result, dict):
                # DAPATKAN STATUS (default 'unknown' jika tidak ada)
                interface_status = result.get("status", "unknown")
                
                parsed_result = {
                    "interface": result.get("interface", iface),
                    "mac": result.get("mac_address", "unknown"),
                    "address": "",
                    "netmask": "",
                    "broadcast": "",
                    "status": interface_status 
                }
                
                # SIMPAN SEMUA IP ADDRESSES
                if "ip_addresses" in result and isinstance(result["ip_addresses"], list):
                    parsed_result["ip_addresses"] = result["ip_addresses"]
                    
                    # Ambil IP pertama untuk backward compatibility
                    if result["ip_addresses"] and len(result["ip_addresses"]) > 0:
                        first_ip = result["ip_addresses"][0]
                        if "/" in first_ip:
                            ip_parts = first_ip.split("/")
                            parsed_result["address"] = ip_parts[0]
                            parsed_result["netmask"] = ip_parts[1]
                            
                            # Hitung broadcast untuk IP pertama
                            try:
                                import ipaddress
                                if "." in parsed_result["netmask"]:
                                    mask = parsed_result["netmask"]
                                    prefix = sum(bin(int(x)).count('1') for x in mask.split('.'))
                                    cidr = f"{parsed_result['address']}/{prefix}"
                                else:
                                    cidr = f"{parsed_result['address']}/{parsed_result['netmask']}"
                                
                                network = ipaddress.IPv4Network(cidr, strict=False)
                                parsed_result["broadcast"] = str(network.broadcast_address)
                            except Exception as e:
                                if logger:
                                    logger(f"[DEBUG] Cannot calculate broadcast: {e}")
                else:
                    # Format lama (single IP)
                    parsed_result["address"] = result.get("address", "")
                    parsed_result["netmask"] = result.get("netmask", "")
                    parsed_result["broadcast"] = result.get("broadcast", "")
                    
                    # Buat array ip_addresses dari data lama
                    if parsed_result["address"]:
                        if parsed_result["netmask"]:
                            parsed_result["ip_addresses"] = [f"{parsed_result['address']}/{parsed_result['netmask']}"]
                        else:
                            parsed_result["ip_addresses"] = [parsed_result["address"]]
                    else:
                        parsed_result["ip_addresses"] = []
                
                if logger:
                    logger(f"[DEBUG] Parsed get_ip_info response: {parsed_result}")
                
                return parsed_result
            else:
                # Fallback
                return {
                    "interface": iface,
                    "address": "",
                    "netmask": "", 
                    "broadcast": "",
                    "mac": "unknown",
                    "ip_addresses": [],
                    "status": "unknown"
                }
                
        except Exception as e:
            if logger:
                logger(f"[ERROR] get_ip_info failed: {e}")
            return {
                "interface": iface,
                "address": "",
                "netmask": "", 
                "broadcast": "",
                "mac": "unknown",
                "ip_addresses": [],
                "status": "unknown",
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