# drivers/switch_drivers/cisco/l3.py
import re
from functools import wraps

def json_serializable(func):
    """Decorator to ensure function returns JSON serializable result"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        def clean(obj):
            if isinstance(obj, dict):
                cleaned = {}
                for k, v in obj.items():
                    if callable(v):
                        continue
                    cleaned[k] = clean(v)
                return cleaned
            elif isinstance(obj, (list, tuple)):
                return [clean(item) for item in obj if not callable(item)]
            elif hasattr(obj, '__dict__'):
                return clean(obj.__dict__)
            else:
                return obj
        
        return clean(result)
    
    return wrapper

class CiscoL3Management:
    def __init__(self, config, parent):
        self.config = config
        self.parent = parent
        self.base = None
        
    def set_base(self, base):
        """Set base SSH Connection"""
        self.base = base
    
    def ensure_l3_allowed(self):
        """Check if L3 features are allowed on this device"""
        if hasattr(self.parent, 'get_device_type'):
            device_type = self.parent.get_device_type()
            if device_type == 'L2':
                raise Exception("This device is Layer 2 only. L3 features are not supported.")
    
    # === Utility Methods ===
    def _parse_interface_name(self, interface):
        """Parse and standardize interface name"""
        if interface.startswith('GigabitEthernet'):
            return interface
        elif interface.startswith('Gi'):
            return interface.replace('Gi', 'GigabitEthernet')
        elif interface.startswith('FastEthernet'):
            return interface
        elif interface.startswith('Fa'):
            return interface.replace('Fa', 'FastEthernet')
        elif interface.startswith('TenGigabitEthernet'):
            return interface
        elif interface.startswith('Te'):
            return interface.replace('Te', 'TenGigabitEthernet')
        else:
            return interface
    
    # === IP Routing Detection ===
    def is_ip_routing_enabled(self, logger=None):
        """Check if IP routing is enabled"""
        try:
            output = self.base.execute_command("show run | include ip routing", enable_mode=True)
            
            if "ip routing" in output.lower():
                return True
            
            # Fallback check
            output = self.base.execute_command("show ip route", enable_mode=True)
            if "Routing entry for" in output or "Gateway of last resort" in output:
                return True
            elif "IP routing not enabled" in output or "Invalid input" in output:
                return False
            
            return False
            
        except Exception as e:
            if logger:
                logger(f"Error checking IP routing: {e}")
            return False
    
    def get_routing_status(self, logger=None):
        """Get routing status"""
        try:
            enabled = self.is_ip_routing_enabled(logger)
            return {
                'status': 'success',
                'data': {
                    'ip_routing_enabled': enabled,
                    'message': 'IP routing is enabled' if enabled else 'IP routing is disabled'
                }
            }
        except Exception as e:
            if logger:
                logger(f"Error getting routing status: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_routing_info(self, logger=None):
        """Get comprehensive routing information"""
        try:
            result = {
                'ip_routing_enabled': self.is_ip_routing_enabled(logger),
                'static_routes': [],
                'connected_routes': [],
                'svi_interfaces': []
            }
            
            # Get routing table summary
            if result['ip_routing_enabled']:
                routes_output = self.base.execute_command("show ip route", enable_mode=True)
                result['routing_table_summary'] = routes_output[:1000]
            
            # Get SVI interfaces
            svi_output = self.base.execute_command("show ip interface brief | include Vlan", enable_mode=True)
            for line in svi_output.split('\n'):
                if 'Vlan' in line:
                    parts = line.split()
                    if len(parts) >= 4 and parts[1] != 'unassigned':
                        result['svi_interfaces'].append({
                            'interface': parts[0],
                            'ip_address': parts[1],
                            'status': parts[4] if len(parts) > 4 else 'up',
                            'protocol': parts[5] if len(parts) > 5 else 'up'
                        })
            
            return {
                'status': 'success',
                'data': result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting routing info: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    # === IP Routing Configuration ===
    def enable_ip_routing(self, logger=None):
        """Enable IP routing (layer 3 switching)"""
        try:
            if logger:
                logger("Enabling IP routing...")
            
            # Check if already enabled
            if self.is_ip_routing_enabled(logger):
                if logger:
                    logger("IP routing already enabled")
                return {
                    'status': 'success',
                    'message': 'IP routing already enabled',
                    'already_enabled': True
                }
            
            # Enter config mode and enable IP routing
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command("ip routing", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            try:
                save_result = self.base.save_configuration()
            except Exception as save_error:
                save_result = str(save_error)
            
            if logger:
                logger("IP routing enabled successfully")
            
            return {
                'status': 'success',
                'message': 'IP routing enabled successfully',
                'already_enabled': False,
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error enabling IP routing: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def disable_ip_routing(self, logger=None):
        """Disable IP routing"""
        try:
            if logger:
                logger("Disabling IP routing...")
            
            # Check if already disabled
            if not self.is_ip_routing_enabled(logger):
                if logger:
                    logger("IP routing already disabled")
                return {
                    'status': 'success',
                    'message': 'IP routing already disabled',
                    'already_disabled': True
                }
            
            # Enter config mode and disable IP routing
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command("no ip routing", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            try:
                save_result = self.base.save_configuration()
            except Exception as save_error:
                save_result = str(save_error)
            
            if logger:
                logger("IP routing disabled successfully")
            
            return {
                'status': 'success',
                'message': 'IP routing disabled successfully',
                'already_disabled': False,
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error disabling IP routing: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    # === SVI (Switch Virtual Interface) Management ===
    @json_serializable
    def create_svi(self, vlan_id, ip_address, subnet_mask, description=None, logger=None):
        """Create SVI interface (VLAN interface)"""
        try:
            if logger:
                logger(f"Creating SVI for VLAN {vlan_id}...")
            
            # First check if VLAN exists
            vlan_check = self.base.execute_command(f"show vlan id {vlan_id}", enable_mode=True)
            if "not found" in vlan_check.lower() or "does not exist" in vlan_check.lower():
                if logger:
                    logger(f"VLAN {vlan_id} does not exist")
                return {
                    'status': 'error',
                    'error': f'VLAN {vlan_id} does not exist. Create VLAN first.'
                }
            
            # Enter config mode and configure SVI
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface vlan {vlan_id}", enable_mode=True)
            
            # Add description if provided
            if description:
                self.base.execute_command(f"description {description}", enable_mode=True)
            
            # Configure IP address
            self.base.execute_command(f"ip address {ip_address} {subnet_mask}", enable_mode=True)
            
            # Enable interface
            self.base.execute_command("no shutdown", enable_mode=True)
            
            # Exit interface mode and config mode
            self.base.execute_command("exit", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            try:
                save_result = self.base.save_configuration()
            except Exception as save_error:
                save_result = str(save_error)
            
            if logger:
                logger(f"SVI Vlan{vlan_id} created successfully")
            
            # Build response data
            data = {
                'vlan_id': vlan_id,
                'interface': f'Vlan{vlan_id}',
                'ip_address': ip_address,
                'subnet_mask': subnet_mask
            }
            
            # Only add description if provided
            if description:
                data['description'] = description
            
            return {
                'status': 'success',
                'message': f'SVI Vlan{vlan_id} created successfully',
                'data': data,
                'save_result': save_result
            }
            
        except Exception as e:
            error_msg = str(e)
            if logger:
                logger(f"Error creating SVI: {error_msg}")
            
            # Return JSON yang valid bahkan ketika error
            return {
                'status': 'error',
                'error': error_msg
            }

    @json_serializable
    def delete_svi(self, vlan_id, logger=None):
        """Delete SVI interface"""
        try:
            if logger:
                logger(f"Deleting SVI Vlan{vlan_id}...")
            
            # Check if SVI exists
            svi_check = self.base.execute_command(f"show interface vlan {vlan_id}", enable_mode=True)
            if "Invalid input" in svi_check or "does not exist" in svi_check:
                if logger:
                    logger(f"SVI Vlan{vlan_id} does not exist")
                return {
                    'status': 'error',
                    'error': f'SVI Vlan{vlan_id} does not exist'
                }
            
            # Enter config mode and delete SVI
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface vlan {vlan_id}", enable_mode=True)
            self.base.execute_command("no ip address", enable_mode=True)
            self.base.execute_command("shutdown", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)

            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"no interface vlan {vlan_id}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            try:
                save_result = self.base.save_configuration()
            except Exception as save_error:
                save_result = str(save_error)
            
            if logger:
                logger(f"SVI Vlan{vlan_id} deleted successfully")
            
            return {
                'status': 'success',
                'message': f'SVI Vlan{vlan_id} deleted successfully',
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error deleting SVI: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def configure_svi(self, vlan_id, ip_address=None, subnet_mask=None, description=None, logger=None):
        """Configure existing SVI interface"""
        try:
            if logger:
                logger(f"Configuring SVI Vlan{vlan_id}...")
            
            # Enter config mode
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface vlan {vlan_id}", enable_mode=True)
            
            # Configure description if provided
            if description is not None:
                self.base.execute_command(f"description {description}", enable_mode=True)
            
            # Configure IP address if provided
            if ip_address and subnet_mask:
                self.base.execute_command(f"ip address {ip_address} {subnet_mask}", enable_mode=True)
            
            # Enable interface
            self.base.execute_command("no shutdown", enable_mode=True)
            
            # Exit interface mode and config mode
            self.base.execute_command("exit", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            try:
                save_result = self.base.save_configuration()
            except Exception as save_error:
                save_result = str(save_error)
            
            if logger:
                logger(f"SVI Vlan{vlan_id} configured successfully")
            
            return {
                'status': 'success',
                'message': f'SVI Vlan{vlan_id} configured successfully',
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error configuring SVI: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_svi_interfaces(self, logger=None):
        """Get all SVI interfaces"""
        try:
            output = self.base.execute_command("show ip interface brief", enable_mode=True)
            svis = []
            
            for line in output.split('\n'):
                if 'Vlan' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        interface_info = {
                            'interface': parts[0],
                            'ip_address': parts[1] if parts[1] != 'unassigned' else None,
                            'ok': parts[2] if len(parts) > 2 else '',
                            'method': parts[3] if len(parts) > 3 else '',
                            'status': parts[4] if len(parts) > 4 else 'unknown',
                            'protocol': parts[5] if len(parts) > 5 else 'unknown'
                        }
                        
                        # Get detailed info for each SVI
                        try:
                            detail_output = self.base.execute_command(
                                f"show interface {parts[0]}", enable_mode=True
                            )
                            
                            # Extract description if exists
                            desc_match = re.search(r'Description: (.+)', detail_output)
                            if desc_match:
                                interface_info['description'] = desc_match.group(1).strip()
                            
                            # Extract MTU
                            mtu_match = re.search(r'MTU (\d+)', detail_output)
                            if mtu_match:
                                interface_info['mtu'] = mtu_match.group(1)
                            
                        except:
                            pass
                        
                        svis.append(interface_info)
            
            return {
                'status': 'success',
                'data': svis,
                'count': len(svis)
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting SVI interfaces: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    # === Static Routing ===
    @json_serializable
    def add_static_route(self, network, mask, next_hop, description=None, logger=None):
        """Add static route"""
        try:
            if logger:
                logger(f"Adding static route {network}/{mask} via {next_hop}...")
            
            # Enter config mode and add route
            self.base.execute_command("configure terminal", enable_mode=True)
            
            if description is not None and description != '':
                self.base.execute_command(f"ip route {network} {mask} {next_hop} name {description}", enable_mode=True)
            else:
                self.base.execute_command(f"ip route {network} {mask} {next_hop}", enable_mode=True)
            
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            try:
                save_result = self.base.save_configuration()
            except Exception as save_error:
                save_result = str(save_error)
            
            if logger:
                logger(f"Static route {network}/{mask} added successfully")
            
            return {
                'status': 'success',
                'message': f'Static route {network}/{mask} added',
                'data': {
                    'network': network,
                    'mask': mask,
                    'next_hop': next_hop,
                    'description': description
                },
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error adding static route: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
        
    @json_serializable
    def remove_static_route(self, network, mask, next_hop, logger=None):
        """Remove static route"""
        try:
            if logger:
                logger(f"Removing static route {network}/{mask} via {next_hop}...")
            
            # Enter config mode and remove route
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"no ip route {network} {mask} {next_hop}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            try:
                save_result = self.base.save_configuration()
            except Exception as save_error:
                save_result = str(save_error)
            
            if logger:
                logger(f"Static route {network}/{mask} removed successfully")
            
            return {
                'status': 'success',
                'message': f'Static route {network}/{mask} removed',
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error removing static route: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_static_routes(self, logger=None):
        """Get all static routes"""
        try:
            output = self.base.execute_command("show ip route static", enable_mode=True)
            
            routes = []
            
            for line in output.split('\n'):
                line = line.strip()
                
                # Look for route entries
                if line.startswith('S') and line[1] == ' ':
                    parts = line.split()
                    if len(parts) >= 5:
                        routes.append({
                            'type': 'static',
                            'network': parts[1],
                            'via': parts[4],
                            'interface': parts[5] if len(parts) > 5 else '',
                            'distance': parts[2].strip('[]') if '[' in parts[2] else '1'
                        })
                
                # Look for directly connected routes
                elif line.startswith('C') and line[1] == ' ':
                    parts = line.split()
                    if len(parts) >= 4:
                        routes.append({
                            'type': 'connected',
                            'network': parts[1],
                            'interface': parts[3]
                        })
            
            return {
                'status': 'success',
                'data': routes,
                'count': len(routes)
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting static routes: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    # === Interface L3 Configuration ===
    @json_serializable
    def configure_interface_ip(self, interface, ip_address, subnet_mask, description=None, logger=None):
        """Configure IP address on routed interface"""
        try:
            if logger:
                logger(f"Configuring IP {ip_address}/{subnet_mask} on {interface}...")
            
            intf_name = self._parse_interface_name(interface)
            
            # Enter config mode and configure interface
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {intf_name}", enable_mode=True)
            
            # Configure description if provided
            if description:
                self.base.execute_command(f"description {description}", enable_mode=True)
            
            # Convert to routed port
            self.base.execute_command("no switchport", enable_mode=True)
            
            # Configure IP address
            self.base.execute_command(f"ip address {ip_address} {subnet_mask}", enable_mode=True)
            
            # Enable interface
            self.base.execute_command("no shutdown", enable_mode=True)
            
            # Exit interface mode and config mode
            self.base.execute_command("exit", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            try:
                save_result = self.base.save_configuration()
            except Exception as save_error:
                save_result = str(save_error)
            
            if logger:
                logger(f"Interface {intf_name} configured as routed port")
            
            return {
                'status': 'success',
                'message': f'Interface {intf_name} configured as routed port',
                'data': {
                    'interface': intf_name,
                    'ip_address': ip_address,
                    'subnet_mask': subnet_mask,
                    'description': description,
                    'mode': 'routed'
                },
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error configuring interface IP: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def convert_to_routed_port(self, interface, logger=None):
        """Convert switch port to routed port"""
        try:
            intf_name = self._parse_interface_name(interface)
            
            if logger:
                logger(f"Converting {intf_name} to routed port...")
            
            # Check current mode
            current_output = self.base.execute_command(f"show interface {intf_name} switchport", enable_mode=True)
            if "Switchport: Enabled" not in current_output:
                if logger:
                    logger(f"Interface {intf_name} is already a routed port")
                return {
                    'status': 'success',
                    'message': f'Interface {intf_name} is already a routed port',
                    'already_routed': True
                }
            
            # Enter config mode and convert to routed port
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {intf_name}", enable_mode=True)
            self.base.execute_command("no switchport", enable_mode=True)
            self.base.execute_command("no shutdown", enable_mode=True)
            self.base.execute_command("exit", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            self.base.execute_command("write mem", enable_mode=True)

            # Save configuration
            # try:
            #     save_result = self.base.save_configuration()
            # except Exception as save_error:
            #     save_result = str(save_error)
            
            if logger:
                logger(f"Interface {intf_name} converted to routed port")
            
            return {
                'status': 'success',
                'message': f'Interface {intf_name} converted to routed port',
                'already_routed': False,
                # 'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error converting to routed port: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def convert_to_switched_port(self, interface, logger=None):
        """Convert routed port back to switch port"""
        try:
            intf_name = self._parse_interface_name(interface)
            
            if logger:
                logger(f"Converting {intf_name} to switch port...")
            
            # Check current mode
            current_output = self.base.execute_command(f"show interface {intf_name} switchport", enable_mode=True)
            if "Switchport: Disabled" not in current_output:
                if logger:
                    logger(f"Interface {intf_name} is already a switch port")
                return {
                    'status': 'success',
                    'message': f'Interface {intf_name} is already a switch port',
                    'already_switched': True
                }
            
            # Enter config mode and convert to switch port
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {intf_name}", enable_mode=True)
            self.base.execute_command("switchport", enable_mode=True)
            self.base.execute_command("no shutdown", enable_mode=True)
            self.base.execute_command("exit", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            try:
                save_result = self.base.save_configuration()
            except Exception as save_error:
                save_result = str(save_error)
            
            if logger:
                logger(f"Interface {intf_name} converted to switch port")
            
            return {
                'status': 'success',
                'message': f'Interface {intf_name} converted to switch port',
                'already_switched': False,
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error converting to switched port: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
        
    # === ACL Management ===
    @json_serializable
    def create_standard_acl(self, acl_number, logger=None):
        """Create standard numbered ACL (1-99)"""
        try:
            if logger:
                logger(f"Creating standard ACL {acl_number}...")
            
            # Validate ACL number for standard range
            try:
                acl_num = int(acl_number)
                if not (1 <= acl_num <= 99):
                    return {
                        'status': 'error',
                        'error': 'Standard ACL numbers must be in range 1-99'
                    }
            except ValueError:
                return {
                    'status': 'error',
                    'error': 'ACL number must be numeric'
                }
            
            # Check if ACL already exists
            acl_check = self.base.execute_command(f"show access-list {acl_number}", enable_mode=True)
            if "access-list" in acl_check.lower():
                if logger:
                    logger(f"ACL {acl_number} already exists")
                return {
                    'status': 'success',
                    'message': f'ACL {acl_number} already exists',
                    'already_exists': True
                }
            
            # Create ACL with deny any as default first rule
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"access-list {acl_number} deny any", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            if logger:
                logger(f"Standard ACL {acl_number} created successfully")

            self.base.save_configuration()
            
            return {
                'status': 'success',
                'message': f'Standard ACL {acl_number} created',
                'data': {
                    'acl_number': acl_number,
                    'type': 'standard',
                    'default_rule': 'deny any'
                }
            }
            
        except Exception as e:
            if logger:
                logger(f"Error creating standard ACL: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    @json_serializable
    def add_standard_acl_rule(self, acl_number, action, source, logger=None):
        """Add rule to standard ACL"""
        try:
            if logger:
                logger(f"Adding rule to ACL {acl_number}: {action} {source}")
            
            # Validate action
            action = action.lower()
            if action not in ['permit', 'deny']:
                return {
                    'status': 'error',
                    'error': 'Action must be "permit" or "deny"'
                }
            
            # Validate source format
            if not self._validate_ip_network(source):
                return {
                    'status': 'error',
                    'error': f'Invalid source format: {source}. Use IP address or network with wildcard'
                }
            
            # Check if ACL exists
            acl_check = self.base.execute_command(f"show access-list {acl_number}", enable_mode=True)
            acl_check_lower = acl_check.lower()
            acl_exists = (
                "access-list" in acl_check_lower or 
                f"access list {acl_number}" in acl_check_lower or
                f"standard ip access list {acl_number}" in acl_check_lower or
                f"Standard IP access list {acl_number}" in acl_check_lower
            )
            
            # Also check if the command returned an error
            has_error = (
                "invalid" in acl_check_lower or 
                "not found" in acl_check_lower or
                "error" in acl_check_lower or
                acl_check.strip() == ""
            )
            
            if has_error or not acl_exists:
                return {
                    'status': 'error',
                    'error': f'ACL {acl_number} does not exist. Create it first.',
                }
            
            # Add rule
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"access-list {acl_number} {action} {source}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            if logger:
                logger(f"Rule added to ACL {acl_number}")

            self.base.save_configuration()
            
            return {
                'status': 'success',
                'message': f'Rule {action} {source} added to ACL {acl_number}',
                'data': {
                    'acl_number': acl_number,
                    'action': action,
                    'source': source
                }
            }
            
        except Exception as e:
            if logger:
                logger(f"Error adding ACL rule: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    @json_serializable
    def create_extended_acl(self, acl_number, logger=None):
        """Create extended numbered ACL (100-199)"""
        try:
            if logger:
                logger(f"Creating extended ACL {acl_number}...")
            
            # Validate ACL number for extended range
            try:
                acl_num = int(acl_number)
                if not (100 <= acl_num <= 199):
                    return {
                        'status': 'error',
                        'error': 'Extended ACL numbers must be in range 100-199'
                    }
            except ValueError:
                return {
                    'status': 'error',
                    'error': 'ACL number must be numeric'
                }
            
            # Check if ACL already exists
            acl_check = self.base.execute_command(f"show access-list {acl_number}", enable_mode=True)
            if "access-list" in acl_check.lower():
                if logger:
                    logger(f"ACL {acl_number} already exists")
                return {
                    'status': 'success',
                    'message': f'ACL {acl_number} already exists',
                    'already_exists': True
                }
            
            # Create ACL with deny any any as default first rule
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"access-list {acl_number} deny ip any any", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            if logger:
                logger(f"Extended ACL {acl_number} created successfully")

            self.base.save_configuration()
            
            return {
                'status': 'success',
                'message': f'Extended ACL {acl_number} created',
                'data': {
                    'acl_number': acl_number,
                    'type': 'extended',
                    'default_rule': 'deny ip any any'
                }
            }
            
        except Exception as e:
            if logger:
                logger(f"Error creating extended ACL: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    @json_serializable
    def add_extended_acl_rule(self, acl_number, action, protocol, source, destination, options=None, logger=None):
        """Add rule to extended ACL"""
        try:
            if logger:
                logger(f"Adding extended rule to ACL {acl_number}")
            
            # Validate action
            action = action.lower()
            if action not in ['permit', 'deny']:
                return {
                    'status': 'error',
                    'error': 'Action must be "permit" or "deny"'
                }
            
            # Validate protocol
            protocol = protocol.lower()
            valid_protocols = ['ip', 'tcp', 'udp', 'icmp', 'gre', 'esp', 'ah']
            if protocol not in valid_protocols:
                return {
                    'status': 'error',
                    'error': f'Protocol must be one of: {", ".join(valid_protocols)}'
                }
            
            # Build rule command
            rule_parts = [f"access-list {acl_number} {action} {protocol} {source} {destination}"]
            
            # Add options for TCP/UDP
            if options:
                if protocol in ['tcp', 'udp']:
                    if 'operator' in options:
                        rule_parts.append(options['operator'])
                        if 'port' in options:
                            rule_parts.append(str(options['port']))
                elif protocol == 'icmp':
                    if 'icmp_type' in options:
                        rule_parts.append(options['icmp_type'])
            
            rule_cmd = " ".join(rule_parts)
            
            # Check if ACL exists
            acl_check = self.base.execute_command(f"show access-list {acl_number}", enable_mode=True)
            acl_check_lower = acl_check.lower()
            acl_exists = (
                "access-list" in acl_check_lower or 
                f"access list {acl_number}" in acl_check_lower or
                f"extended ip access list {acl_number}" in acl_check_lower or
                f"Extended IP access list {acl_number}" in acl_check_lower
            )
            
            # Also check if the command returned an error
            has_error = (
                "invalid" in acl_check_lower or 
                "not found" in acl_check_lower or
                "error" in acl_check_lower or
                acl_check.strip() == ""
            )
            
            if has_error or not acl_exists:
                return {
                    'status': 'error',
                    'error': f'ACL {acl_number} does not exist. Create it first.',
                }
            
            # Add rule
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(rule_cmd, enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            if logger:
                logger(f"Extended rule added to ACL {acl_number}")

            self.base.save_configuration()
            
            return {
                'status': 'success',
                'message': f'Extended rule added to ACL {acl_number}',
                'data': {
                    'acl_number': acl_number,
                    'action': action,
                    'protocol': protocol,
                    'source': source,
                    'destination': destination,
                    'options': options,
                    'command': rule_cmd
                }
            }
            
        except Exception as e:
            if logger:
                logger(f"Error adding extended ACL rule: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    @json_serializable
    def apply_acl_to_interface(self, interface, acl_number, direction, logger=None):
        """Apply ACL to interface"""
        try:
            if logger:
                logger(f"Applying ACL {acl_number} to {interface} {direction}...")
            
            # Validate direction
            direction = direction.lower()
            if direction not in ['in', 'out']:
                return {
                    'status': 'error',
                    'error': 'Direction must be "in" or "out"'
                }
            
            intf_name = self._parse_interface_name(interface)
            
            # Check if ACL exists
            # Check if ACL exists
            acl_check = self.base.execute_command(f"show access-list {acl_number}", enable_mode=True)
            acl_check_lower = acl_check.lower()
            acl_exists = (
                "access-list" in acl_check_lower or 
                f"access list {acl_number}" in acl_check_lower or
                f"standard ip access list {acl_number}" in acl_check_lower or
                f"Standard IP access list {acl_number}" in acl_check_lower or
                f"extended ip access list {acl_number}" in acl_check_lower or
                f"Extended IP access list {acl_number}" in acl_check_lower
            )
            
            # Also check if the command returned an error
            has_error = (
                "invalid" in acl_check_lower or 
                "not found" in acl_check_lower or
                "error" in acl_check_lower or
                acl_check.strip() == ""
            )
            
            if has_error or not acl_exists:
                return {
                    'status': 'error',
                    'error': f'ACL {acl_number} does not exist. Create it first.',
                }
            
            # Apply ACL to interface
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {intf_name}", enable_mode=True)
            
            if direction == 'in':
                self.base.execute_command(f"ip access-group {acl_number} in", enable_mode=True)
            else:
                self.base.execute_command(f"ip access-group {acl_number} out", enable_mode=True)
            
            self.base.execute_command("end", enable_mode=True)
            
            if logger:
                logger(f"ACL {acl_number} applied to {intf_name} {direction}")

            self.base.save_configuration()
            
            return {
                'status': 'success',
                'message': f'ACL {acl_number} applied to {intf_name} {direction}',
                'data': {
                    'interface': intf_name,
                    'acl_number': acl_number,
                    'direction': direction
                }
            }
            
        except Exception as e:
            if logger:
                logger(f"Error applying ACL to interface: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    # === ACL Removal Methods ===
    @json_serializable
    def remove_acl_rule(self, acl_number, sequence=None, logger=None):
        """Remove specific rule from ACL or entire ACL"""
        try:
            if logger:
                logger(f"Removing from ACL {acl_number}...")
            
            if sequence:
                # Remove specific rule by sequence number
                self.base.execute_command("configure terminal", enable_mode=True)
                self.base.execute_command(f"no access-list {acl_number} {sequence}", enable_mode=True)
                self.base.execute_command("end", enable_mode=True)
                
                if logger:
                    logger(f"Rule {sequence} removed from ACL {acl_number}")

                self.base.save_configuration()
                
                return {
                    'status': 'success',
                    'message': f'Rule {sequence} removed from ACL {acl_number}'
                }
            else:
                # Remove entire ACL
                # First, remove from any interfaces
                interfaces_output = self.base.execute_command("show ip interface", enable_mode=True)
                for line in interfaces_output.split('\n'):
                    if acl_number in line and 'access list' in line.lower():
                        parts = line.split()
                        intf_name = parts[0]
                        direction = 'in' if 'inbound' in line.lower() else 'out'
                        
                        self.base.execute_command("configure terminal", enable_mode=True)
                        self.base.execute_command(f"interface {intf_name}", enable_mode=True)
                        self.base.execute_command(f"no ip access-group {acl_number} {direction}", enable_mode=True)
                        self.base.execute_command("end", enable_mode=True)
                
                # Then remove ACL
                self.base.execute_command("configure terminal", enable_mode=True)
                self.base.execute_command(f"no access-list {acl_number}", enable_mode=True)
                self.base.execute_command("end", enable_mode=True)
                
                if logger:
                    logger(f"ACL {acl_number} removed")

                self.base.save_configuration()
                
                return {
                    'status': 'success',
                    'message': f'ACL {acl_number} removed'
                }
            
        except Exception as e:
            if logger:
                logger(f"Error removing ACL/rule: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    @json_serializable
    def get_acls(self, logger=None):
        """Get all ACLs and their rules"""
        try:
            if logger:
                logger("Getting ACL information...")
            
            output = self.base.execute_command("show ip access-lists", enable_mode=True)
            
            acls = []
            current_acl = None
            
            for line in output.split('\n'):
                line = line.strip()
                
                # Look for ACL definition
                if line.startswith('Standard IP access list') or line.startswith('Extended IP access list'):
                    if current_acl:
                        acls.append(current_acl)
                    
                    # Parse ACL header
                    parts = line.split()
                    if len(parts) >= 5:
                        acl_num = parts[-1]
                        acl_type = 'standard' if 'Standard' in line else 'extended'
                        
                        current_acl = {
                            'number': acl_num,
                            'type': acl_type,
                            'name': acl_num,
                            'rules': [],
                            'hit_counts': {}
                        }
                
                # Look for ACL rules
                elif line and current_acl:
                    # Extract rule details
                    rule_match_matches = re.match(r'(\d+)\s+(permit|deny)\s+(.+?)\s+\((\d+)\s+matches\)', line)
                    if rule_match_matches:
                        rule_num, action, criteria, hits = rule_match_matches.groups()
                        current_acl['rules'].append({
                            'sequence': int(rule_num),
                            'action': action,
                            'criteria': criteria.strip(),
                            'hit_count': int(hits)
                        })
                        continue
                    
                    # Coba pattern tanpa matches (untuk kasus Anda)
                    rule_match_simple = re.match(r'(\d+)\s+(permit|deny)\s+(.+)$', line)
                    if rule_match_simple:
                        rule_num, action, criteria = rule_match_simple.groups()
                        current_acl['rules'].append({
                            'sequence': int(rule_num),
                            'action': action,
                            'criteria': criteria.strip(),
                            'hit_count': 0  # Default jika tidak ada hit count
                        })
                        continue
                    
                    # Coba pattern dengan koma (untuk format: "192.168.10.0, wildcard bits 0.0.0.255")
                    rule_match_comma = re.match(r'(\d+)\s+(permit|deny)\s+([\d\.,]+)(?:\s+wildcard\s+bits\s+([\d\.]+))?', line)
                    if rule_match_comma:
                        rule_num, action, network, wildcard = rule_match_comma.groups()
                        if wildcard:
                            criteria = f"{network} {wildcard}"
                        else:
                            criteria = network
                        
                        current_acl['rules'].append({
                            'sequence': int(rule_num),
                            'action': action,
                            'criteria': criteria.strip(),
                            'hit_count': 0
                        })
                        continue
            
            # Add the last ACL
            if current_acl:
                acls.append(current_acl)
            
            # Get ACL interfaces
            try:
                interface_output = self.base.execute_command("show ip interface", enable_mode=True)
                for line in interface_output.split('\n'):
                    if 'access list' in line.lower():
                        parts = line.split()
                        if len(parts) >= 5:
                            intf_name = parts[0]
                            acl_info = line.lower()
                            
                            # Extract ACL number from line
                            for acl in acls:
                                if str(acl['number']) in line:
                                    if 'inbound' in acl_info:
                                        acl['applied_in'] = intf_name
                                    elif 'outbound' in acl_info:
                                        acl['applied_out'] = intf_name
            except Exception as e:
                if logger:
                    logger(f"DEBUG: Error getting interface ACL assignments: {e}")
            
            return {
                'status': 'success',
                'data': acls,
                'count': len(acls)
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting ACLs: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    @json_serializable
    def configure_ntp_server(self, ntp_server, logger=None):
        """Configure NTP server"""
        try:
            if logger:
                logger(f"Configuring NTP server {ntp_server}...")
            
            # Validate IP address or hostname
            if not (self._validate_ip_address(ntp_server) or self._validate_hostname(ntp_server)):
                return {
                    'status': 'error',
                    'error': f'Invalid NTP server: {ntp_server}'
                }
            
            # Configure NTP
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"ntp server {ntp_server}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            if logger:
                logger(f"NTP server {ntp_server} configured")

            self.base.save_configuration()
            
            # Verify NTP status
            ntp_status = self.base.execute_command("show ntp status", enable_mode=True)
            ntp_associations = self.base.execute_command("show ntp associations", enable_mode=True)
            
            return {
                'status': 'success',
                'message': f'NTP server {ntp_server} configured',
                'data': {
                    'ntp_server': ntp_server,
                    'status': 'configured',
                    'ntp_status': ntp_status[:500],  # Limit output
                    'associations': ntp_associations[:500]
                }
            }
            
        except Exception as e:
            if logger:
                logger(f"Error configuring NTP: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    # === Helper Methods for ACL, DNS, NTP ===
    def _validate_ip_address(self, ip_address):
        """Validate IP address format"""
        import ipaddress
        try:
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False

    def _validate_ip_network(self, network):
        """Validate IP network with optional wildcard"""
        # Simple validation - can be enhanced
        parts = network.split()
        if len(parts) == 1:
            # Could be IP, host, or any
            return network in ['any', 'host', 'any'] or self._validate_ip_address(parts[0])
        elif len(parts) == 2:
            # Could be host IP or network wildcard
            if parts[0] == 'host':
                return self._validate_ip_address(parts[1])
            else:
                # Assume network wildcard format
                return (self._validate_ip_address(parts[0]) and 
                       (parts[1] == '0.0.0.0' or self._validate_ip_address(parts[1])))
        return False

    def _validate_hostname(self, hostname):
        """Validate hostname format"""
        import re
        if len(hostname) > 255:
            return False
        if hostname[-1] == ".":
            hostname = hostname[:-1]
        allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        return all(allowed.match(x) for x in hostname.split("."))

    def get_ntp_status(self, logger=None):
        """Get NTP configuration status"""
        try:
            # Get configured servers
            config_output = self.base.execute_command("show running-config | include ntp server", enable_mode=True)
            ntp_servers = []
            
            for line in config_output.split('\n'):
                if 'ntp server' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        ntp_servers.append(parts[2])
            
            # Get NTP status
            status_output = self.base.execute_command("show ntp status", enable_mode=True)
            associations_output = self.base.execute_command("show ntp associations", enable_mode=True)
            
            return {
                'status': 'success',
                'data': {
                    'ntp_servers': ntp_servers,
                    'status': status_output[:500],
                    'associations': associations_output[:500],
                    'count': len(ntp_servers)
                }
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting NTP status: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    # === L3 Feature Test ===
    def test_l3_capability(self, logger=None):
        """Test if switch supports L3 features"""
        try:
            if logger:
                logger("Testing L3 capability...")
            
            tests = {
                'ip_routing': False,
                'svi_support': False,
                'static_routing': False,
                'acl_support': False
            }
            
            # Test IP routing
            tests['ip_routing'] = self.is_ip_routing_enabled(logger)
            
            # Test SVI support
            try:
                output = self.base.execute_command("show interface vlan 1", enable_mode=True)
                if "Invalid input" not in output:
                    tests['svi_support'] = True
            except:
                tests['svi_support'] = False
            
            # Test static routing
            try:
                output = self.base.execute_command("show ip route static", enable_mode=True)
                if "Invalid input" not in output:
                    tests['static_routing'] = True
            except:
                tests['static_routing'] = False
            
            # Test ACL support
            try:
                output = self.base.execute_command("show access-lists", enable_mode=True)
                if "Invalid input" not in output:
                    tests['acl_support'] = True
            except:
                tests['acl_support'] = False
            
            # Determine overall capability
            l3_capable = any(tests.values())
            
            if logger:
                logger(f"L3 capability test results: {tests}")
            
            return {
                'status': 'success',
                'data': tests,
                'l3_capable': l3_capable,
                'message': 'L3 capable' if l3_capable else 'L2 switch only'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error testing L3 capability: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }