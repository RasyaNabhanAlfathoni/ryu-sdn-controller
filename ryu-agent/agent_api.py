from flask import Flask, request, jsonify
from drivers.linux.network import ServerNetworkDriver
from drivers.linux.firewall import ServerFirewallDriver
from drivers.linux.service import ServerServiceDriver
from drivers.linux.system import ServerSystemDriver
from drivers.linux.wazuh_dispatcher import WazuhDispatcher
from drivers.linux.lldp import LLDPDriver
import psutil
import subprocess
import json
import datetime

app = Flask(__name__)

# Initialize drivers with logging support 
network_driver = ServerNetworkDriver()
firewall_driver = ServerFirewallDriver()
service_driver = ServerServiceDriver()
system_driver = ServerSystemDriver()
wazuh_dispatcher = WazuhDispatcher()
lldp_driver = LLDPDriver()

def log_message(message):
    # Helper untuk logging (Menampilkan IP dari sisi Agent)
    print(f"[AGENT-API] {message}")


# === NETWORK ENDPOINTS ===
@app.route('/api/network/ip/add', methods=['POST'])
def add_ip():
    # Add IP address to interface
    try:
        data = request.json
        log_message(f"POST /api/network/ip/add - {data}")
        result = network_driver.add_ip(data['interface'], data['ip_cidr'])
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in add_ip: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/network/ip/remove', methods=['POST'])
def remove_ip():
    # Remove IP address from interface
    try:
        data = request.json
        log_message(f"POST /api/network/ip/remove - {data}")
        result = network_driver.del_ip(data['interface'], data['ip_cidr'])
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in remove_ip: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/network/interface/configure', methods=['POST'])
def configure_interface():
    # Network interface configuration
    try:
        data = request.json
        log_message(f"POST /api/network/interface/configure - {data}")
        
        result = network_driver.configure_interface(
            iface=data['interface'],
            ip_cidr=data['ip_cidr'],
            gateway=data.get('gateway'),
            dns_servers=data.get('dns_servers'),
            onboot=data.get('onboot', True),
            dhcp=data.get('dhcp', False)
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in configure_interface: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/network/interface/enable', methods=['POST'])
def enable_interface():
    # Enable network interface
    try:
        data = request.json
        log_message(f"POST /api/network/interface/enable - {data}")
        result = network_driver.enable_iface(data['interface'])
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in enable_interface: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/network/interface/disable', methods=['POST'])
def disable_interface():
    # Disable network interface
    try:
        data = request.json
        log_message(f"POST /api/network/interface/disable - {data}")
        result = network_driver.disable_iface(data['interface'])
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in disable_interface: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/network/interface/<iface>/info', methods=['GET'])
def get_ip_info(iface):
    # Get IP info for specific interface
    try:
        log_message(f"GET /api/network/interface/{iface}/info")
        result = network_driver.get_ip_info(iface)
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in get_ip_info: {e}")
        return jsonify({"error": str(e)}), 500

# === Network Advanced ENDPOINTS ===

@app.route('/api/network/routing', methods=['GET'])
def get_routing_table():
    # Get routing table via driver
    try:
        log_message("GET /api/network/routing")
        result = network_driver.get_routing_table()  # Call driver
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in get_routing_table: {e}")
        return jsonify({"error": str(e)}), 500
    

@app.route('/api/network/routing/add', methods=['POST'])
def add_route():
    # Add static route
    try:
        data = request.json
        log_message(f"POST /api/network/routing/add - {data}")
        result = network_driver.add_route(
            data['network'], 
            data.get('gateway'), 
            data.get('interface')
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in add_route: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/network/routing/delete', methods=['POST'])
def delete_route():
    # Delete static route
    try:
        data = request.json
        log_message(f"POST /api/network/routing/delete - {data}")
        result = network_driver.delete_route(
            data['network'], 
            data.get('gateway'), 
            data.get('interface')
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in delete_route: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/network/dns/set', methods=['POST'])
def set_dns():
    # Configure DNS servers
    try:
        data = request.json
        log_message(f"POST /api/network/dns/set - {data}")
        result = network_driver.set_dns_servers(data['dns_servers'])
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in set_dns: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/network/portscan', methods=['POST'])
def port_scan():
    # Port scanning via driver
    try:
        data = request.json
        log_message(f"POST /api/network/portscan - {data}")
        result = network_driver.port_scan(data.get('target'), data.get('ports'))
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in port_scan: {e}")
        return jsonify({"error": str(e)}), 500
    

# === UFW FIREWALL ENDPOINTS ===

@app.route('/api/firewall/ufw/status', methods=['GET'])
def ufw_status():
    # Get UFW firewall status
    try:
        log_message("GET /api/firewall/ufw/status")
        result = firewall_driver.ufw_status()
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in ufw_status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/ufw/enable', methods=['POST'])
def ufw_enable():
    # Enable UFW firewall
    try:
        log_message("POST /api/firewall/ufw/enable")
        result = firewall_driver.ufw_enable()
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in ufw_enable: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/ufw/disable', methods=['POST'])
def ufw_disable():
    # Disable UFW firewall
    try:
        log_message("POST /api/firewall/ufw/disable")
        result = firewall_driver.ufw_disable()
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in ufw_disable: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/ufw/reload', methods=['POST'])
def ufw_reload():
    # Reload UFW firewall
    try:
        log_message("POST /api/firewall/ufw/reload")
        result = firewall_driver.ufw_reload()
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in ufw_reload: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/ufw/reset', methods=['POST'])
def ufw_reset():
    # Reset UFW firewall
    try:
        log_message("POST /api/firewall/ufw/reset")
        result = firewall_driver.ufw_reset()
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in ufw_reset: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/ufw/allow', methods=['POST'])
def ufw_allow():
    # Allow port/protocol in UFW
    try:
        data = request.json
        log_message(f"POST /api/firewall/ufw/allow - {data}")
        result = firewall_driver.ufw_allow(data['port_proto'])
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in ufw_allow: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/ufw/deny', methods=['POST'])
def ufw_deny():
    # Deny port/protocol in UFW
    try:
        data = request.json
        log_message(f"POST /api/firewall/ufw/deny - {data}")
        result = firewall_driver.ufw_deny(data['port_proto'])
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in ufw_deny: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/ufw/delete', methods=['POST'])
def ufw_delete():
    # Delete UFW rule
    try:
        data = request.json
        log_message(f"POST /api/firewall/ufw/delete - {data}")
        result = firewall_driver.ufw_delete(data['rule'])
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in ufw_delete: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/ufw/command', methods=['POST'])
def ufw_command():
    # Execute UFW command
    try:
        data = request.json
        log_message(f"POST /api/firewall/ufw/command - {data}")

        action = data.get('action')
        direction = data.get('direction')
        port_proto = data.get('port_proto')

        if direction and port_proto:
            result = firewall_driver.ufw(action, direction, port_proto)
        elif port_proto:
            result = firewall_driver.ufw(action, port_proto)
        else:
            result = firewall_driver.ufw(action)

        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in ufw_command: {e}")
        return jsonify({"error": str(e)}), 500


# === FIREWALLD ENDPOINTS ===

@app.route('/api/firewall/firewalld/status', methods=['GET'])
def firewall_status():
    # Get firewalld status
    try:
        log_message("GET /api/firewall/firewalld/status")
        result = firewall_driver.firewall_status()
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_status: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/firewall/firewalld/list-services', methods=['GET'])
def firewalld_list_services():
    # Get list firewalld services
    try:
        log_message("GET /api/firewall/firewalld/list-services")
        result = firewall_driver.firewall_cmd("--list-services")
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewalld_list_services: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/firewalld/list-ports', methods=['GET'])
def firewalld_list_ports():
    # Get list firewalld ports
    try:
        log_message("GET /api/firewall/firewalld/list-ports")
        result = firewall_driver.firewall_cmd("--list-ports")
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewalld_list_ports: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/firewalld/reload', methods=['POST'])
def firewall_reload():
    # Reload firewalld
    try:
        log_message("POST /api/firewall/firewalld/reload")
        result = firewall_driver.firewall_reload()
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_reload: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/firewalld/add-port', methods=['POST'])
def firewall_add_port():
    # Add port to firewalld
    try:
        data = request.json
        log_message(f"POST /api/firewall/firewalld/add-port - {data}")
        result = firewall_driver.firewall_add_port(data['port_proto'])
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_add_port: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/firewalld/remove-port', methods=['POST'])
def firewall_remove_port():
    # Remove port from firewalld
    try:
        data = request.json
        log_message(f"POST /api/firewall/firewalld/remove-port - {data}")
        result = firewall_driver.firewall_remove_port(data['port_proto'])
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_remove_port: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/firewalld/enable-masquerade', methods=['POST'])
def firewall_enable_masquerade():
    # Enable masquerade in firewalld
    try:
        log_message("POST /api/firewall/firewalld/enable-masquerade")
        result = firewall_driver.firewall_enable_masquerade()
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_enable_masquerade: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/firewalld/disable-masquerade', methods=['POST'])
def firewall_disable_masquerade():
    # Disable masquerade in firewalld
    try:
        log_message("POST /api/firewall/firewalld/disable-masquerade")
        result = firewall_driver.firewall_disable_masquerade()
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_disable_masquerade: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/firewalld/command', methods=['POST'])
def firewall_command():
    # Execute firewall-cmd command
    try:
        data = request.json
        log_message(f"POST /api/firewall/firewalld/command - {data}")
        result = firewall_driver.firewall_cmd(data['args'])
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_command: {e}")
        return jsonify({"error": str(e)}), 500


# === NAT FIREWALL ENDPOINTS ===

@app.route('/api/firewall/nat/setup', methods=['POST'])
def setup_nat():
    # Setup NAT
    try:
        data = request.json
        log_message(f"POST /api/firewall/nat/setup - {data}")
        result = firewall_driver.setup_nat(data['interface'])
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in setup_nat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/nat/clear', methods=['POST'])
def clear_nat():
    # Clear NAT rules
    try:
        log_message("POST /api/firewall/nat/clear")
        result = firewall_driver.clear_nat()
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in clear_nat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/status', methods=['GET'])
def status_all():
    # Get complete all firewall status
    try:
        log_message("GET /api/firewall/status")
        result = firewall_driver.status_all()
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in status_all: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/detect', methods=['GET'])
def detect_firewall():
    # Detect firewall type
    try:
        log_message("GET /api/firewall/detect")
        result = firewall_driver.detect_firewall()
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in detect_firewall: {e}")
        return jsonify({"error": str(e)}), 500


# === NEW SERVICE ENDPOINTS ===

@app.route('/api/system/services', methods=['GET'])
def list_services():
    # List all system services
    try:
        log_message("GET /api/system/services")
        result = service_driver.list_services()
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in list_services: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/service/control', methods=['POST'])
def service_control():
    # Control system service
    try:
        data = request.json
        log_message(f"POST /api/system/service/control - {data}")
        result = service_driver.service_control(data['service'], data['action'])
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in service_control: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/service/<service>/status', methods=['GET'])
def service_status(service):
    # Get service status
    try:
        log_message(f"GET /api/system/service/{service}/status")
        result = service_driver.service_status(service)
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in service_status: {e}")
        return jsonify({"error": str(e)}), 500


# === LLDP ENDPOINTS ===

@app.route('/api/network/lldp/neighbors', methods=['GET', 'POST'])
def get_lldp_neighbors():
    """Get LLDP neighbors information"""
    try:
        data = request.json if request.method == 'POST' else {}
        log_message(f"{request.method} /api/network/lldp/neighbors - {data}")
        
        if 'iface' in data:
            result = lldp_driver.get_interface_neighbors(data['iface'])
        else:
            result = lldp_driver.get_neighbors()
            
        return jsonify({
            "status": "success",
            "data": result,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        log_message(f"Error in get_lldp_neighbors: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

@app.route('/api/network/lldp/statistics', methods=['GET'])
def get_lldp_statistics():
    """Get LLDP statistics"""
    try:
        log_message("GET /api/network/lldp/statistics")
        result = lldp_driver.get_lldp_statistics()
        return jsonify({
            "status": "success",
            "data": result,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        log_message(f"Error in get_lldp_statistics: {e}")
        return jsonify({
            "status": "error", 
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

@app.route('/api/network/lldp/status', methods=['GET'])
def get_lldp_status():
    """Get LLDP daemon status"""
    try:
        log_message("GET /api/network/lldp/status")
        result = lldp_driver.get_lldp_status()
        return jsonify({
            "status": "success",
            "data": result,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        log_message(f"Error in get_lldp_status: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }), 500


# === SYSTEM ENDPOINTS ===

@app.route('/api/system/logs', methods=['GET'])
def get_logs():
    # Get system logs via driver
    try:
        n = request.args.get('lines', 50, type=int)
        log_message(f"GET /api/system/logs?lines={n}")
        result = system_driver.get_system_logs(n)  # Call driver
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in get_logs: {e}")
        return jsonify({"error": str(e)}), 500

# === WAZUH ENDPOINTS ===
@app.route('/api/wazuh/install', methods=['POST'])
def wazuh_install():
    """Install Wazuh agent"""
    try:
        data = request.json
        log_message(f"POST /api/wazuh/install - {data}")
        result = wazuh_dispatcher.dispatch("server.wazuh.install", data)
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in wazuh_install: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/wazuh/uninstall', methods=['POST'])
def wazuh_uninstall():
    """Uninstall Wazuh agent"""
    try:
        log_message("POST /api/wazuh/uninstall")
        result = wazuh_dispatcher.dispatch("server.wazuh.uninstall", {})
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in wazuh_uninstall: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/wazuh/status', methods=['GET'])
def wazuh_status():
    """Get Wazuh agent status"""
    try:
        log_message("GET /api/wazuh/status")
        result = wazuh_dispatcher.dispatch("server.wazuh.status", {})
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in wazuh_status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/wazuh/security/overview', methods=['POST'])
def wazuh_security_overview():
    """Get security overview"""
    try:
        data = request.json
        log_message(f"POST /api/wazuh/security/overview - {data}")
        result = wazuh_dispatcher.dispatch("server.wazuh.security.overview", data)
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in wazuh_security_overview: {e}")
        return jsonify({"error": str(e)}), 500

# Health check
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "agent_api"})

if __name__ == '__main__':
    print("Starting Agent API on http://0.0.0.0:8081")
    app.run(host='0.0.0.0', port=8081, debug=False)
