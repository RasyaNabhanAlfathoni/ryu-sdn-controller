import re

class CiscoVlanDriver:
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def get_vlans(self, logger=None):
        """Get all VLANs"""
        try:
            if logger:
                logger("Getting VLANs...")
            
            output = self.base.execute_command("show vlan brief", enable_mode=True)
            
            vlans = []
            lines = output.split('\n')
            
            for line in lines:
                if line.strip() and line[0].isdigit():
                    parts = line.split()
                    if len(parts) >= 2:
                        vlan_info = {
                            'vlan_id': parts[0],
                            'name': parts[1],
                            'status': 'active' if len(parts) > 2 and 'active' in parts[2].lower() else 'inactive',
                            'interfaces': parts[3:] if len(parts) > 3 else []
                        }
                        vlans.append(vlan_info)
            
            if logger:
                logger(f"Found {len(vlans)} VLANs")
            
            return {
                'status': 'success',
                'vlans': vlans
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting VLANs: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def create_vlan(self, vlan_id, name=None, logger=None):
        try:
            if logger:
                logger(f"Creating VLAN {vlan_id}...")

            self.base.execute_command("configure terminal", enable_mode=True)

            self.base.execute_command(f"vlan {vlan_id}", enable_mode=True)

            if name:
                self.base.execute_command(f"name {name}", enable_mode=True)

            self.base.execute_command("end", enable_mode=True)

            # Verifikasi Command
            verify = self.base.execute_command(
                f"show vlan id {vlan_id}",
                enable_mode=True
            )

            if "not found" in verify.lower():
                raise Exception("VLAN not created (verification failed)")

            if logger:
                logger(f"VLAN {vlan_id} successfully verified")

            return {
                'status': 'success',
                'message': f'VLAN {vlan_id} created',
                'vlan_id': vlan_id,
                'name': name or f'VLAN{vlan_id}'
            }

        except Exception as e:
            if logger:
                logger(f"Error creating VLAN: {str(e)}")

            return {
                'status': 'error',
                'error': str(e)
            }

    
    def delete_vlan(self, vlan_id, logger=None):
        try:
            if logger:
                logger(f"Deleting VLAN {vlan_id}...")

            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"no vlan {vlan_id}", enable_mode=True)
            self.base.execute_command("end", enable_mode=True)

            verify = self.base.execute_command(
                f"show vlan id {vlan_id}",
                enable_mode=True
            )

            if "not found" not in verify.lower():
                raise Exception("VLAN still exists after delete")

            self.base.execute_command("write memory", enable_mode=True)

            return {
                "status": "success",
                "message": f"VLAN {vlan_id} deleted"
            }

        except Exception as e:
            if logger:
                logger(f"Error deleting VLAN: {e}")
            return {"status": "error", "error": str(e)}

    def assign_vlan_access(self, interface_name, vlan_id, logger=None):
        try:
            if logger:
                logger(f"Assigning {interface_name} to VLAN {vlan_id}")

            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {interface_name}", enable_mode=True)
            self.base.execute_command("switchport mode access", enable_mode=True)
            self.base.execute_command(f"switchport access vlan {vlan_id}", enable_mode=True)
            self.base.execute_command("exit", enable_mode=True)
            self.base.execute_command("end",enable_mode=True)

            self.base.execute_command("write memory", enable_mode=True)

            return {
                "status": "success",
                "interface": interface_name,
                "vlan_id": vlan_id,
                "mode": "access"
            }

        except Exception as e:
            if logger:
                logger(f"Error assigning VLAN: {e}")
            return {"status": "error", "error": str(e)}
        
    def assign_vlan_trunk(self, interface_name, native_vlan=1, allowed_vlans=None, logger=None):
        try:
            # Convert allowed_vlans
            if allowed_vlans is None:
                allowed_vlans_str = "all"
            elif isinstance(allowed_vlans, list):
                allowed_vlans_str = ",".join(map(str, allowed_vlans))
            else:
                allowed_vlans_str = str(allowed_vlans)
            
            # 1. Reset interface completely
            if logger:
                logger(f"1. Resetting interface {interface_name}")
            
            reset_commands = [
                "configure terminal",
                f"interface {interface_name}",
                "shutdown",
                "no switchport port-security",
                "no switchport",
                "switchport",
                "exit",
                "end"
            ]
            
            for cmd in reset_commands:
                try:
                    self.base.execute_command(cmd, enable_mode=True)
                except Exception as e:
                    if logger:
                        logger(f"Note: {e}")
            
            import time
            time.sleep(2)
            
            # 2. Configure trunk dengan Encapsulation
            if logger:
                logger(f"\n2. Configuring trunk with dot1q encapsulation")
            
            trunk_commands = [
                "configure terminal",
                f"interface {interface_name}",
                "switchport",  # Ensure its a switchport
                "switchport trunk encapsulation dot1q",
                "switchport mode trunk",
                f"switchport trunk native vlan {native_vlan}",
                f"switchport trunk allowed vlan {allowed_vlans_str}",
                "no shutdown",
                "exit",
                "end"
            ]
            
            for cmd in trunk_commands:
                result = self.base.execute_command(cmd, enable_mode=True)
                if result and logger:
                    logger(f"Output: {result}")
            
            time.sleep(2)
            
            # 3. Verification
            if logger:
                logger(f"\n3. Verification")
            
            # Check running config
            running_config = self.base.execute_command(
                f"show run interface {interface_name}",
                enable_mode=True
            )
            
            # Check for critical lines
            required_configs = [
                "switchport trunk encapsulation dot1q",
                "switchport mode trunk",
                f"switchport trunk native vlan {native_vlan}",
                f"switchport trunk allowed vlan {allowed_vlans_str}"
            ]
            
            missing_configs = []
            for required in required_configs:
                if required not in running_config:
                    missing_configs.append(required)
            
            if missing_configs:
                if logger:
                    logger(f"Missing configs: {missing_configs}")
                
                # Try alternative approach if encapsulation fails
                if "switchport trunk encapsulation" not in running_config:
                    if logger:
                        logger(f"\n4. Alternative approach - try without explicit encapsulation")
                    
                    alt_commands = [
                        "configure terminal",
                        f"interface {interface_name}",
                        "switchport mode dynamic desirable", 
                        f"switchport trunk native vlan {native_vlan}",
                        f"switchport trunk allowed vlan {allowed_vlans_str}",
                        "end"
                    ]
                    
                    for cmd in alt_commands:
                        self.base.execute_command(cmd, enable_mode=True)
                    
                    time.sleep(1)
                    
                    # Check again
                    running_config = self.base.execute_command(
                        f"show run interface {interface_name}",
                        enable_mode=True
                    )
                    
                    if logger:
                        logger(f"Alt config:\n{running_config}")
            
            # Final verification with show command
            switchport_output = self.base.execute_command(
                f"show interfaces {interface_name} switchport",
                enable_mode=True
            )
            
            if logger:
                logger(f"\nSwitchport status:\n{switchport_output}")
            
            # Check if trunk is operational
            if "operational mode: trunk" not in switchport_output.lower():
                if logger:
                    logger(f"Warning: May not be operational trunk yet")
            
            # 5. Save configuration
            self.base.execute_command("write memory", enable_mode=True)
            
            if logger:
                logger(f"\nTrunk configuration attempt completed")
            
            return {
                "status": "success",
                "interface": interface_name,
                "mode": "trunk",
                "native_vlan": native_vlan,
                "allowed_vlans": allowed_vlans_str,
                "note": "Configuration applied, check switchport status for operational state"
            }
            
        except Exception as e:
            if logger:
                logger(f"\nError: {e}")
            
            return {
                "status": "error",
                "error": str(e)
            }