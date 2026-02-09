import re

class CiscoInterfaceDriver:
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def get_interfaces(self, logger=None):
        """Get all interfaces dengan parsing yang lebih komprehensif"""
        try:
            if logger:
                logger("Getting interfaces...")
            
            # Dapatkan output dari switch
            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("terminal length 0", enable_mode=True)
            output = self.base.execute_command("show interfaces", enable_mode=True)
            
            if logger:
                logger(f"Output length: {len(output)} chars")
                logger("Sample output (first 500 chars):")
                logger(output[:500])
            
            interfaces = []
            current_interface = None
            current_data = {}
            
            lines = output.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                if logger and i < 10:  # Log 10 baris pertama untuk debugging
                    logger(f"Line {i}: '{line}'")
                
                # Gunakan regex yang lebih komprehensif untuk semua tipe interface Cisco
                interface_match = re.match(r'^(Ethernet\d+/\d+|GigabitEthernet\d+/\d+|FastEthernet\d+/\d+|TenGigabitEthernet\d+/\d+|Vlan\d+|Port-channel\d+)\s+', line)
                
                if interface_match:
                    if current_interface and current_data:
                        interfaces.append(current_data)
                        if logger:
                            logger(f"Added interface: {current_interface}")
                    
                    # Start new interface
                    current_interface = interface_match.group(1)
                    current_data = {
                        'interface': current_interface,
                        'status': 'down',  # default
                        'description': '',
                        'mac_address': '',
                        'mtu': '',
                        'bandwidth': '',
                        'ip_address': ''
                    }
                    
                    if logger:
                        logger(f"Found new interface: {current_interface}")
                    
                    # Parse status dari baris pertama interface
                    if 'is up' in line and 'line protocol is up' in line:
                        current_data['status'] = 'up'
                    elif 'administratively down' in line:
                        current_data['status'] = 'down'
                    elif 'is up' in line or 'line protocol is up' in line:
                        current_data['status'] = 'up (partial)'
                
                # Hanya parse jika sedang memproses suatu interface
                elif current_interface and current_data:
                    # Parse status (baris terpisah kadang ada status tambahan)
                    if 'line protocol is' in line.lower():
                        if 'up' in line.lower():
                            current_data['status'] = 'up'
                        else:
                            current_data['status'] = 'down'
                    
                    # Parse description (bisa multi-line)
                    elif 'Description:' in line:
                        desc = line.split('Description:', 1)[-1].strip()
                        if desc:
                            current_data['description'] = desc
                    
                    # Parse MAC address (format: "address is aabb.cc00.0100")
                    elif 'address is' in line.lower() and not current_data['mac_address']:
                        mac_match = re.search(r'address is (\S+)', line)
                        if mac_match:
                            current_data['mac_address'] = mac_match.group(1)
                            if logger:
                                logger(f"  Found MAC for {current_interface}: {current_data['mac_address']}")
                    
                    # Parse MTU
                    elif 'MTU' in line and not current_data['mtu']:
                        mtu_match = re.search(r'MTU (\d+)', line)
                        if mtu_match:
                            current_data['mtu'] = mtu_match.group(1)
                    
                    # Parse bandwidth (BW dalam Kbit/sec)
                    elif 'BW' in line and not current_data['bandwidth']:
                        bw_match = re.search(r'BW (\d+)', line)
                        if bw_match:
                            current_data['bandwidth'] = bw_match.group(1)
            
            # Add last interface
            if current_interface and current_data:
                interfaces.append(current_data)
                if logger:
                    logger(f"Added last interface: {current_interface}")
            
            # Get IP addresses dari "show ip interface brief"
            if logger:
                logger("Getting IP addresses...")
            
            try:
                ip_output = self.base.execute_command("show ip interface brief", enable_mode=True)
                
                if logger:
                    logger("IP output sample:")
                    logger(ip_output[:300])
                
                ip_lines = ip_output.split('\n')
                
                for line in ip_lines:
                    line = line.strip()
                    parts = line.split()
                    
                    if len(parts) >= 2:
                        intf_name = parts[0]
                        ip_addr = parts[1]
                        
                        # Skip header dan unassigned IPs
                        if intf_name in ['Interface', '']:
                            continue
                        
                        if ip_addr.lower() not in ['unassigned', '--', '']:
                            # Update interface dengan IP
                            for intf in interfaces:
                                if intf['interface'] == intf_name:
                                    intf['ip_address'] = ip_addr
                                    if logger:
                                        logger(f"Assigned IP {ip_addr} to {intf_name}")
                                    break
            
            except Exception as ip_error:
                if logger:
                    logger(f"Warning getting IP addresses: {str(ip_error)}")
            
            if logger:
                logger(f"Found {len(interfaces)} interfaces:")
                for intf in interfaces:
                    logger(f"  - {intf['interface']}: status={intf['status']}, mac={intf['mac_address'][:10]}..., ip={intf['ip_address']}")

            try:
                if logger:
                    logger("Getting interface descriptions...")

                desc_output = self.base.execute_command("enable", enable_mode=False)
                desc_output = self.base.execute_command(
                    "show interface description",
                    enable_mode=True
                )

                desc_map = {}

                for line in desc_output.splitlines():
                    line = line.strip()
                    if not line:
                        continue

                    # Skip header
                    if line.lower().startswith("interface"):
                        continue

                    # Cisco biasanya pakai spasi banyak sebagai separator
                    parts = re.split(r'\s{2,}', line)

                    if len(parts) >= 4:
                        iface = parts[0]
                        description = parts[3]
                        desc_map[iface] = description

                        if logger:
                            logger(f"Description found: {iface} -> {description}")

                # Inject description ke interface list
                for intf in interfaces:
                    if intf['interface'] in desc_map:
                        intf['description'] = desc_map[intf['interface']]

            except Exception as desc_error:
                if logger:
                    logger(f"Warning getting descriptions: {str(desc_error)}")

            return {
                'status': 'success',
                'interfaces': interfaces
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting interfaces: {str(e)}")
                import traceback
                logger(f"Traceback: {traceback.format_exc()}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def configure_interface(self, interface_name, params, logger=None):
        try:
            if logger:
                logger(f"Configuring interface {interface_name}...")

            self.base.execute_command("enable", enable_mode=False)    

            # Masuk global config
            self.base.execute_command("configure terminal", enable_mode=True)

            # Masuk interface
            self.base.execute_command(f"interface {interface_name}")

            # Description
            if 'description' in params:
                self.base.execute_command(f"description {params['description']}")

            # IP Address
            if 'ip_address' in params and 'subnet_mask' in params:
                self.base.execute_command(
                    f"ip address {params['ip_address']} {params['subnet_mask']}"
                )

            # Speed
            if params.get('speed') in ['10', '100', '1000', 'auto']:
                self.base.execute_command(f"speed {params['speed']}")

            # Duplex
            if params.get('duplex') in ['full', 'half', 'auto']:
                self.base.execute_command(f"duplex {params['duplex']}")

            # Admin status
            if 'admin_status' in params:
                if params['admin_status'] == 'up':
                    self.base.execute_command("no shutdown")
                else:
                    self.base.execute_command("shutdown")

            # KELUAR DARI CONFIG MODE (PENTING)
            self.base.execute_command("end")

            # Save config
            save_result = self.base.save_configuration()

            return {
                'status': 'success',
                'message': f'Interface {interface_name} configured',
                'save_result': save_result
            }

        except Exception as e:
            if logger:
                logger(f"Error configuring interface: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    
    def enable_interface(self, interface_name, logger=None):
        try:
            if logger:
                logger(f"Enabling interface {interface_name}...")

            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {interface_name}")
            self.base.execute_command("no shutdown")
            self.base.execute_command("end")

            save_result = self.base.save_configuration()

            return {
                'status': 'success',
                'message': f'Interface {interface_name} enabled',
                'save_result': save_result
            }

        except Exception as e:
            if logger:
                logger(f"Error enabling interface: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    
    def disable_interface(self, interface_name, logger=None):
        try:
            if logger:
                logger(f"Disabling interface {interface_name}...")

            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(f"interface {interface_name}")
            self.base.execute_command("shutdown")
            self.base.execute_command("end")

            save_result = self.base.save_configuration()

            return {
                'status': 'success',
                'message': f'Interface {interface_name} disabled',
                'save_result': save_result
            }

        except Exception as e:
            if logger:
                logger(f"Error disabling interface: {str(e)}")
            return {'status': 'error', 'error': str(e)}
