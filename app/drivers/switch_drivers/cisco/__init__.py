from .ssh_base import CiscoSSHBase
from .interface import CiscoInterfaceDriver
from .vlan import CiscoVlanDriver
from .stp import CiscoSTPDriver
from .qos import CiscoQoSDriver
from .security import CiscoSecurityDriver
from .lldp import CiscoLLDPDriver
from .system import CiscoSystemDriver
from .snmp import CiscoSnmpDriver
import re

class CiscoSSHDriver:
    """Complete Cisco driver untuk SDN management"""
    
    def __init__(self, config):
        if not config.get('username'):
            print(f"[CiscoSSHDriver] ERROR: Username not provided in config for {config.get('ip')}")
            # tidak lanjut jika tidak ada username
            raise ValueError(f"Username not provided for {config.get('ip')}")
        
        required_fields = ['ip', 'username']
        for field in required_fields:
            if field not in config or not config[field]:
                raise ValueError(f"Missing required field: {field}")

        self.config = config
        self.base = CiscoSSHBase(config)
        self.base.connect()
        
        # Initialize semua modules
        self.system = CiscoSystemDriver(config)
        self.interface = CiscoInterfaceDriver(config)
        self.vlan = CiscoVlanDriver(config)
        self.stp = CiscoSTPDriver(config)
        self.qos = CiscoQoSDriver(config)
        self.security = CiscoSecurityDriver(config)
        self.lldp = CiscoLLDPDriver(config)
        self.snmp = CiscoSnmpDriver(config) 
        
        # Set base reference untuk semua modules
        self._init_modules()
    
    def _init_modules(self):
        """Set base reference untuk semua modules"""
        modules = [
            self.system, self.interface, self.vlan, self.stp,
            self.qos, self.security, self.lldp, self.snmp
        ]
        
        for module in modules:
            if hasattr(module, 'set_base'):
                module.set_base(self.base)
            elif hasattr(module, 'base'):
                module.base = self.base
    
    def disconnect(self):
        """Disconnect dari device"""
        self.base.disconnect()

    def get_device_info(self):
        """Get comprehensive device information"""
        try:
            print(f"[CiscoSSHDriver] Getting device info for {self.config.get('ip')}")
            
            # Connect jika belum connected
            if not self.base.connected:
                print("[CiscoSSHDriver] Connecting to device...")
                self.base.connect()
            
            # Basic info structure dengan default values
            info = {
                'vendor': 'Cisco',
                'connected': self.base.connected,
                'southbound': 'paramiko',
                'device_type': 'switch',
                'status': 'active' if self.base.connected else 'inactive',
                'main_ip_address': self.config['ip'],
                'model': 'Unknown',
                'serial_number': '',
                'board': 'Unknown',
                'ios_version': 'Unknown',
                'os_version': 'Unknown',
                'main_interface': '',
                'main_mac_address': ''
            }

            if hasattr(self, 'snmp') and self.snmp is not None:
                self.snmp.set_base(self.base)
                print("[CiscoSSHDriver] SNMP driver base connection set")
            
            # === 1. GET HOSTNAME ===
            try:
                host_output = self.base.execute_command("show running-config | include hostname", enable_mode=True)
                if host_output and "ERROR" not in host_output:
                    host_match = re.search(r'hostname\s+(\S+)', host_output)
                    if host_match:
                        hostname = host_match.group(1)
                        info['hostname'] = hostname
                        info['identity'] = hostname
                        print(f"[DEBUG] Hostname from config: {hostname}")
            except Exception as e:
                print(f"[CiscoSSHDriver] Error getting hostname: {e}")
            
            # Fallback hostname
            if 'hostname' not in info:
                info['hostname'] = f"cisco-{self.config['ip']}"
                info['identity'] = info['hostname']
            
            # === 2. PARSE SHOW VERSION (UTAMA) ===
            version_output = self.base.execute_command("show version", enable_mode=False)
            
            if version_output and "ERROR" not in version_output:
                print(f"[DEBUG] Show version (first 800 chars):\n{version_output[:800]}")
                
                # Parse IOS Version
                ios_patterns = [
                    r'[Cc]isco\s+IOS\s+[Ss]oftware\s*[,]?\s*(?:\([^)]+\))?\s*[,\s]*[Vv]ersion\s+([^,\s]+)',
                    r'[Vv]ersion\s+([^,\s]+)',
                    r'[Ii][Oo][Ss]\s+[Vv]ersion\s+([^,\s]+)',
                    r'[Ss]oftware\s+[Vv]ersion\s+([^,\s]+)',
                    r'[Ss]ystem\s+[Ii]mage\s+[Ff]ile\s+is\s+"[^"]*[\\/][^\\/]*?([\d\.]+(?:\([^)]+\))?)\.'
                ]
                
                for pattern in ios_patterns:
                    version_match = re.search(pattern, version_output, re.IGNORECASE)
                    if version_match:
                        full_version = version_match.group(1).strip()
                        if full_version and len(full_version) > 2:
                            info['ios_version'] = full_version
                            info['os_version'] = full_version  # SIMPAN FULL VERSION
                            info['version'] = full_version
                            print(f"[DEBUG] Found IOS version: {full_version}")
                            break
                
                # Parse Model dari berbagai pola yang umum
                model_patterns = [
                    r'[Mm]odel\s+(?:[Nn]umber\s*)?[:\s]+\s*([A-Za-z0-9\-_]+[A-Za-z0-9])',
                    r'[Pp]rocessor\s+[Bb]oard\s+[Ii][Dd]\s+([A-Za-z0-9\-_]+[A-Za-z0-9])',
                    r'[Pp][Ii][Dd]\s*[:\s]+\s*([A-Za-z0-9\-_]+[A-Za-z0-9])',
                    r'[Ss]ystem\s+[Ii]mage\s+[Ff]ile\s+is\s+"[^"]*[\\/]([A-Za-z0-9\-_]+)\.',
                    r'WS-\w+-\w+',  # Pattern umum untuk model Cisco switch
                    r'C\d{4}[A-Z]?-\d+[A-Z]+-\d+[A-Z]?',  # Pattern Cisco Catalyst
                    r'CISCO\d+\w+'  # Pattern lainnya
                ]
                
                for pattern in model_patterns:
                    model_match = re.search(pattern, version_output)
                    if model_match:
                        model = model_match.group(0) if pattern.startswith('WS-') or pattern.startswith('C') else model_match.group(1)
                        model = model.strip()
                        # Filter out false positives
                        if (model and len(model) > 3 and 
                            model.lower() not in ['ios', 'software', 'version'] and
                            not model.replace('-', '').isdigit()):
                            info['model'] = model
                            info['board'] = model
                            print(f"[DEBUG] Found model: {model}")
                            break
                
                # Parse Serial Number
                processor_board_pattern = r'Processor\s+board\s+ID\s+(\S+)'
                serial_match = re.search(processor_board_pattern, version_output, re.IGNORECASE)
                
                if serial_match:
                    serial = serial_match.group(1).strip()
                    if serial:
                        info['serial_number'] = serial
                        print(f"[DEBUG] Found Processor board ID: {serial}")
                else:
                    # Coba pattern lainnya untuk serial number
                    serial_patterns = [
                        r'[Ss]ystem\s+[Ss]erial\s+[Nn]umber\s*[:\s]+\s*(\S+)',
                        r'[Ss]erial\s+[Nn]umber\s*[:\s]+\s*(\S+)',
                        r'[Ss][Nn]\s*[:\s]+\s*(\S+)',
                    ]
                    
                    for pattern in serial_patterns:
                        serial_match = re.search(pattern, version_output, re.IGNORECASE)
                        if serial_match:
                            serial = serial_match.group(1).strip()
                            if serial and len(serial) >= 6:
                                info['serial_number'] = serial
                                print(f"[DEBUG] Found serial number: {serial}")
                                break
            
            # === 3. TRY SHOW INVENTORY UNTUK DATA LEBIH AKURAT ===
            try:
                inv_output = self.base.execute_command("show inventory", enable_mode=True)
                if inv_output and "ERROR" not in inv_output:
                    print(f"[DEBUG] Show inventory output length: {len(inv_output)} chars")
                    
                    # Parse untuk model (jika belum ditemukan)
                    if info['model'] == 'Unknown':
                        # Cari pola PID atau NAME
                        pid_match = re.search(r'PID\s*:\s*([A-Za-z0-9\-_]+)', inv_output, re.IGNORECASE)
                        if pid_match:
                            model = pid_match.group(1).strip()
                            if model and '-' in model:  # Model Cisco biasanya ada tanda '-'
                                info['model'] = model
                                info['board'] = model
                                print(f"[DEBUG] Inventory PID/model: {model}")
                        else:
                            # Cari pola NAME dengan model
                            name_matches = re.findall(r'NAME\s*:\s*"([^"]+)"', inv_output, re.IGNORECASE)
                            for name in name_matches:
                                if 'cisco' in name.lower() or any(x in name.lower() for x in ['ws-', 'catalyst', 'nexus']):
                                    info['model'] = name
                                    print(f"[DEBUG] Inventory name: {name}")
                                    break
            except Exception as e:
                print(f"[CiscoSSHDriver] Error getting inventory: {e}")
            
            # === 4. DETEKSI MAIN INTERFACE===
            try:
                # Strategy 1: Gunakan show ip interface brief untuk menemukan interface dengan IP management
                ip_brief = self.base.execute_command("show ip interface brief", enable_mode=True)
                if ip_brief and "ERROR" not in ip_brief:
                    print(f"[DEBUG] IP Interface Brief:\n{ip_brief[:500]}")
                    
                    # Cari VLAN interface yang memiliki IP sama dengan device IP
                    vlan_interface = None
                    lines = ip_brief.split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if not line or line.lower().startswith('interface'):
                            continue
                        
                        parts = line.split()
                        if len(parts) >= 4:
                            interface = parts[0]
                            ip_addr = parts[1]
                            
                            # Jika interface ini memiliki IP yang sama dengan device
                            if ip_addr == self.config['ip']:
                                vlan_interface = interface
                                print(f"[DEBUG] Found management VLAN interface: {interface} with IP {ip_addr}")
                                break
                    
                    # **Strategy 2: Jika ada VLAN interface, cari physical interface yang membawa VLAN tersebut**
                    if vlan_interface and 'vlan' in vlan_interface.lower():
                        try:
                            # Dapatkan VLAN ID dari interface (misal Vlan100 -> 100)
                            vlan_id_match = re.search(r'vlan\s*(\d+)', vlan_interface, re.IGNORECASE)
                            if vlan_id_match:
                                vlan_id = vlan_id_match.group(1)
                                
                                vlan_detail = self.base.execute_command(f"show vlan id {vlan_id}", enable_mode=True)
                                if vlan_detail and "ERROR" not in vlan_detail:
                                    print(f"[DEBUG] VLAN {vlan_id} detail: {vlan_detail[:300]}")
                                    
                                    # Parse interfaces dari output show vlan id
                                    # Format: "100  VLAN0100                         active    Et0/1, Et0/2, Et0/3"
                                    for line in vlan_detail.split('\n'):
                                        if vlan_id in line and any(x in line.lower() for x in ['et', 'fa', 'gi', 'te']):
                                            # Cari interface fisik dalam line
                                            interface_patterns = [
                                                r'(Et\d+/\d+)',
                                                r'(Fa\d+/\d+)',
                                                r'(Gi\d+/\d+)',
                                                r'(Te\d+/\d+)',
                                                r'(Ethernet\d+/\d+)',
                                                r'(FastEthernet\d+/\d+)',
                                                r'(GigabitEthernet\d+/\d+)',
                                                r'(TenGigabitEthernet\d+/\d+)'
                                            ]
                                            
                                            for pattern in interface_patterns:
                                                interface_matches = re.findall(pattern, line, re.IGNORECASE)
                                                if interface_matches:
                                                    # Ambil interface pertama yang ditemukan
                                                    info['main_interface'] = interface_matches[0]
                                                    print(f"[DEBUG] Found physical interface from VLAN detail: {info['main_interface']}")
                                                    break
                                            
                                            if info['main_interface']:
                                                break
                                
                                # *Gunakan show interface status untuk mapping VLAN**
                                if not info['main_interface']:
                                    int_status = self.base.execute_command("show interface status", enable_mode=True)
                                    if int_status and "ERROR" not in int_status:
                                        print(f"[DEBUG] Interface status for VLAN mapping")
                                        lines = int_status.split('\n')
                                        
                                        for line in lines:
                                            line = line.strip()
                                            if not line or 'Port' in line:
                                                continue
                                            
                                            parts = line.split()
                                            if len(parts) >= 4:
                                                interface = parts[0]
                                                vlan_on_port = parts[3]
                                                
                                                # Cari interface yang berada di VLAN yang sama
                                                if vlan_on_port == vlan_id:
                                                    info['main_interface'] = interface
                                                    print(f"[DEBUG] Found interface from status on VLAN {vlan_id}: {interface}")
                                                    break
                        
                        except Exception as e:
                            print(f"[CiscoSSHDriver] Error finding physical interface for VLAN: {e}")
                    
                    # Strategy 3: Jika interface bukan VLAN, gunakan langsung
                    elif vlan_interface and not info['main_interface']:
                        info['main_interface'] = vlan_interface
                        print(f"[DEBUG] Using management interface directly: {vlan_interface}")
                    
                    # Strategy 4: Fallback ke interface fisik connected pertama
                    if not info['main_interface']:
                        int_status = self.base.execute_command("show interface status", enable_mode=True)
                        if int_status and "ERROR" not in int_status:
                            lines = int_status.split('\n')
                            
                            for line in lines:
                                line = line.strip()
                                if not line or 'Port' in line:
                                    continue
                                
                                parts = line.split()
                                if len(parts) >= 4:
                                    interface = parts[0]
                                    status = parts[2].lower() if len(parts) > 3 else ''
                                    
                                    # Ambil interface fisik pertama yang connected
                                    if (status == 'connected' and 
                                        any(x in interface.lower() for x in ['ethernet', 'fast', 'gigabit', 'ten'])):
                                        info['main_interface'] = interface
                                        print(f"[DEBUG] Found first connected physical interface: {interface}")
                                        break
            except Exception as e:
                print(f"[CiscoSSHDriver] Error detecting main interface: {e}")
                info['main_interface'] = 'Ethernet0/0'
            
            # === 5. GET MAC ADDRESS DARI MAIN INTERFACE ===
            try:
                if info['main_interface']:
                    mac_cmd = f"show interface {info['main_interface']} | include address|bia"
                    mac_output = self.base.execute_command(mac_cmd, enable_mode=True)
                    
                    if mac_output:
                        # Pattern untuk berbagai format MAC
                        mac_patterns = [
                            r'([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})',
                            r'[Aa]ddress\s+is\s+([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})',
                            r'[Hh]ardware\s+is\s+[^,]+,\s+[Aa]ddress\s+is\s+([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})',
                            r'[Bb][Ii][Aa]\s+([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})',
                            r'([0-9a-fA-F]{12})'
                        ]
                        
                        for pattern in mac_patterns:
                            mac_match = re.search(pattern, mac_output, re.IGNORECASE)
                            if mac_match:
                                mac_raw = mac_match.group(1).upper()
                                print(f"[DEBUG] Raw MAC found: {mac_raw}")
                                
                                # Convert ke format standar
                                if '.' in mac_raw:
                                    # Format Cisco: AABB.CC00.0100
                                    mac_parts = mac_raw.split('.')
                                    if len(mac_parts) == 3:
                                        mac_hex = ''.join(mac_parts)
                                        info['main_mac_address'] = ':'.join([mac_hex[i:i+2] for i in range(0, 12, 2)])
                                        info['mac_address_raw'] = mac_raw
                                        break
                                elif len(mac_raw) == 12:
                                    # Format hex plain: AABBCC000100
                                    info['main_mac_address'] = ':'.join([mac_raw[i:i+2] for i in range(0, 12, 2)])
                                    info['mac_address_raw'] = '.'.join([mac_raw[i:i+4] for i in range(0, 12, 4)])
                                    break
            except Exception as e:
                print(f"[CiscoSSHDriver] Error getting MAC address: {e}")
            
            # === 6. FALLBACK DAN VALIDATION ===
            # Jika model masih unknown, coba command khusus
            if info['model'] == 'Unknown':
                try:
                    model_cmd = "show version | include Model|WS-|CISCO"
                    model_output = self.base.execute_command(model_cmd, enable_mode=False)
                    if model_output:
                        # Cari pola umum model Cisco
                        model_matches = re.findall(r'(WS-[A-Z0-9\-]+|CISCO[A-Z0-9\-]+|C\d{4}[A-Z]?-\d+[A-Z]+)', model_output)
                        if model_matches:
                            info['model'] = model_matches[0]
                except:
                    pass
            
            # Jika serial masih kosong, coba command khusus
            if not info['serial_number']:
                try:
                    serial_cmd = "show version | include Serial|SN|System.serial|board ID"
                    serial_output = self.base.execute_command(serial_cmd, enable_mode=False)
                    if serial_output:
                        print(f"[DEBUG] Raw serial command output: '{serial_output}'")
                        
                        # **PERBAIKAN: Gunakan pattern yang tepat untuk Processor board ID**
                        # Pattern 1: Processor board ID 67110913
                        processor_pattern = r'Processor\s+board\s+ID\s+(\S+)'
                        processor_match = re.search(processor_pattern, serial_output, re.IGNORECASE)
                        
                        if processor_match:
                            info['serial_number'] = processor_match.group(1).strip()
                            print(f"[DEBUG] Found Processor board ID from fallback: {info['serial_number']}")
                        else:
                            # Pattern 2: Cari angka 8-12 digit
                            numeric_pattern = r'\b(\d{6,12})\b'
                            numeric_match = re.search(numeric_pattern, serial_output)
                            if numeric_match:
                                info['serial_number'] = numeric_match.group(1).strip()
                                print(f"[DEBUG] Found numeric serial from fallback: {info['serial_number']}")
                except Exception as e:
                    print(f"[CiscoSSHDriver] Error getting serial from fallback: {e}")
            
            # === 7. CLEAN UP DAN FINAL OUTPUT ===
            # Hapus whitespace dan karakter tidak perlu
            for key in ['model', 'serial_number', 'os_version', 'ios_version']:
                if key in info and isinstance(info[key], str):
                    info[key] = info[key].strip()
            
            print(f"[CiscoSSHDriver] FINAL Device info:")
            for key, value in sorted(info.items()):
                if key not in ['password'] and value:
                    print(f"  {key:20}: {value}")
            print("-" * 50)
            
            return info
            
        except Exception as e:
            print(f"[CiscoSSHDriver] ERROR in get_device_info: {e}")
            import traceback
            traceback.print_exc()
            
            # Return minimal info jika error
            return {
                'vendor': 'Cisco',
                'connected': False,
                'southbound': 'paramiko',
                'device_type': 'switch',
                'hostname': f"cisco-{self.config.get('ip', 'unknown')}",
                'identity': f"cisco-{self.config.get('ip', 'unknown')}",
                'os_version': 'Unknown',
                'ios_version': 'Unknown',
                'model': 'Unknown',
                'serial_number': '',
                'board': 'Unknown',
                'main_ip_address': self.config.get('ip', ''),
                'main_mac_address': '',
                'main_interface': 'unknown',
                'status': 'inactive',
                'error': str(e)
            }
    
    def test_connection(self):
        """Test koneksi Cisco Paramiko"""
        try:
            output = self.base.execute_command("show clock", enable_mode=False)
            return {
                'status': 'success',
                'connected': True,
                'output': output[:100]
            }
        except Exception as e:
            return {
                'status': 'error',
                'connected': False,
                'error': str(e)
            }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()