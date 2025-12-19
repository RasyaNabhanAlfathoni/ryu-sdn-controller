"""
Cisco System Operations - Discovery & Info
"""
import re
import json

class CiscoSystemDriver:
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def set_base(self, base):
        """Set base SSH connection"""
        self.base = base
    
    def get_system_info(self, logger=None):
        """Get detailed system information"""
        try:
            if logger:
                logger("Getting Cisco system info...")
            
            # Execute multiple show commands
            commands = {
                'version': "show version",
                'inventory': "show inventory",
                'hostname': "show running-config | include hostname",
                'interfaces': "show ip interface brief",
                'vlans': "show vlan brief",
                'interface_status': "show interfaces status",
                'clock': "show clock",
                'memory': "show memory statistics",
                'cpu': "show processes cpu sorted | exclude 0.00"
            }
            
            results = {}
            for key, cmd in commands.items():
                try:
                    output = self.base.execute_command(cmd, enable_mode=True)
                    results[key] = output[:1000]  # Limit output
                except Exception as e:
                    results[key] = f"Error: {str(e)}"
            
            # Parse semua info
            parsed_info = {
                'basic_info': self._parse_basic_info(results.get('version', '')),
                'hardware': self._parse_hardware_info(results.get('inventory', '')),
                'status': 'success',
                'raw_results': {k: len(v) for k, v in results.items()}  # Size info saja
            }
            
            # Parse hostname
            hostname_output = results.get('hostname', '')
            if 'hostname' in hostname_output.lower():
                for line in hostname_output.split('\n'):
                    if 'hostname' in line.lower():
                        parsed_info['basic_info']['hostname'] = line.split('hostname')[-1].strip()
                        break
            
            # Parse interfaces summary
            intf_output = results.get('interface_status', '')
            parsed_info['interface_summary'] = self._parse_interface_summary(intf_output)
            
            # Parse VLAN summary
            vlan_output = results.get('vlans', '')
            parsed_info['vlan_summary'] = self._parse_vlan_summary(vlan_output)
            
            # Parse CPU/Memory
            cpu_output = results.get('cpu', '')
            parsed_info['performance'] = self._parse_performance(cpu_output, results.get('memory', ''))
            
            if logger:
                logger(f"System info collected: {parsed_info['basic_info'].get('model', 'Unknown')}")
            
            return parsed_info
            
        except Exception as e:
            if logger:
                logger(f"Error getting system info: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _parse_basic_info(self, version_output):
        """Parse show version output"""
        info = {}
        
        lines = version_output.split('\n')
        for line in lines:
            line = line.strip()
            
            # IOS Version
            if 'Software' in line and 'Version' in line:
                version_match = re.search(r'Version\s+([\w\.\(\)]+)', line)
                if version_match:
                    info['ios_version'] = version_match.group(1)
            
            # Model
            elif 'bytes of memory' in line.lower():
                model_match = re.search(r'(\d{3,4}[A-Z]*)', line)
                if model_match:
                    info['model'] = model_match.group(1)
            
            # Serial
            elif 'System Serial Number' in line or 'Serial Number' in line:
                serial_match = re.search(r'[Ss]erial [Nn]umber.*?(\S+)', line)
                if serial_match:
                    info['serial'] = serial_match.group(1)
            
            # Uptime
            elif 'uptime is' in line.lower():
                uptime_match = re.search(r'uptime is (.+)$', line)
                if uptime_match:
                    info['uptime'] = uptime_match.group(1)
            
            # ROM Version
            elif 'ROM:' in line:
                rom_match = re.search(r'ROM:\s*(.+)', line)
                if rom_match:
                    info['rom_version'] = rom_match.group(1)
        
        return info
    
    def _parse_hardware_info(self, inventory_output):
        """Parse show inventory output"""
        hardware = []
        
        lines = inventory_output.split('\n')
        current_item = {}
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('NAME:'):
                if current_item:
                    hardware.append(current_item)
                current_item = {'name': line.split('NAME:')[-1].strip()}
            
            elif line.startswith('DESCR:'):
                current_item['description'] = line.split('DESCR:')[-1].strip()
            
            elif line.startswith('PID:'):
                current_item['pid'] = line.split('PID:')[-1].strip()
            
            elif line.startswith('VID:'):
                current_item['vid'] = line.split('VID:')[-1].strip()
            
            elif line.startswith('SN:'):
                current_item['sn'] = line.split('SN:')[-1].strip()
        
        if current_item:
            hardware.append(current_item)
        
        return hardware
    
    def _parse_interface_summary(self, intf_output):
        """Parse show interfaces status"""
        interfaces = []
        
        lines = intf_output.split('\n')
        for line in lines:
            if 'Gi' in line or 'Fa' in line or 'Te' in line:
                parts = line.split()
                if len(parts) >= 5:
                    intf_info = {
                        'interface': parts[0],
                        'status': parts[1],
                        'vlan': parts[2],
                        'duplex': parts[3],
                        'speed': parts[4] if len(parts) > 4 else '',
                        'type': parts[5] if len(parts) > 5 else ''
                    }
                    interfaces.append(intf_info)
        
        return {
            'total': len(interfaces),
            'up': len([i for i in interfaces if i['status'] == 'connected']),
            'down': len([i for i in interfaces if i['status'] != 'connected']),
            'interfaces': interfaces[:10]  # Limit output
        }
    
    def _parse_vlan_summary(self, vlan_output):
        """Parse show vlan brief"""
        vlans = []
        
        lines = vlan_output.split('\n')
        for line in lines:
            if line.strip() and line[0].isdigit():
                parts = line.split()
                if len(parts) >= 2:
                    vlan_info = {
                        'vlan_id': parts[0],
                        'name': parts[1],
                        'status': 'active' if len(parts) > 2 and 'active' in parts[2].lower() else 'inactive',
                        'ports': ' '.join(parts[3:]) if len(parts) > 3 else ''
                    }
                    vlans.append(vlan_info)
        
        return {
            'total': len(vlans),
            'active': len([v for v in vlans if v['status'] == 'active']),
            'vlans': vlans[:20]  # Limit output
        }
    
    def _parse_performance(self, cpu_output, memory_output):
        """Parse CPU and memory usage"""
        perf = {
            'cpu_5s': '0%',
            'cpu_1m': '0%', 
            'cpu_5m': '0%',
            'memory_used': '0',
            'memory_free': '0'
        }
        
        # Parse CPU
        cpu_lines = cpu_output.split('\n')
        for line in cpu_lines:
            if 'CPU utilization' in line:
                # Format: "CPU utilization for five seconds: 2%/0%; one minute: 1%; five minutes: 1%"
                matches = re.findall(r'(\d+)%', line)
                if len(matches) >= 3:
                    perf['cpu_5s'] = f"{matches[0]}%"
                    perf['cpu_1m'] = f"{matches[1]}%"
                    perf['cpu_5m'] = f"{matches[2]}%"
        
        # Parse Memory
        mem_lines = memory_output.split('\n')
        for line in mem_lines:
            if 'Total' in line and 'Used' in line and 'Free' in line:
                # Format: "Total: 262144000, Used: 85294080, Free: 176849920"
                numbers = re.findall(r'(\d+)', line)
                if len(numbers) >= 3:
                    perf['memory_total'] = numbers[0]
                    perf['memory_used'] = numbers[1]
                    perf['memory_free'] = numbers[2]
        
        return perf
    
    def save_config(self, logger=None):
        """Save running configuration to startup"""
        try:
            if logger:
                logger("Saving configuration...")
            
            output = self.base.execute_command("write memory", enable_mode=True)
            
            if logger:
                logger("Configuration saved successfully")
            
            return {
                'status': 'success',
                'message': 'Configuration saved successfully',
                'output': output[:200]
            }
            
        except Exception as e:
            if logger:
                logger(f"Error saving config: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def reboot(self, logger=None):
        """Reboot switch dengan konfirmasi"""
        try:
            if logger:
                logger("Rebooting Cisco switch...")
            
            # Save config dulu
            self.save_config(logger)
            
            # Send reload command
            output = self.base.execute_command("reload", enable_mode=True)
            
            if logger:
                logger("Switch reboot command sent")
            
            return {
                'status': 'success',
                'message': 'Reboot command sent to switch',
                'note': 'Switch akan reboot dalam 1 menit'
            }
            
        except Exception as e:
            if logger:
                logger(f"Error rebooting switch: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_running_config(self, logger=None):
        """Get running configuration"""
        try:
            if logger:
                logger("Getting running configuration...")
            
            config = self.base.execute_command("show running-config", enable_mode=True)
            
            if logger:
                logger(f"Config retrieved ({len(config)} bytes)")
            
            return {
                'status': 'success',
                'config': config,
                'size': len(config)
            }
            
        except Exception as e:
            if logger:
                logger(f"Error getting config: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }