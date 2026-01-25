# app/drivers/server_drivers/server_metrics_manager.py
import json
import os
import subprocess
from datetime import datetime

class ServerFileManager:
    def __init__(self):
        # Path ke folder Prometheus
        BASE_DIR = os.getenv("PROMETHEUS_DIR", "/home/student/ryu/ryu/prometheus")
        self.targets_file = os.path.join(BASE_DIR, 'server_targets.json')
        
        # Inisialisasi file
        self._init_file()
    
    def _init_file(self):
        """Inisialisasi file JSON jika belum ada"""
        if not os.path.exists(self.targets_file):
            with open(self.targets_file, 'w') as f:
                json.dump([], f, indent=2)
            print(f"Initialized server targets file: {self.targets_file}")
    
    def sync_from_database(self, devices_data):
        """
        Sync devices dari database ke JSON file
        
        Args:
            devices_data: List devices dari database/controller
        """
        try:
            targets = []
            
            for device in devices_data:
                # Filter hanya server dengan southbound = server_api
                if device.get('southbound') == 'server_api':
                    # Ambil IP dari device
                    ip = device.get('main_ip_address') or device.get('ip')
                    
                    # Validasi IP
                    if not ip or ip == '127.0.0.1' or ip == 'unknown':
                        continue
                    
                    # Build target entry
                    target = {
                        "targets": [f"{ip}:9100"],  # Node Exporter port default
                        "labels": {
                            "instance": ip,
                            "hostname": device.get('hostname', 'unknown'),
                            "device_id": device.get('device_id', 'unknown'),
                            "job": "node-exporter-servers",
                            "group": "servers",
                            "os": device.get('os_version', 'unknown'),
                            "architecture": device.get('architecture', 'unknown'),
                            "southbound": "server_api",
                            "vendor": device.get('vendor', 'unknown'),
                            "virtualization": device.get('virtualization', 'physical'),
                            "registered_at": datetime.now().isoformat()
                        }
                    }
                    
                    # Tambah interface info jika ada
                    if 'interfaces' in device:
                        # Ambil IP dari interfaces untuk cross-check
                        for iface in device.get('interfaces', []):
                            if iface.get('ip_address') and iface.get('ip_address') != '':
                                target['labels']['interface_ip'] = iface['ip_address']
                                target['labels']['interface_name'] = iface.get('interface_name', 'unknown')
                                break
                    
                    targets.append(target)
                    print(f"Added server target: {ip} ({device.get('hostname')})")
            
            # Write ke file
            with open(self.targets_file, 'w') as f:
                json.dump(targets, f, indent=2)
            
            print(f"Synced {len(targets)} servers to {self.targets_file}")
            
            return len(targets)
            
        except Exception as e:
            print(f"Error syncing servers: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def get_targets(self):
        """Get current targets dari file"""
        try:
            with open(self.targets_file, 'r') as f:
                return json.load(f)
        except:
            return []
        
    def delete_device(self, device_id):
        """Remove a device from server targets JSON file"""
        try:
            # Baca file targets
            with open(self.targets_file, 'r') as f:
                targets = json.load(f)
            
            # Hitung target sebelum
            initial_count = len(targets)
            
            # Filter out device dengan device_id yang sesuai
            filtered_targets = [
                target for target in targets 
                if target.get("labels", {}).get("device_id") != device_id
            ]
            
            # Cek apakah ada perubahan
            if len(filtered_targets) == initial_count:
                print(f"Device {device_id} not found in server targets")
                return False
            
            # Tulis kembali ke file
            with open(self.targets_file, 'w') as f:
                json.dump(filtered_targets, f, indent=2)
            
            removed_count = initial_count - len(filtered_targets)
            print(f"Removed {removed_count} target(s) for device {device_id} from server_targets.json")
            
            # Restart Prometheus jika diperlukan
            # self.restart_prometheus()
            
            return True
            
        except FileNotFoundError:
            print(f"Server targets file not found: {self.targets_file}")
            return False
        except json.JSONDecodeError:
            print(f"Invalid JSON in {self.targets_file}")
            return False
        except Exception as e:
            print(f"Error deleting device {device_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    # def restart_prometheus(self):
    #     try:
    #         subprocess.run(["docker", "restart", "prometheus"], check=True)
    #     except Exception as e:
    #         raise Exception(f"Failed to restart prometheus: {str(e)}")