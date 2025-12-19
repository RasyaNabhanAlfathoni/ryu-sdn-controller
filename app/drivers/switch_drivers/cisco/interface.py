import re

class CiscoInterfaceDriver:
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def get_interfaces(self, logger=None):
        """Get all interfaces"""
        try:
            if logger:
                logger("Getting interfaces...")
            
            output = self.base.execute_command("show interfaces", enable_mode=True)
            
            interfaces = []
            current_interface = None
            current_data = {}
            
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                
                # Deteksi interface baru
                if line.startswith('GigabitEthernet') or line.startswith('FastEthernet') or line.startswith('TenGigabitEthernet'):
                    if current_interface and current_data:
                        interfaces.append(current_data)
                    
                    # Start new interface
                    current_interface = line.split()[0]
                    current_data = {
                        'interface': current_interface,
                        'status': 'down',
                        'description': '',
                        'mac_address': '',
                        'mtu': '',
                        'bandwidth': '',
                        'ip_address': ''
                    }
                
                # Parse status
                elif 'line protocol is' in line.lower():
                    if 'up' in line.lower():
                        current_data['status'] = 'up'
                    else:
                        current_data['status'] = 'down'
                
                # Parse description
                elif 'Description:' in line:
                    desc = line.split('Description:')[-1].strip()
                    current_data['description'] = desc
                
                # Parse MAC address
                elif 'Hardware is' in line and 'address is' in line:
                    mac_match = re.search(r'address is (\S+)', line)
                    if mac_match:
                        current_data['mac_address'] = mac_match.group(1)
                
                # Parse MTU
                elif 'MTU' in line:
                    mtu_match = re.search(r'MTU (\d+)', line)
                    if mtu_match:
                        current_data['mtu'] = mtu_match.group(1)
                
                # Parse bandwidth
                elif 'BW' in line and 'Kbit' in line:
                    bw_match = re.search(r'BW (\d+)', line)
                    if bw_match:
                        current_data['bandwidth'] = bw_match.group(1)
            
            # Add last interface
            if current_interface and current_data:
                interfaces.append(current_data)
            
            # Get IP addresses
            ip_output = self.base.execute_command("show ip interface brief", enable_mode=True)
            ip_lines = ip_output.split('\n')
            
            for line in ip_lines:
                parts = line.split()
                if len(parts) >= 4:
                    intf_name = parts[0]
                    ip_addr = parts[1]
                    
                    # Update interface dengan IP
                    for intf in interfaces:
                        if intf['interface'] == intf_name and ip_addr != 'unassigned':
                            intf['ip_address'] = ip_addr
            
            if logger:
                logger(f"Found {len(interfaces)} interfaces")
            
            return {
                'status': 'success',
                'interfaces': interfaces
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting interfaces: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def configure_interface(self, interface_name, params, logger=None):
        """Configure interface"""
        try:
            if logger:
                logger(f"Configuring interface {interface_name}...")
            
            config_commands = []
            
            # Enter interface config mode
            config_commands.append(f"interface {interface_name}")
            
            # Configure description
            if 'description' in params:
                desc = params['description']
                config_commands.append(f"description {desc}")
            
            # Configure IP address
            if 'ip_address' in params and 'subnet_mask' in params:
                ip_addr = params['ip_address']
                subnet = params['subnet_mask']
                config_commands.append(f"ip address {ip_addr} {subnet}")
            
            # Configure speed/duplex
            if 'speed' in params:
                speed = params['speed']
                if speed in ['10', '100', '1000', 'auto']:
                    config_commands.append(f"speed {speed}")
            
            if 'duplex' in params:
                duplex = params['duplex']
                if duplex in ['full', 'half', 'auto']:
                    config_commands.append(f"duplex {duplex}")
            
            # Configure shutdown/no shutdown
            if 'admin_status' in params:
                if params['admin_status'] == 'up':
                    config_commands.append("no shutdown")
                else:
                    config_commands.append("shutdown")
            
            # Exit interface config
            config_commands.append("exit")
            
            # Execute configuration
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"Interface {interface_name} configured successfully")
            
            return {
                'status': 'success',
                'message': f'Interface {interface_name} configured',
                'commands': config_commands
            }
            
        except Exception as e:
            if logger:
                logger(f"Error configuring interface: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def enable_interface(self, interface_name, logger=None):
        """Enable interface (no shutdown)"""
        try:
            if logger:
                logger(f"Enabling interface {interface_name}...")
            
            config_commands = [
                f"interface {interface_name}",
                "no shutdown",
                "exit"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"Interface {interface_name} enabled")
            
            return {
                'status': 'success',
                'message': f'Interface {interface_name} enabled'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error enabling interface: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def disable_interface(self, interface_name, logger=None):
        """Disable interface (shutdown)"""
        try:
            if logger:
                logger(f"Disabling interface {interface_name}...")
            
            config_commands = [
                f"interface {interface_name}",
                "shutdown",
                "exit"
            ]
            
            result = self.base.configure_terminal(config_commands)
            
            if logger:
                logger(f"Interface {interface_name} disabled")
            
            return {
                'status': 'success',
                'message': f'Interface {interface_name} disabled'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error disabling interface: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }