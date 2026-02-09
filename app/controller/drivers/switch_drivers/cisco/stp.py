import re
import time

class CiscoSTPDriver:
    def __init__(self, config):
        self.config = config
        self.base = None
    
    def set_base(self, base):
        """Set base SSH connection"""
        self.base = base
    
    def get_stp_info(self, logger=None):
        try:
            summary_out = self.base.execute_command("enable", enable_mode=False)

            summary_out = self.base.execute_command(
                "show spanning-tree summary", enable_mode=True
            )

            summary = self._parse_stp_summary(summary_out)

            vlan_ids = self._extract_vlans_from_summary(summary_out)

            vlan_data = {}

            for vlan in vlan_ids:
                out = self.base.execute_command("enable", enable_mode=False)
                out = self.base.execute_command(
                    f"show spanning-tree vlan {vlan}",
                    enable_mode=True
                )
                vlan_data[str(vlan)] = self._parse_stp_vlan(out)

            portfast = self._parse_portfast_config()

            return {
                "status": "success",
                "stp": summary,
                "vlans": vlan_data,
                "portfast": portfast
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _parse_stp_vlan(self, output):
        data = {
            "is_root": False,
            "bridge_id": None,
            "priority": None,
            "root_bridge": None,
            "root_priority": None,
            "interfaces": {}
        }

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            # Root ID
            if line.startswith("Root ID"):
                match = re.search(r'Priority\s+(\d+)', line)
                if match:
                    data["root_priority"] = int(match.group(1))

            # Bridge ID
            elif line.startswith("Bridge ID"):
                match = re.search(r'Priority\s+(\d+)', line)
                if match:
                    data["priority"] = int(match.group(1))

            elif "This bridge is the root" in line:
                data["is_root"] = True

            # Skip header
            elif (
                line.startswith("Interface")
                or "Role" in line and "Sts" in line and "Cost" in line
            ):
                continue

            # Interface entry (Gi, Fa, Te, Eth, Po, dll)
            elif re.match(r'^(Gi|Fa|Te|Eth|Po)\S+', line):
                parts = re.split(r'\s+', line)
                if len(parts) >= 4:
                    iface = parts[0]
                    cost = int(parts[3]) if parts[3].isdigit() else 0

                    data["interfaces"][iface] = {
                        "role": parts[1] if len(parts) > 1 else "Unknown",
                        "state": parts[2] if len(parts) > 2 else "Unknown",
                        "cost": cost,
                        "portfast": False
                    }

        return data

    def _extract_vlans_from_summary(self, output):
        vlans = []
        for line in output.splitlines():
            line = line.strip()
            # Cocokkan VLAN0001, VLAN1, VLAN0010, dll
            match = re.match(r'^VLAN\s*0*(\d+)', line, re.IGNORECASE)
            if match:
                vlans.append(int(match.group(1)))
        return vlans

    def _parse_stp_summary(self, output):
        """Parse show spanning-tree summary dengan parsing yang lebih baik"""
        summary = {
            'stp_enabled': False,
            'mode': 'Unknown',
            'vlans': 0
        }
        
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip().lower()
            
            # Deteksi STP enabled dari berbagai kondisi
            # 1. Jika ada "switch is in" mode tertentu, berarti STP enabled
            if 'switch is in' in line:
                summary['stp_enabled'] = True
                
                # Extract mode dari line
                if 'rapid-pvst' in line:
                    summary['mode'] = 'Rapid-PVST'
                elif 'pvst' in line:
                    summary['mode'] = 'PVST'
                elif 'mst' in line:
                    summary['mode'] = 'MST'
                elif 'rstp' in line:
                    summary['mode'] = 'RSTP'
            
            # 2. Atau jika ada "spanning tree enabled" secara eksplisit
            elif 'spanning tree enabled' in line:
                summary['stp_enabled'] = 'yes' in line or 'true' in line or 'enabled' in line
            
            # 3. Deteksi mode dari line lain
            elif 'mode' in line:
                if 'rapid-pvst' in line:
                    summary['mode'] = 'Rapid-PVST'
                    summary['stp_enabled'] = True
                elif 'pvst' in line:
                    summary['mode'] = 'PVST'
                    summary['stp_enabled'] = True
                elif 'mst' in line or 'multiple' in line:
                    summary['mode'] = 'MST'
                    summary['stp_enabled'] = True
                elif 'rstp' in line:
                    summary['mode'] = 'RSTP'
                    summary['stp_enabled'] = True
            
            # Cari jumlah VLAN dari tabel
            if 'vlans' in line and 'blocking' not in line and 'listening' not in line:
                # Pattern: "2 vlans" di akhir output
                match = re.search(r'(\d+)\s+vlans?', line)
                if match:
                    summary['vlans'] = int(match.group(1))
        
        # **PERBAIKAN TAMBAHAN: Jika mode diketahui tapi stp_enabled masih false, set ke true**
        if summary['mode'] != 'Unknown' and not summary['stp_enabled']:
            summary['stp_enabled'] = True
        
        return summary
    
    def enable_stp(self, logger=None):
        """Enable STP globally dengan benar"""
        try:
            if logger:
                logger("Enabling STP...")
            
            # Masuk ke config mode
            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            
            # Enable STP dengan Rapid-PVST
            self.base.execute_command("spanning-tree mode rapid-pvst", enable_mode=True)
            
            # Enable system-id extension (untuk VLAN extended)
            self.base.execute_command("spanning-tree extend system-id", enable_mode=True)
            
            # Keluar dari config mode
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            save_result = self.base.save_configuration()
            
            if logger:
                logger("STP enabled successfully")
                logger(f"Configuration saved: {save_result}")
            
            # Tunggu sebentar agar config apply
            time.sleep(2)
            
            return {
                'status': 'success',
                'message': 'STP enabled with Rapid-PVST mode',
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error enabling STP: {str(e)}")
                import traceback
                logger(f"Traceback: {traceback.format_exc()}")
            
            return {
                'status': 'error',
                'error': str(e)
            }

    def disable_stp(self, logger=None):
        """Disable STP globally"""
        try:
            if logger:
                logger("Disabling STP globally...")
            
            # Masuk ke config mode
            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            
            # Disable STP secara global
            self.base.execute_command("no spanning-tree mode", enable_mode=True)
            
            # Keluar dari config mode
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            save_result = self.base.save_configuration()
            
            if logger:
                logger("STP disabled globally")
                logger(f"Configuration saved: {save_result}")
            
            return {
                'status': 'success',
                'message': 'STP disabled globally',
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error disabling STP: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }

    def enable_stp_vlan(self, vlan, logger=None):
        """Enable STP untuk VLAN tertentu"""
        try:
            if logger:
                logger(f"Enabling STP for VLAN {vlan}")

            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(
                f"spanning-tree vlan {vlan} priority 32768",
                enable_mode=True
            )
            self.base.execute_command("end", enable_mode=True)

            save_result = self.base.save_configuration()

            return {
                'status': 'success',
                'message': f'STP enable for VLAN {vlan}',
                'save_result': save_result
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def disable_stp_vlan(self, vlan, logger=None):
        """Disable STP untuk VLAN tertentu"""
        try:
            if logger:
                logger(f"Disabling STP for VLAN {vlan}")

            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            self.base.execute_command(
                f"no spanning-tree vlan {vlan}",
                enable_mode=True
            )
            self.base.execute_command("end", enable_mode=True)

            save_result = self.base.save_configuration()

            return {
                'status': 'success',
                'message': f'STP disabled for VLAN {vlan}',
                'save_result': save_result
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    
    def set_bridge_priority(self, priority, vlan=None, logger=None):
        """Set bridge priority"""
        try:
            if logger:
                logger(f"Setting bridge priority to {priority}...")
            
            # Validasi priority (harus kelipatan 4096)
            try:
                priority_int = int(priority)
                if priority_int % 4096 != 0:
                    return {
                        'status': 'error',
                        'error': f'Priority {priority} must be multiple of 4096'
                    }
            except ValueError:
                return {
                    'status': 'error',
                    'error': f'Invalid priority: {priority}'
                }
            
            # Masuk ke config mode
            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            
            if not vlan:
                return {
                    'status': 'error',
                    'error': 'Cisco STP priority MUST be set per VLAN'
                }

            self.base.execute_command(
                f"spanning-tree vlan {vlan} priority {priority}",
                enable_mode=True
            )
            
            # Keluar dari config mode
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            save_result = self.base.save_configuration()
            
            if logger:
                logger(f"Bridge priority set to {priority}")
                logger(f"Configuration saved: {save_result}")
            
            return {
                'status': 'success',
                'message': f'Bridge priority set to {priority}',
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error setting bridge priority: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def configure_portfast(self, interface=None, logger=None):
        """Configure PortFast on interface"""
        try:
            if logger:
                logger(f"Configuring PortFast on {interface or 'all'}...")
            
            # Masuk ke config mode
            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            
            if interface:
                # PortFast pada interface spesifik
                self.base.execute_command(f"interface {interface}", enable_mode=True)
                self.base.execute_command("spanning-tree portfast", enable_mode=True)
                self.base.execute_command("exit", enable_mode=True)
            else:
                # PortFast default pada semua interface
                self.base.execute_command("spanning-tree portfast default", enable_mode=True)
            
            # Keluar dari config mode
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            save_result = self.base.save_configuration()
            
            if logger:
                logger("PortFast configured")
                logger(f"Configuration saved: {save_result}")
            
            return {
                'status': 'success',
                'message': 'PortFast configured',
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error configuring PortFast: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
        
    def _parse_portfast_config(self):
        out = self.base.execute_command("enable", enable_mode=False)
        out = self.base.execute_command(
            "show running-config | section ^interface",
            enable_mode=True
        )

        result = {
            "default": False,
            "interfaces": []
        }

        current_iface = None

        for line in out.splitlines():
            line = line.rstrip()

            if not line:
                continue

            # Deteksi interface
            if line.startswith("interface"):
                parts = line.split()
                current_iface = parts[1] if len(parts) > 1 else None

            # Deteksi portfast di dalam interface
            elif "spanning-tree portfast" in line and current_iface:
                result["interfaces"].append(current_iface)

        # Cek global default
        global_out = self.base.execute_command("enable", enable_mode=False)
        global_out = self.base.execute_command(
            "show running-config | include ^spanning-tree portfast",
            enable_mode=True
        )

        if "default" in global_out:
            result["default"] = True

        return result
    
    def disable_portfast(self, interface=None, logger=None):
        """Disable PortFast on interface"""
        try:
            if logger:
                logger(f"Disabling PortFast on {interface or 'all'}...")
            
            # Masuk ke config mode
            self.base.execute_command("enable", enable_mode=False)
            self.base.execute_command("configure terminal", enable_mode=True)
            
            if interface:
                # Disable PortFast pada interface spesifik
                self.base.execute_command(f"interface {interface}", enable_mode=True)
                self.base.execute_command("no spanning-tree portfast", enable_mode=True)
                self.base.execute_command("exit", enable_mode=True)
            else:
                # Disable PortFast default pada semua interface
                self.base.execute_command("no spanning-tree portfast default", enable_mode=True)
            
            # Keluar dari config mode
            self.base.execute_command("end", enable_mode=True)
            
            # Save configuration
            save_result = self.base.save_configuration()
            
            if logger:
                logger("PortFast disabled")
                logger(f"Configuration saved: {save_result}")
            
            return {
                'status': 'success',
                'message': 'PortFast disabled',
                'save_result': save_result
            }
            
        except Exception as e:
            if logger:
                logger(f"Error disabling PortFast: {str(e)}")
            
            return {
                'status': 'error',
                'error': str(e)
            }
