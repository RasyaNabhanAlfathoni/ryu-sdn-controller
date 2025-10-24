import requests
import json

class ServerAPI:
    name = "AgentClient"  # Ganti nama untuk clarity

    def __init__(self, dev):
        self.agent_ip = dev.get("ip")  # IP agent (contoh: 192.168.221.163)
        self.agent_url = f"http://{self.agent_ip}:8080"  # Agent URL API endpoint
        self.device_id = dev.get("id")
        self.device_data = dev
        print(f"[AgentClient] Initialized for {self.device_id} at {self.agent_url}")

    def _call_agent(self, endpoint, data=None, logger=None):
        """Call agent HTTP API"""
        try:
            url = f"{self.agent_url}{endpoint}"
            if logger:
                logger(f"Calling agent API: {url}")
            
            headers = {'Content-Type': 'application/json'}
            timeout = 10
            
            if data:
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            else:
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

    def list_interfaces(self, logger=None):
        """Get list of network interfaces from agent"""
        return self._call_agent("/api/network/interfaces", logger=logger)
    
    def get_interface_details(self, logger=None):
        """Get detailed interface information from agent"""
        return self._call_agent("/api/network/interfaces/detail", logger=logger)
    
    def show_all(self, logger=None):
        """Show all interfaces with details"""
        return self.get_interface_details(logger=logger)
    
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
    
    def enable_iface(self, iface, logger=None):
        """Enable network interface on agent"""
        return self._call_agent("/api/network/interface/enable", {
            "interface": iface
        }, logger=logger)
    
    def disable_iface(self, iface, logger=None):
        """Disable network interface on agent"""
        return self._call_agent("/api/network/interface/disable", {
            "interface": iface
        }, logger=logger)
    
    def get_interface_ips(self, iface, logger=None):
        """Get IP addresses for specific interface from agent"""
        return self._call_agent(f"/api/network/interface/{iface}/ips", logger=logger)

    def get_ip_info(self, iface, logger=None):
        """Get IP info for specific interface from agent"""
        return self._call_agent(f"/api/network/interface/{iface}/info", logger=logger)

    def get_interface_status(self, iface, logger=None):
        """Get interface status from agent"""
        return self._call_agent(f"/api/network/interface/{iface}/status", logger=logger)
    

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

    def get_arp_table(self, logger=None):
        """Get ARP table"""
        return self._call_agent("/api/network/arp", logger=logger)

    
    # === Firewall UFW Management Methods ===
    
    def ufw_status(self, logger=None):
        """Get UFW firewall status from agent"""
        return self._call_agent("/api/firewall/ufw/status", logger=logger)
    
    def ufw_enable(self, logger=None):
        """Enable UFW firewall on agent"""
        return self._call_agent("/api/firewall/ufw/enable", logger=logger)
    
    def ufw_disable(self, logger=None):
        """Disable UFW firewall on agent"""
        return self._call_agent("/api/firewall/ufw/disable", logger=logger)
    
    def ufw_reload(self, logger=None):
        """Reload UFW firewall on agent"""
        return self._call_agent("/api/firewall/ufw/reload", logger=logger)
    
    def ufw_reset(self, logger=None):
        """Reset UFW firewall on agent"""
        return self._call_agent("/api/firewall/ufw/reset", logger=logger)
    
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
        if direction and port_proto:
            return self._call_agent("/api/firewall/ufw/command", {
                "action": action,
                "direction": direction,
                "port_proto": port_proto
            }, logger=logger)
        elif port_proto:
            return self._call_agent("/api/firewall/ufw/command", {
                "action": action,
                "port_proto": port_proto
            }, logger=logger)
        else:
            return self._call_agent("/api/firewall/ufw/command", {
                "action": action
            }, logger=logger)

    
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


    # === System Monitoring Methods ===
    
    def get_utilization(self, logger=None):
        """Get system utilization from agent"""
        return self._call_agent("/api/system/utilization", logger=logger)
    
    def get_logs(self, n=50, logger=None):
        """Get system logs from agent"""
        return self._call_agent(f"/api/system/logs?lines={n}", logger=logger)