"""
Cisco Port Security Management
"""
import re
from .interface import CiscoInterfaceDriver

class CiscoSecurityDriver:
    def __init__(self, config):
        self.config = config
        self.base = None
        self.interface_driver = CiscoInterfaceDriver(config=self.config)
    
    def set_base(self, base):
        """Set base SSH connection"""
        self.base = base
    
    def enable_port_security(self, interface, max_mac=1, violation='restrict', logger=None):
        """Enable port security on interface"""
        try:
            if logger:
                logger(f"Enabling port security on {interface}...")
            
            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {interface}", enable_mode=True)
            self.base.execute_command("switchport mode access", enable_mode=True)
            self.base.execute_command("switchport port-security", enable_mode=True)
            self.base.execute_command("switchport port-security mac-address sticky", enable_mode=True)
            self.base.execute_command(f"switchport port-security maximum {max_mac}", enable_mode=True)
            self.base.execute_command(f"switchport port-security violation {violation}", enable_mode=True)
            self.base.execute_command("switchport port-security aging time 5", enable_mode=True)
            self.base.execute_command("switchport port-security aging type inactivity", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)            
            
            save_result = self.base.save_configuration()
            
            if logger:
                logger(f"Port security enabled on {interface}")
            
            return {
                'status': 'success',
                'message': f'Port security enabled on {interface}',
                'interface': interface,
                'max_mac': max_mac,
                'violation_action': violation
            }
            
        except Exception as e:
            if logger:
                logger(f"Error enabling port security: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def disable_port_security(self, interface, logger=None):
        """Disable port security on interface"""
        try:
            if logger:
                logger(f"Disabling port security on {interface}...")

            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {interface}", enable_mode=True)
            self.base.execute_command("no switchport port-security", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            save_result = self.base.save_configuration()
            
            if logger:
                logger(f"Port security disabled on {interface}")
            
            return {
                'status': 'success',
                'message': f'Port security disabled on {interface}',
                'interface': interface
            }
            
        except Exception as e:
            if logger:
                logger(f"Error disabling port security: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def enable_sticky_mac(self, interface, logger=None):
        """Enable sticky MAC learning on interface"""
        try:
            if logger:
                logger(f"Enabling sticky MAC on {interface}...")

            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {interface} ", enable_mode=True)
            self.base.execute_command("switchport port-security mac-address sticky", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            save_result = self.base.save_configuration()
            
            if logger:
                logger(f"Sticky MAC enabled on {interface}")
            
            return {
                'status': 'success',
                'message': f'Sticky MAC enabled on {interface}',
                'interface': interface
            }
            
        except Exception as e:
            if logger:
                logger(f"Error enabling sticky MAC: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def add_static_mac(self, interface, mac_address, logger=None):
        """Add static MAC address to port security"""
        try:
            if logger:
                logger(f"Adding static MAC {mac_address} to {interface}...")
            
            # Format MAC address
            mac_clean = mac_address.upper().replace(':', '').replace('.', '').replace('-', '')
            if len(mac_clean) == 12:
                mac_formatted = '.'.join([mac_clean[i:i+4] for i in range(0, 12, 4)])
            else:
                mac_formatted = mac_address

            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {interface}", enable_mode=True)
            self.base.execute_command(f"switchport port-security mac-address {mac_formatted}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            save_result = self.base.save_configuration()
            
            if logger:
                logger(f"Static MAC {mac_address} added to {interface}")
            
            return {
                'status': 'success',
                'message': f'Static MAC {mac_address} added to {interface}',
                'interface': interface,
                'mac_address': mac_address
            }
            
        except Exception as e:
            if logger:
                logger(f"Error adding static MAC: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_port_security_status(self, interface=None, logger=None):
        try:
            if interface:
                output = self.base.execute_command("enable", enable_mode=False)
                output = self.base.execute_command(
                    f"show port-security interface {interface}",
                    enable_mode=True
                )
                return {
                    "status": "success",
                    "port_security": self._parse_single_interface(output, interface)
                }

            # Untuk Global
            interfaces = self.interface_driver.get_interfaces()
            results = []

            for iface in interfaces:
                out = self.base.execute_command("enable", enable_mode=False)
                out = self.base.execute_command(
                    f"show port-security interface {iface}",
                    enable_mode=True
                )
                parsed = self._parse_single_interface(out, iface)
                if parsed["enabled"]:
                    results.append(parsed)

            return {
                "status": "success",
                "port_security": {
                    "enabled": bool(results),
                    "interfaces": results
                }
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _parse_single_interface(self, output, interface):
        data = {
            "interface": interface,
            "enabled": False,
            "details": {}
        }

        for line in output.splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                key = k.strip().lower().replace(' ', '_')
                val = v.strip()
                data["details"][key] = val

                if key == "port_security" and val.lower() == "enabled":
                    data["enabled"] = True

        return data
    
    def clear_port_security(self, interface, logger=None):
        """Clear ALL port security configuration on interface"""
        try:
            if logger:
                logger(f"Clearing ALL port security configuration on {interface}...")

            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {interface}", enable_mode=True)
            
            # Dapatkan semua MAC addresses yang terdaftar
            try:
                mac_output = self.base.execute_command(
                    f"show port-security address interface {interface}",
                    enable_mode=True
                )
                
                # Parse MAC addresses dari output
                mac_addresses = self._extract_mac_addresses(mac_output)
                
                if logger:
                    logger(f"Found {len(mac_addresses)} MAC addresses to remove")
                
                # Hapus satu per satu
                for mac in mac_addresses:
                    try:
                        self.base.execute_command(
                            f"no switchport port-security mac-address {mac}",
                            enable_mode=True
                        )
                        if logger:
                            logger(f"Removed MAC address: {mac}")
                    except Exception as mac_error:
                        if logger:
                            logger(f"Warning: Could not remove MAC {mac}: {mac_error}")
            except Exception as e:
                if logger:
                    logger(f"Warning: Could not get MAC addresses: {e}")
            
            # Hapus sticky MAC configuration
            self.base.execute_command("no switchport port-security mac-address sticky", enable_mode=True)
            
            # Reset semua parameter ke default
            self.base.execute_command("no switchport port-security maximum", enable_mode=True)
            self.base.execute_command("no switchport port-security violation", enable_mode=True)
            self.base.execute_command("no switchport port-security aging time", enable_mode=True)
            self.base.execute_command("no switchport port-security aging type", enable_mode=True)
            
            self.base.execute_command("no switchport port-security", enable_mode=True)
            
            # Keluar dari interface dan config mode
            self.base.execute_command("exit", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            # Clear sticky MAC di memory
            self.base.execute_command(f"clear port-security sticky interface {interface}", enable_mode=True)
            # Clear MAC address table untuk interface ini
            self.base.execute_command(f"clear mac address-table interface {interface}", enable_mode=True)
            
            # Reset interface
            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {interface}", enable_mode=True)
            self.base.execute_command("shutdown", enable_mode=True)
            self.base.execute_command("no shutdown", enable_mode=True)
            self.base.execute_command("exit", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)
            
            import time
            time.sleep(2)
            
            # Save configuration
            save_result = self.base.save_configuration()
            
            # Verify
            verify_output = self.base.execute_command(
                f"show port-security interface {interface}",
                enable_mode=True
            )
            
            return {
                'status': 'success',
                'message': f'Port security completely cleared on {interface}',
                'interface': interface,
                'verification': verify_output,
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error clearing port security: {str(e)}")
                import traceback
                logger(f"Traceback: {traceback.format_exc()}")
            
            return {
                'status': 'error',
                'error': str(e)
            }

    def _extract_mac_addresses(self, output):
        """Extract MAC addresses from show port-security address output"""
        mac_addresses = []
        
        # Format AABB.CCDD.EEFF atau AA:BB:CC:DD:EE:FF
        patterns = [
            r'([0-9A-F]{4}\.[0-9A-F]{4}\.[0-9A-F]{4})',  # XXXX.XXXX.XXXX
            r'([0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2})',  # XX:XX:XX:XX:XX:XX
            r'([0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4})'  # XXXX-XXXX-XXXX
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, output.upper())
            mac_addresses.extend(matches)
        
        # Remove duplicates
        return list(set(mac_addresses))