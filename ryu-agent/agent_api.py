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
import argparse
import os

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

@app.route('/api/network/interfaces', methods=['GET'])
def list_interfaces():
    """List all network interfaces"""
    try:
        log_message("GET /api/network/interfaces")
        result = network_driver.list_interfaces()
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in list_interfaces: {e}")
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
@app.route('/api/firewall/firewalld/enable', methods=['POST'])
def firewalld_enable():
    """Enable and start firewalld service"""
    try:
        log_message("POST /api/firewall/firewalld/enable")
        result = firewall_driver.firewalld_enable()
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewalld_enable: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/firewalld/disable', methods=['POST'])
def firewalld_disable():
    """Disable and stop firewalld service"""
    try:
        log_message("POST /api/firewall/firewalld/disable")
        result = firewall_driver.firewalld_disable()
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewalld_disable: {e}")
        return jsonify({"error": str(e)}), 500
    
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
    # Add port to firewalld dengan zone support
    try:
        data = request.json
        port_proto = data.get('port_proto')
        zone = data.get('zone', 'public')
        
        log_message(f"POST /api/firewall/firewalld/add-port - port: {port_proto}, zone: {zone}")
        result = firewall_driver.firewall_add_port(port_proto, zone=zone)
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_add_port: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/firewalld/remove-port', methods=['POST'])
def firewall_remove_port():
    # Remove port from firewalld dengan zone support
    try:
        data = request.json
        port_proto = data.get('port_proto')
        zone = data.get('zone', 'public')
        
        log_message(f"POST /api/firewall/firewalld/remove-port - port: {port_proto}, zone: {zone}")
        result = firewall_driver.firewall_remove_port(port_proto, zone=zone)
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_remove_port: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/firewalld/enable-masquerade', methods=['POST'])
def firewall_enable_masquerade():
    # Enable masquerade in firewalld dengan zone support
    try:
        data = request.json or {}
        zone = data.get('zone', 'public')
        
        log_message(f"POST /api/firewall/firewalld/enable-masquerade - zone: {zone}")
        result = firewall_driver.firewall_enable_masquerade(zone=zone)
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_enable_masquerade: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/firewalld/disable-masquerade', methods=['POST'])
def firewall_disable_masquerade():
    # Disable masquerade in firewalld dengan zone support
    try:
        data = request.json or {}
        zone = data.get('zone', 'public')
        
        log_message(f"POST /api/firewall/firewalld/disable-masquerade - zone: {zone}")
        result = firewall_driver.firewall_disable_masquerade(zone=zone)
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_disable_masquerade: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/firewall/firewalld/command', methods=['POST'])
def firewall_command():
    # Execute firewall-cmd command dengan zone support
    try:
        data = request.json
        args = data.get('args', '')
        zone = data.get('zone')
        
        log_message(f"POST /api/firewall/firewalld/command - args: {args}, zone: {zone}")
        
        # Jika ada zone, tambah ke args
        if zone:
            args = f"--zone={zone} {args}"
        
        result = firewall_driver.firewall_cmd(args, zone=zone)
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_command: {e}")
        return jsonify({"error": str(e)}), 500

# agent_api.py - tambah endpoint baru
@app.route('/api/firewall/firewalld/offline-command', methods=['POST'])
def firewall_offline_command():
    """Execute firewall-offline-cmd command"""
    try:
        data = request.json
        args = data.get('args', '')
        zone = data.get('zone')
        
        log_message(f"POST /api/firewall/firewalld/offline-command - args: {args}, zone: {zone}")
        
        # Panggil driver method
        result = firewall_driver.firewall_offline_cmd(args, zone=zone)
        return jsonify({"status": "success", "output": result})
    except Exception as e:
        log_message(f"Error in firewall_offline_command: {e}")
        return jsonify({"error": str(e)}), 500


# === NAT FIREWALL ENDPOINTS ===

@app.route('/api/firewall/nat/list', methods=['GET'])
def list_nat():
    # Get NAT rules list
    try:
        log_message("GET /api/firewall/nat/list")
        result = firewall_driver.get_nat_rules()
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in list_nat: {e}")
        return jsonify({"error": str(e)}), 500

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
            "result": result,
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
            "result": result,
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
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in get_lldp_status: {e}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }), 500


# === SYSTEM ENDPOINTS ===

@app.route('/api/system/users', methods=['GET'])
def get_users():
    """Get list of system users"""
    try:
        log_message("GET /api/system/users")
        result = system_driver.get_users()
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in get_users: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/users/<username>', methods=['GET'])
def get_user_info(username):
    """Get detailed information about a specific user"""
    try:
        log_message(f"GET /api/system/users/{username}")
        result = system_driver.get_user_info(username)
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in get_user_info: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/users/create', methods=['POST'])
def create_user():
    """Create a new system user"""
    try:
        data = request.json
        log_message(f"POST /api/system/users/create - {data}")
        
        result = system_driver.create_user(
            username=data['username'],
            password=data.get('password'),
            shell=data.get('shell', '/bin/bash'),
            home_dir=data.get('home_dir')
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in create_user: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/users/delete', methods=['POST'])
def delete_user():
    """Delete a system user"""
    try:
        data = request.json
        log_message(f"POST /api/system/users/delete - {data}")
        
        result = system_driver.delete_user(
            username=data['username'],
            remove_home=data.get('remove_home', False)
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in delete_user: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/users/modify', methods=['POST'])
def modify_user():
    """Modify user properties"""
    try:
        data = request.json
        log_message(f"POST /api/system/users/modify - {data}")
        
        result = system_driver.modify_user(
            username=data['username'],
            shell=data.get('shell'),
            home_dir=data.get('home_dir')
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in modify_user: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/users/change-password', methods=['POST'])
def change_user_password():
    """Change user password"""
    try:
        data = request.json
        log_message(f"POST /api/system/users/change-password - {data}")
        
        # Don't log the password
        safe_data = data.copy()
        if 'password' in safe_data:
            safe_data['password'] = '******'
        log_message(f"POST /api/system/users/change-password - {safe_data}")
        
        result = system_driver.change_user_password(
            username=data['username'],
            password=data['password']
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in change_user_password: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/users/add-to-group', methods=['POST'])
def add_user_to_group():
    """Add user to group"""
    try:
        data = request.json
        log_message(f"POST /api/system/users/add-to-group - {data}")
        
        result = system_driver.add_user_to_group(
            username=data['username'],
            group=data['group']
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in add_user_to_group: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/users/remove-from-group', methods=['POST'])
def remove_user_from_group():
    """Remove user from group"""
    try:
        data = request.json
        log_message(f"POST /api/system/users/remove-from-group - {data}")
        
        result = system_driver.remove_user_from_group(
            username=data['username'],
            group=data['group']
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in remove_user_from_group: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/groups', methods=['GET'])
def get_groups():
    """Get list of system groups"""
    try:
        log_message("GET /api/system/groups")
        result = system_driver.get_groups()
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in get_groups: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/groups/create', methods=['POST'])
def create_group():
    """Create a new system group"""
    try:
        data = request.json
        log_message(f"POST /api/system/groups/create - {data}")
        
        result = system_driver.create_group(
            group_name=data['group_name']
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in create_group: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/groups/delete', methods=['POST'])
def delete_group():
    """Delete a system group"""
    try:
        data = request.json
        log_message(f"POST /api/system/groups/delete - {data}")
        
        result = system_driver.delete_group(
            group_name=data['group_name']
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in delete_group: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/hostname', methods=['GET'])
def get_hostname():
    """Get current hostname"""
    try:
        log_message("GET /api/system/hostname")
        result = system_driver.get_hostname()
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in get_hostname: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/hostname/set', methods=['POST'])
def set_hostname():
    """Set new hostname"""
    try:
        data = request.json
        log_message(f"POST /api/system/hostname/set - {data}")
        
        result = system_driver.set_hostname(
            hostname=data['hostname']
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in set_hostname: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/reboot', methods=['POST'])
def reboot():
    """Reboot the system"""
    try:
        data = request.json
        log_message("POST /api/system/reboot")
        
        result = system_driver.reboot(
            delay_seconds=data.get('delay_seconds', 0)
        )
        return jsonify(result)
    except Exception as e:
        log_message(f"Error in reboot: {e}")
        return jsonify({"error": str(e)}), 500

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
        import sys 
        import traceback
        # Debug 1: Log bahwa endpoint dipanggil
        print("=== DEBUG: /api/wazuh/install called ===", file=sys.stderr)
        print(f"Headers: {dict(request.headers)}", file=sys.stderr)
        
        # Debug 2: Cek data JSON
        if not request.is_json:
            print("ERROR: Request is not JSON", file=sys.stderr)
            return jsonify({"error": "Request must be JSON", "success": False}), 400
        
        data = request.get_json(silent=True)  # silent=True untuk menghindari error parsing
        print(f"DEBUG: Raw data: {data}", file=sys.stderr)
        print(f"DEBUG: Type of data: {type(data)}", file=sys.stderr)
        
        if data is None:
            print("ERROR: JSON data is None or invalid", file=sys.stderr)
            return jsonify({"error": "Invalid JSON data", "success": False}), 400
        
        # Debug 3: Validasi data adalah dict
        if not isinstance(data, dict):
            print(f"ERROR: data is not dict, it's {type(data)}", file=sys.stderr)
            return jsonify({"error": f"Data must be dictionary, got {type(data)}", "success": False}), 400
        
        # Debug 4: Log semua parameter
        print(f"DEBUG: manager_ip = {data.get('manager_ip')}", file=sys.stderr)
        print(f"DEBUG: agent_key = {data.get('agent_key')}", file=sys.stderr)
        print(f"DEBUG: agent_name = {data.get('agent_name')}", file=sys.stderr)
        
        # Debug 5: Import dispatcher
        try:
            from drivers.linux.wazuh_dispatcher import WazuhDispatcher
            print("DEBUG: WazuhDispatcher import successful", file=sys.stderr)
        except ImportError as e:
            print(f"ERROR: Cannot import WazuhDispatcher: {e}", file=sys.stderr)
            return jsonify({"error": f"Import error: {e}", "success": False}), 500
        
        # Debug 6: Create dispatcher
        try:
            dispatcher = WazuhDispatcher(logger=lambda msg: print(f"[Dispatcher] {msg}", file=sys.stderr))
            print("DEBUG: WazuhDispatcher created", file=sys.stderr)
        except Exception as e:
            print(f"ERROR: Cannot create WazuhDispatcher: {e}", file=sys.stderr)
            return jsonify({"error": f"Cannot create dispatcher: {e}", "success": False}), 500
        
        # Debug 7: Dispatch action
        print("DEBUG: Dispatching action...", file=sys.stderr)
        result = dispatcher.dispatch("server.wazuh.install", data)
        
        # Debug 8: Log result
        print(f"DEBUG: Result from dispatch: {result}", file=sys.stderr)
        print(f"DEBUG: Type of result: {type(result)}", file=sys.stderr)
        
        # Debug 9: Validasi result
        if not isinstance(result, dict):
            print(f"ERROR: Result is not dict, it's {type(result)}", file=sys.stderr)
            return jsonify({"error": f"Dispatcher returned non-dict: {type(result)}", "success": False}), 500
        
        # Debug 10: Return result
        print("DEBUG: Returning JSON response", file=sys.stderr)
        return jsonify(result)
        
    except Exception as e:
        print(f"CRITICAL ERROR in wazuh_install: {e}", file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        return jsonify({"error": f"Server error: {str(e)}", "success": False}), 500

@app.route('/api/wazuh/uninstall', methods=['GET'])
def wazuh_uninstall():
    """Uninstall Wazuh agent"""
    try:
        import sys
        import traceback
        
        print("=== DEBUG: /api/wazuh/uninstall called ===", file=sys.stderr)
        
        # Import dispatcher
        try:
            from drivers.linux.wazuh_dispatcher import WazuhDispatcher
            print("DEBUG: WazuhDispatcher import successful", file=sys.stderr)
        except ImportError as e:
            print(f"ERROR: Cannot import WazuhDispatcher: {e}", file=sys.stderr)
            return jsonify({"error": f"Import error: {e}", "success": False}), 500
        
        # Create dispatcher
        dispatcher = WazuhDispatcher(logger=lambda msg: print(f"[Dispatcher] {msg}", file=sys.stderr))
        
        # Dispatch action
        result = dispatcher.dispatch("server.wazuh.uninstall", {})
        
        print(f"DEBUG: Result from dispatch: {result}", file=sys.stderr)
        return jsonify(result)
        
    except Exception as e:
        print(f"CRITICAL ERROR in wazuh_uninstall: {e}", file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        return jsonify({"error": f"Server error: {str(e)}", "success": False}), 500

@app.route('/api/wazuh/status', methods=['GET'])
def wazuh_status():
    """Get Wazuh agent status"""
    try:
        import sys
        import traceback
        
        print("=== DEBUG: /api/wazuh/status called ===", file=sys.stderr)
        
        # Import dispatcher
        try:
            from drivers.linux.wazuh_dispatcher import WazuhDispatcher
            print("DEBUG: WazuhDispatcher import successful", file=sys.stderr)
        except ImportError as e:
            print(f"ERROR: Cannot import WazuhDispatcher: {e}", file=sys.stderr)
            return jsonify({"error": f"Import error: {e}", "success": False}), 500
        
        # Create dispatcher
        dispatcher = WazuhDispatcher(logger=lambda msg: print(f"[Dispatcher] {msg}", file=sys.stderr))
        
        # Dispatch action
        result = dispatcher.dispatch("server.wazuh.status", {})
        
        print(f"DEBUG: Result from dispatch: {result}", file=sys.stderr)
        return jsonify(result)
        
    except Exception as e:
        print(f"CRITICAL ERROR in wazuh_status: {e}", file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        return jsonify({"error": f"Server error: {str(e)}", "success": False}), 500
    
@app.route('/api/wazuh/config', methods=['GET', 'PUT'])
def wazuh_config():
    """Get or update Wazuh agent configuration (ossec.conf)"""
    try:
        import sys
        import json
        
        method = request.method
        log_message(f"{method} /api/wazuh/config")
        
        # Debug: Log request
        print(f"[DEBUG] Method: {method}", file=sys.stderr)
        print(f"[DEBUG] Headers: {dict(request.headers)}", file=sys.stderr)
        
        # Handle GET vs PUT differently
        if method == 'GET':
            print("[DEBUG] Handling GET request", file=sys.stderr)
            from drivers.linux.wazuh_dispatcher import WazuhDispatcher
            dispatcher = WazuhDispatcher(
                logger=lambda msg: print(f"[Dispatcher] {msg}", file=sys.stderr)
            )
            result = dispatcher.dispatch("server.wazuh.config.get", {})
            print(f"[DEBUG] GET result: {json.dumps(result)[:200]}...", file=sys.stderr)
            return jsonify(result)
        
        elif method == 'PUT':
            print("[DEBUG] Handling PUT request", file=sys.stderr)
            
            # Check for JSON content
            if not request.is_json:
                print("[ERROR] Request is not JSON", file=sys.stderr)
                return jsonify({
                    "success": False, 
                    "error": "Request must be JSON"
                }), 400
            
            data = request.get_json(silent=True)
            print(f"[DEBUG] Raw data: {data}", file=sys.stderr)
            
            if data is None:
                print("[ERROR] Invalid JSON", file=sys.stderr)
                return jsonify({
                    "success": False, 
                    "error": "Invalid JSON data"
                }), 400
            
            config_content = data.get("config_content")
            if not config_content:
                print("[ERROR] Missing config_content", file=sys.stderr)
                return jsonify({
                    "success": False, 
                    "error": "config_content is required"
                }), 400
            
            print(f"[DEBUG] Config length: {len(config_content)} chars", file=sys.stderr)
            
            # Dispatch update action
            from drivers.linux.wazuh_dispatcher import WazuhDispatcher
            dispatcher = WazuhDispatcher(
                logger=lambda msg: print(f"[Dispatcher] {msg}", file=sys.stderr)
            )
            
            result = dispatcher.dispatch("server.wazuh.config.update", {
                "config_content": config_content
            })
            
            print(f"[DEBUG] PUT result: {json.dumps(result)[:200]}...", file=sys.stderr)
            return jsonify(result)
        
        else:
            return jsonify({
                "success": False,
                "error": f"Method {method} not allowed"
            }), 405
        
    except Exception as e:
        print(f"[CRITICAL] Error in wazuh_config: {e}", file=sys.stderr)
        import traceback
        print(f"[CRITICAL] Traceback: {traceback.format_exc()}", file=sys.stderr)
        return jsonify({
            "success": False, 
            "error": f"Server error: {str(e)}"
        }), 500

# Health check
@app.route('/health', methods=['GET'])
def health(detailed=False):
    """Basic health check untuk server agent"""
    try:            
        # Uptime
        import time
        uptime_seconds = time.time() - psutil.boot_time()
        uptime_str = str(datetime.timedelta(seconds=uptime_seconds))
            
        # 3. Determine overall status
        overall_status = "healthy"
        issues = []
            
        # 4. Basic response (untuk detailed=False)
        if not detailed:
            return {
                "status": "ok",
                "health": overall_status,
                "service": "agent_api",
                "timestamp": datetime.datetime.now().isoformat(),
                "uptime": uptime_str,
                "issues": issues if issues else None
            }
            
    except Exception as e:
        print(f"Health check error: {e}")
        return {
            "status": "error",
            "health": "unknown",
            "timestamp": datetime.datetime.now().isoformat(),
            "error": str(e)
        }

def parse_arguments():
    parser = argparse.ArgumentParser(description='Agent API Server')
    parser.add_argument('--port', type=int, default=8081)
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--debug', action='store_true')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()

    port = int(os.environ.get('AGENT_API_PORT', args.port))
    host = os.environ.get('AGENT_API_HOST', args.host)

    env_debug = os.environ.get('AGENT_DEBUG')
    debug = args.debug if env_debug is None else env_debug.lower() == 'true'

    print(f"Starting Agent API on http://{host}:{port}")
    print(f"Debug mode: {debug}")

    app.run(host=host, port=port, debug=debug)
