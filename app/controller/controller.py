import os, sys 
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.append(BASE_DIR)

# Untuk Wazuh Cert
try:
    import ssl_patch  # Ini akan apply monkey patch
    print("SSL patch imported successfully")
except ImportError:
    print("Warning: ssl_patch.py not found, SSL recursion bug may occur")

from ryu.base import app_manager
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from ryu.lib import hub
from webob import Response
import json, uuid, time
from datetime import datetime
import socket

# === Database Integration ===
from database.device_repository import DeviceRepository
from database.db_connection import DBConnection

# === SNMP Driver ===
from drivers.snmp_file_manager import SNMPFileManager

# === Router Driver ===
from drivers.router_drivers.mikrotik.routeros_api import RouterOSApiDriver
from actions.routers.mikrotik import MikrotikRouterActions

# === Switch Driver  ===
from drivers.switch_drivers.cisco import CiscoSSHDriver
from actions.switchs.cisco import CiscoSwitchActions
from drivers.switch_drivers.ruijie.auto_discover import AutoDiscoverRuijie
from actions.switchs.ruijie.global_actions import RuijieSwitchGlobalActions
from actions.switchs.ruijie.device_actions import RuijieSwitchActions
from drivers.switch_drivers.ruijie.ruijie_cloud import RuijieCloudDriver

# === Access-Point Driver ===
from drivers.access_point_drivers.unifi.paramiko import UnifiParamikoDriver
from drivers.access_point_drivers.unifi.auto_discover import AutoDiscoverAPUnifi
from actions.access_points.unifi.global_actions import UnifiAccessPointGlobalActions
from actions.access_points.unifi.device_actions import UnifiAccessPointActions
from actions.access_points.mikrotik import MikrotikAPActions

# === Server Driver ===
from drivers.server_drivers.server_api import ServerAPI
from actions.servers.server import ServerActions
from drivers.server_file_manager import ServerFileManager

# === Wazuh Driver ===
from drivers.wazuh_drivers.wazuh_api import WazuhAPI
from drivers.wazuh_drivers.wazuh_indexer import WazuhIndexerAPI

# === Loki Driver ===
from drivers.loki_api import LokiAPI

API_INSTANCE_NAME = 'northbound_api'

# Ini sesuaikan dengan secret key nya
ALLOWED_API_KEYS = set([os.environ.get("RYU_API_KEY", "agent-secret-token-1")])

def to_postgresql_datetime(ts):
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    return ts

def _check_api_key(req):
    # WebOb request: headers accessible via req.headers
    headers = getattr(req, 'headers', {})
    api_key = headers.get('X-API-KEY') if headers else None
    return api_key in ALLOWED_API_KEYS

class JobStore:
    def __init__(self): self.data = {}
    def create(self, payload):
        jid = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
        self.data[jid] = {"status":"queued","payload":payload,"logs":[],"result":None}
        return jid
    def set(self, jid, **kw): self.data[jid].update(kw)
    def append_log(self, jid, line): self.data[jid]["logs"].append(line)

class DeviceRegistry:
    def __init__(self):
        self.db = {}  # id -> dict {ip, auth, southbound, version}

    def create(self, data):
        device_id = data["id"]
        if device_id in self.db:
            raise ValueError(f"Device {device_id} already exists")
        self.db[device_id] = data
        return data

    def get(self, did):
        if did not in self.db:
            raise KeyError(f"Device {did} not found")
        return self.db[did]

    def list(self):
        return list(self.db.values())

class Orchestrator(app_manager.RyuApp):
    _CONTEXTS = {'wsgi': WSGIApplication}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        self.jobs = JobStore()
        self.devices = DeviceRegistry()
        wsgi.register(NorthboundApi, {API_INSTANCE_NAME: self})

        self.queue = hub.Queue()
        self.worker = hub.spawn(self.worker_loop)

        # ruijie auto discovery (BACKGROUND THREAD)
        self.ruijie_discover_thread = hub.spawn(
            AutoDiscoverRuijie.loop
        )

        # unifi auto discovery (BACKGROUND THREAD)
        self.unifi_discover_thread = hub.spawn(
            AutoDiscoverAPUnifi.loop
        )
        # Inisialisasi server metrics manager
        self.server_file_manager = ServerFileManager()
        hub.sleep(2)
        # Start health check thread
        self.health_check_thread = hub.spawn(self.health_check_loop)
        # Start auto-sync thread (setiap 30 detik)
        self.sync_thread = hub.spawn(self.auto_sync_servers)

        # Initialize Wazuh Manager API
        try:
            wazuh_api_url = os.getenv('WAZUH_API_URL')
            wazuh_user = os.getenv('WAZUH_API_USER')
            wazuh_password = os.getenv('WAZUH_API_PASSWORD')

            if all([wazuh_api_url, wazuh_user, wazuh_password]):
                self.wazuh_api = WazuhAPI(
                    base_url=wazuh_api_url,
                    username=wazuh_user,
                    password=wazuh_password,
                    core=self,  # Pass core reference untuk job creation
                    logger=self.logger
                )
                self.logger.info("Wazuh integration initialized successfully")
            else:
                self.logger.warning("Wazuh environment variables not set")
                self.wazuh_api = None

        except Exception as e:
            self.logger.error(f"Failed to initialize Wazuh integration: {e}")
            self.wazuh_api = None

        # Initialize Wazuh Indexer API
        try:
            indexer_url = os.getenv('WAZUH_INDEXER_URL')
            indexer_user = os.getenv('WAZUH_INDEXER_USER')
            indexer_password = os.getenv('WAZUH_INDEXER_PASSWORD')

            if all([indexer_url, indexer_user, indexer_password]):
                self.wazuh_indexer = WazuhIndexerAPI(
                    base_url=indexer_url,
                    username=indexer_user,
                    password=indexer_password,
                    logger=self.logger
                )
                self.logger.info("Wazuh Indexer initialized")
            else:
                self.logger.warning("Wazuh Indexer env not set")
                self.wazuh_indexer = None

        except Exception as e:
            self.logger.error(f"Wazuh Indexer init failed: {e}")
            self.wazuh_indexer = None

        try:
            from database.device_repository import DeviceRepository
            loki_url = os.environ.get('LOKI_URL', 'http://localhost:3100')
            
            self.loki_api = LokiAPI(
                base_url=loki_url,
                device_repository=DeviceRepository,
                logger=self.logger.info
            )
            self.logger.info("Loki API initialized with device validation")
        except Exception as e:
            self.logger.error(f"Loki initialization failed: {e}")
            self.loki_api = None

    def health_check_loop(self):
        """Background thread untuk health check semua devices"""
        import time
        
        print("Starting health check service")
        
        while True:
            try:
                hub.sleep(60)  # Check setiap 1 menit
                
                # Ambil semua devices dari database
                devices = DeviceRepository.list_all()
                
                for device in devices:
                    device_id = device.get('device_id')
                    device_type = device.get('device_type')
                    southbound = device.get('southbound')
                    ip_address = device.get('main_ip_address')
                    
                    # Skip jika tidak ada IP
                    if not ip_address:
                        continue
                    
                    is_active = False
                    
                    # Health check berdasarkan device type
                    if device_type == 'server' and southbound == 'server_api':
                        # Test koneksi ke agent API
                        is_active = self.check_server_agent_health(ip_address)
                    elif southbound == 'routeros_api':
                        # Test koneksi ke RouterOS API
                        is_active = self.check_routeros_health(device)
                    elif device_type == 'switch' and southbound == 'paramiko':
                        # Test koneksi ke Cisco Paramiko SSH
                        is_active = self.check_switch_health(device)
                    elif device_type == 'access_point' and southbound == 'paramiko':
                        # Test koneksi ke Paramiko
                        is_active = self.check_access_point_health(device)
                    
                    # Update status berdasarkan health check
                    if is_active:
                        DeviceRepository.update_device_status(
                            device_id, 
                            'active',
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        )
                    else:
                        DeviceRepository.update_device_status(
                            device_id, 
                            'inactive'
                        )
                        
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                hub.sleep(300)  # Tunggu 5 menit jika error
    
    def check_server_agent_health(self, ip_address):
        """Check jika server agent API accessible"""
        import requests
        
        try:
            # Coba akses endpoint health agent
            response = requests.get(
                f"http://{ip_address}:8081/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def check_routeros_health(self, device):
        """Check jika RouterOS API accessible"""
        try:
            device_id = device.get('device_id')            
            try:
                db_device = DeviceRepository.find_by_device_id(device_id)
                if not db_device:
                    return False
                    
                ip_address = db_device.get('main_ip_address')
                username = db_device.get('username')
                password = db_device.get('password')
                
            except Exception as db_err:
                ip_address = device.get('main_ip_address')
                username = device.get('username')
                password = device.get('password')
            
            # Validasi data
            if not ip_address:
                return False
            if not username:
                username = "admin"  # Default Mikrotik username
            if not password:
                possible_passwords = ["", "admin", "password", "123456"]
                for pw in possible_passwords:
                    try:
                        driver_config = {
                            "ip": ip_address,
                            "username": username,
                            "password": pw,
                            "device_id": device_id,
                            "use_ssl": False
                        }
                        
                        driver = RouterOSApiDriver(driver_config)                
                        info = driver.get_device_info()
                        
                        if info.get('connected', False):
                            # Update database dengan password yang berhasil (jika ada)
                            if pw:
                                try:
                                    DeviceRepository.update_router(device_id, pw)
                                except:
                                    pass
                            
                            return True
                    except Exception as e:
                        continue
                
                return False
            
            # Jika password ada, coba koneksi normal
            try:
                driver_config = {
                    "ip": ip_address,
                    "username": username,
                    "password": password,
                    "device_id": device_id,
                    "use_ssl": False
                }
                
                driver = RouterOSApiDriver(driver_config)                
                info = driver.get_device_info()
                
                connected = info.get('connected', False)
                if connected:
                    return True
                else:
                    return False
                    
            except ValueError as e:
                return False
            except Exception as e:
                return False
                
        except Exception as e:
            return False
        
    def check_switch_health(self, device):
        """Check jika Cisco switch Paramiko accessible"""
        try:
            device_id = device.get('device_id')
            self.logger.info(f"Health checking Cisco switch: {device_id}")
            
            # Gunakan DeviceRepository untuk ambil data
            try:
                # Ambil data FRESH dari database
                db_device = DeviceRepository.find_switch(device_id)
                
                if not db_device:
                    self.logger.error(f"Switch {device_id} not found in database")
                    return False
                    
                # Gunakan data dari database
                ip_address = db_device.get('main_ip_address')
                username = db_device.get('username')
                password = db_device.get('password')
                
            except Exception as db_err:
                self.logger.error(f"Database error for {device_id}: {db_err}")
                # Fallback ke data dari parameter
                ip_address = device.get('main_ip_address')
                username = device.get('username')
                password = device.get('password')
            
            # Validasi data
            if not ip_address:
                self.logger.error(f"No IP address for device {device_id}")
                return False
            if not username:
                self.logger.warning(f"No username for Cisco device {device_id}, using default")
            if not password:
                self.logger.warning(f"No password configured for Cisco device {device_id}")
                return False
            
            # trim whitespace
            password = str(password).strip()
            
            # VALIDASI FINAL SEBELUM BUAT DRIVER
            if not password:
                self.logger.error(f"Empty password after trimming for {device_id}")
                return False
            
            # **BUAT DRIVER DENGAN KONFIG YANG BENAR**
            try:
                driver_config = {
                    "ip": ip_address,
                    "username": username,
                    "password": password,
                    "enable": True,  # Cisco biasanya butuh enable mode
                    "device_id": device_id,
                    "port": 22  # default SSH port
                }
                
                self.logger.info(f"Creating CiscoSSHDriver with config: IP={ip_address}, User={username}")
                
                driver = CiscoSSHDriver(driver_config)
                
                # Coba get device info
                self.logger.info(f"Testing connection to {ip_address}...")
                info = driver.get_device_info()
                
                # Disconnect bersih
                try:
                    driver.disconnect()
                except:
                    pass
                
                connected = info.get('connected', False)
                
                if connected:
                    return True
                else:
                    return False
                    
            except ValueError as e:
                # Invalid config
                self.logger.error(f"Invalid config for Cisco health check {device_id}: {e}")
                return False
            except Exception as e:
                # Connection failed
                self.logger.error(f"Cisco health check connection failed for {device_id}: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                return False
                
        except Exception as e:
            self.logger.error(f"Switch health check failed for {device.get('device_id', 'unknown')}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def check_access_point_health(self, device):
        """Check jika Access Point via Paramiko accessible"""
        try:
            device_id = device.get('device_id')
            
            # Gunakan DeviceRepository untuk ambil data FRESH
            try:
                db_device = DeviceRepository.find_by_device_id(device_id)
                if not db_device:
                    return False
                    
                ip_address = db_device.get('main_ip_address')
                username = db_device.get('username')
                password = db_device.get('password')
                
            except Exception as db_err:
                ip_address = device.get('main_ip_address')
                username = device.get('username')
                password = device.get('password')
            
            if not ip_address:
                self.logger.error(f"No IP address for AP {device_id}")
                return False
            
            # Fallback credentials untuk Unifi
            if not username:
                username = "ubnt"
            
            if not password:
                possible_passwords = ["", "admin", "password", "123456"]
                
                for pw in possible_passwords:
                    try:
                        driver_config = {
                            "ip": ip_address,
                            "username": username,
                            "password": pw,
                            "device_id": device_id,
                            "use_ssl": False
                        }
                        
                        driver = RouterOSApiDriver(driver_config)                
                        info = driver.get_device_info()
                        
                        if info.get('connected', False):
                            if pw:
                                try:
                                    DeviceRepository.update_access_point(device_id, pw)
                                except:
                                    pass
                            
                            return True
                    except Exception as e:
                        continue
            try:
                driver_config = {
                    "ip": ip_address,
                    "username": username,
                    "password": password,
                    "device_id": device_id
                }
                                
                driver = UnifiParamikoDriver(driver_config)
                info = driver.get_device_info()
                
                connected = info.get('connected', False)
                if connected:
                    return True
                else:
                    return False
                    
            except ValueError as e:
                return False
            except Exception as e:
                import traceback
                self.logger.error(traceback.format_exc())
                return False
                
        except Exception as e:
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def detect_vendor(self, dev):
        # == Deteksi otomatis tipe perangkat ==

        # (Mikrotik, RouterOS API)
        try:
            driver = RouterOSApiDriver(dev)
            info = driver.get_device_info()
            device_type = info.get("device_type", "router")
            
            info.update({
                "southbound": "routeros_api",
                "vendor": "MikroTik",
                "device_type": device_type,
                "connected": True
            })
            return info
        except Exception as e:
            self.logger.debug(f"Mikrotik detection failed: {e}")
            pass  # Kalau gagal connect Mikrotik, lanjut test lain

        # (Server Linux)
        try:
            srv = ServerAPI(dev)
            info = srv.get_basic_info()
            info["southbound"] = "server_api"
            info["vendor"] = "GenericServer"
            info["connected"] = True
            return info
        except Exception:
            pass

        # (Cisco Switch - PARAMIKO)
        try:
            with CiscoSSHDriver(dev) as cisco:
                info = cisco.get_device_info()
                if info.get('connected'):
                    info["southbound"] = "paramiko"
                    info["vendor"] = "Cisco"
                    info["device_type"] = "switch"
                    return info
        except Exception as e:
            self.logger.debug(f"Cisco detection failed: {e}")

        # (Unifi Access Point, Paramiko)
        try:
            driver = UnifiParamikoDriver(dev)
            info = driver.get_device_info()
            info["southbound"] = "paramiko"
            info["vendor"] = "Unifi"
            info["connected"] = True
            return info
        except Exception:
            pass

        # untuk Cisco / Juniper (next)
        return {
            "vendor": "Unknown",
            "southbound": "Unknown",
            "connected": False
        }

    def worker_loop(self):
        while True:

            jid, payload = self.queue.get()
            try:
                self.jobs.set(jid, status="running")
                self.run_command(jid, payload)
                self.jobs.set(jid, status="success")
            except Exception as e:
                self.jobs.set(jid, status="failed", result=str(e))

    def run_command(self, jid, p):
        action = p["action"]
        params = p.get("params", {})

        # WAZUH ACTIONS (GLOBAL - TIDAK BUTUH device_id)
        wazuh_global_actions = [
            "wazuh.manager.info", "wazuh.manager.stats", "wazuh.manager.configuration",
            "wazuh.agent.list", "wazuh.agent.detail", "wazuh.agent.status", "wazuh.agent.config",
           "wazuh.sca.summary", "wazuh.sca.events", "wazuh.fim.summary", "wazuh.fim.events",
            "wazuh.fim.timeline", "wazuh.fim.action_summary", "wazuh.fim.most_active_agents", 
            "wazuh.threat.summary", "wazuh.threat.events", "wazuh.threat.failed_login",  
            "wazuh.threat.success_login", "wazuh.threat.high_level", "wazuh.threat.top_mitre", 
            "wazuh.threat.top_agents", "wazuh.discover.logs", "wazuh.system.processes", 
            "wazuh.system.hardware",
        ]
        
        # SNMP ACTIONS (GLOBAL - TIDAK BUTUH device_id)
        snmp_global_actions = [
            "snmp.device.add", "snmp.metric.add", "snmp.test.oid",
            "snmp.metric.delete", "snmp.metric.edit", "snmp.device.delete", 
            "snmp.device.edit"
        ]

        # LOKI ACTIONS (GLOBAL - TIDAK BUTUH device_id)
        loki_global_actions = [
            "loki.query.logs", "loki.search.logs", "loki.health"
        ]
        
        # GLOBAL ACTIONS
        global_actions = (
            wazuh_global_actions + snmp_global_actions + loki_global_actions +
            list(UnifiAccessPointGlobalActions.get_actions(None).keys()) +
            list(RuijieSwitchGlobalActions.get_actions(None).keys())
        )
        
        # GLOBAL ACTIONS langsung dispatch tanpa device_id
        if action in global_actions:
            self.jobs.append_log(jid, f"Executing GLOBAL action: {action}")
            try:
                result = self.dispatch(None, action, params, jid)
                self.jobs.set(jid, result=result)
                return result
            except Exception as e:
                self.jobs.set(jid, status="failed", result=str(e))
                raise
        
        # DEVICE-BASED ACTION
        device_id = p.get("device_id")
        if not device_id:
            raise ValueError("device_id is required")

        # Cari device - prioritaskan memory registry dulu (karena device ada di memory)
        dev_config = None
    
        # Method 1: PRIORITAS - Cari di database (sumber utama)
        try:
            dev_row = DeviceRepository.find_by_device_id(device_id)
            if dev_row:
                self.jobs.append_log(jid, f"Found in database: {dev_row.get('device_type')}")
                
                # Konversi format database ke format yang dibutuhkan driver
                dev_config = {
                    "id": dev_row["device_id"],
                    "device_id": dev_row["device_id"],
                    "ip": dev_row.get("main_ip_address") or dev_row.get("ip"),
                    "main_ip_address": dev_row.get("main_ip_address"),
                    "username": dev_row.get("username") or dev_row.get("main_username", "unknown"),
                    "password": dev_row.get("password", ""),
                    "vendor": dev_row.get("vendor", "unknown"),
                    "device_type": dev_row.get("device_type", "unknown"),
                    "southbound": dev_row.get("southbound", "unknown"),
                    "hostname": dev_row.get("hostname", "unknown"),
                    # Tambahkan field lain yang diperlukan driver
                    "identity": dev_row.get("identity", dev_row.get("hostname", "unknown")),
                    "version": dev_row.get("os_version", ""),
                    "model": dev_row.get("model", ""),
                    "serial-number": dev_row.get("serial_number", "")
                }
                self.jobs.append_log(jid, f"Database config: {dev_config}")
        except Exception as e:
            self.jobs.append_log(jid, f"Database lookup failed: {e}")

        # Method 2: Fallback - Cari di memory registry (jika tidak ditemukan di database)
        if not dev_config and hasattr(self, 'devices'):
            try:
                memory_dev = self.devices.get(device_id)
                if memory_dev:
                    self.jobs.append_log(jid, "Found device in memory registry (fallback)")
                    dev_config = memory_dev
            except Exception as e:
                self.jobs.append_log(jid, f"Memory registry lookup failed: {e}")

        # Jika masih tidak ditemukan, coba cari dari database langsung
        if not dev_config:
            try:
                # Coba cari semua devices dari database
                db_devices = DeviceRepository.list_all()
                for db_dev in db_devices:
                    if db_dev.get("device_id") == device_id:
                        # Konversi format
                        dev_config = {
                            "id": db_dev["device_id"],
                            "device_id": db_dev["device_id"],
                            "ip": db_dev.get("main_ip_address"),
                            "main_ip_address": db_dev.get("main_ip_address"),
                            "username": db_dev.get("username", "unknown"),
                            "password": db_dev.get("password", ""),
                            "vendor": db_dev.get("vendor", "unknown"),
                            "device_type": db_dev.get("device_type", "unknown"),
                            "southbound": db_dev.get("southbound", "unknown"),
                            "hostname": db_dev.get("hostname", "unknown"),
                            "identity": db_dev.get("hostname", "unknown")
                        }
                        self.jobs.append_log(jid, f"Found in list_all database: {device_id}")
                        break
            except Exception as e:
                self.jobs.append_log(jid, f"Secondary database lookup failed: {e}")

        if not dev_config:
            self.jobs.append_log(jid, f"ERROR: Device {device_id} not found in any registry")
            # Tambahkan debug info
            try:
                all_ids = DeviceRepository.get_all_device_ids()
                self.jobs.append_log(jid, f"Available device IDs in database: {all_ids}")
            except:
                self.jobs.append_log(jid, "Cannot fetch device IDs from database")
            raise ValueError(f"Device '{device_id}' not found")

        # Create driver
        try:
            driver = self.pick_driver(dev_config)
            self.jobs.append_log(jid, f"Driver created successfully: {type(driver).__name__}")
            
            # PERBAIKAN: Simpan result dari dispatch ke job store
            result = self.dispatch(driver, action, params, jid)
            self.jobs.set(jid, result=result) 
            return result
            
        except Exception as e:
            self.jobs.append_log(jid, f"Driver creation failed: {e}")
            raise

    def pick_driver(self, dev):
        sb = (dev.get("southbound") or "").lower()
        vendor = (dev.get("vendor") or "").lower()
        device_type = (dev.get("device_type") or "").lower()
        if sb == "routeros_api" and vendor == "mikrotik":
            return RouterOSApiDriver(dev)
        elif sb == "paramiko" and vendor == "unifi":
            return UnifiParamikoDriver(dev)
        elif sb == "server_api":
            return ServerAPI(dev)
        elif sb == "paramiko" and (vendor == "cisco" or device_type == "switch"):
            return CiscoSSHDriver(dev)
        elif sb == "ruijie_cloud" and vendor == "ruijie":
            return RuijieCloudDriver(dev)
        else:
            raise ValueError(f"Unknown southbound driver: {sb}")

    def dispatch(self, d, action, params, jid, dev_config=None):
        # Global actions (tidak memerlukan device driver)
        global_actions = {
            # === SNMP Actions ===
            "snmp.metric.add": lambda p, logger: SNMPFileManager().add_metric(
                module=p["module"],
                metric=p
            ),
            "snmp.metric.delete": lambda p, logger: SNMPFileManager().delete_metric(
                module=p["module"],
                name=p["name"]
            ),
            "snmp.metric.edit": lambda p, logger: SNMPFileManager().edit_metric(
                module=p["module"],
                name=p["name"],
                new_values=p["new_values"]
            ),
            "snmp.device.add": lambda p, logger: SNMPFileManager().add_device(p),
            "snmp.device.delete": lambda p, logger: SNMPFileManager().delete_device(p["id"]),
            "snmp.device.edit": lambda p, logger: SNMPFileManager().edit_device(p["id"], p["data"]),
            "snmp.test.oid": lambda p, logger: SNMPFileManager().test_snmp(
                ip=p["ip"],
                community=p.get("community", "public"),
                oid=p["oid"],
                version=p.get("version")
            ),

            # === Wazuh Actions ===
            "wazuh.manager.info": lambda p, logger: self.wazuh_api.get_manager_info(logger=logger),
            "wazuh.manager.stats": lambda p, logger: self.wazuh_api.get_manager_stats(logger=logger),
            "wazuh.manager.configuration": lambda p, logger: self.wazuh_api.get_manager_configuration(logger=logger),
            "wazuh.agent.list": lambda p, logger: self.wazuh_api.get_agents(p.get("filters"), logger),
            "wazuh.agent.detail": lambda p, logger: self.wazuh_api.get_agent_detail(p["agent_id"], logger),
            "wazuh.agent.status": lambda p, logger: self.wazuh_api.get_agent_status(p["agent_id"], logger),
            "wazuh.sca.summary": lambda p, logger: self.wazuh_api.get_security_configuration_assessment(
                p["agent_id"], logger
            ),
            "wazuh.sca.events": lambda p, logger: self.wazuh_indexer.sca_events(
                agent_id=p["agent_id"],
                hours=p.get("hours", 24)
            ),
            "wazuh.fim.summary": lambda p, logger: self.wazuh_api.get_fim_data(
                p.get("agent_id"), p.get("filters"), logger
            ),
            "wazuh.fim.events": lambda p, logger: self.wazuh_indexer.fim_events(
                agent_id=p.get("agent_id"),
                hours=p.get("hours", 24)
            ),
            "wazuh.fim.timeline": lambda p, logger: self.wazuh_indexer.fim_timeline(
                agent_id=p.get("agent_id"),
                hours=p.get("hours", 24)
            ),
            "wazuh.fim.action_summary": lambda p, logger: self.wazuh_indexer.fim_action_summary(
                hours=p.get("hours", 24),
                agent_id=p.get("agent_id")
            ),
            "wazuh.fim.most_active_agents": lambda p, logger: self.wazuh_indexer.fim_most_active_agents(
                hours=p.get("hours", 24),
                top=p.get("top", 5)
            ),
            "wazuh.threat.summary": lambda p, logger: self.wazuh_indexer.threat_summary(
                hours=p.get("hours", 24)
            ),
            "wazuh.threat.events": lambda p, logger: self.wazuh_indexer.threat_events(
                hours=p.get("hours", 24),
                size=p.get("size", 100),
                agent_id=p.get("agent_id"),
            ),
            "wazuh.threat.failed_login": lambda p, logger: self.wazuh_indexer.threat_failed_logins(
                hours=p.get("hours", 24),
                agent_id=p.get("agent_id"),
            ),
            "wazuh.threat.success_login": lambda p, logger: self.wazuh_indexer.threat_success_logins(
                hours=p.get("hours", 24),
                agent_id=p.get("agent_id"),
            ),
            "wazuh.threat.high_level": lambda p, logger: self.wazuh_indexer.threat_high_level(
                hours=p.get("hours", 24),
                agent_id=p.get("agent_id"),
            ),
            "wazuh.threat.top_mitre": lambda p, logger: self.wazuh_indexer.top_mitre_attacks(
                hours=p.get("hours", 24),
                agent_id=p.get("agent_id"),
                top=p.get("top", 10)
            ),
            "wazuh.threat.top_agents": lambda p, logger: self.wazuh_indexer.top_threat_agents(
                hours=p.get("hours", 24),
                top=p.get("top", 5)
            ),
            "wazuh.discover.logs": lambda p, logger: self.wazuh_indexer.discover_logs(
                index=p.get("index", "wazuh-alerts-*"),
                keyword=p.get("keyword"),
                hours=p.get("hours", 24),
                size=p.get("size", 100)
            ),
            "wazuh.system.hardware": lambda p, logger: self.wazuh_api.get_syscollector_hardware(
                agent_id=p.get("agent_id"),
                logger=logger
            ),
            "wazuh.system.processes": lambda p, logger: self.wazuh_api.get_syscollector_processes(
                agent_id=p.get("agent_id"),
                filters=p.get("filters", {}),
                logger=logger
            ),

            # === LOKI ACTIONS ===
            "loki.query.logs": lambda p, logger: self.loki_api.query_range(
                query=p.get("query", ""),
                limit=p.get("limit", 100),
                hours=p.get("hours", 1)
            ),
            "loki.search.logs": lambda p, logger: self.loki_api.search_logs(
                params=p,
                logger=logger
            ),
            "loki.health": lambda p, logger: self.loki_api.health(
                params=p,
                logger=logger
            ),
        }

        # Tambahkan Unifi global actions
        global_actions.update(UnifiAccessPointGlobalActions.get_actions(None))
        global_actions.update(RuijieSwitchGlobalActions.get_actions(None))

        # Device-based actions
        device_actions = {}
        
        if d is not None:
            # Deteksi tipe driver
            driver_type = "unknown"
            if hasattr(d, '__class__'):
                if 'RouterOS' in d.__class__.__name__:
                    driver_type = "mikrotik"
                    device_type = (d.dev.get("device_type") or "").lower()
                    if device_type == "access_point":
                        device_actions = MikrotikAPActions.get_actions(d)
                    else:
                        device_actions = MikrotikRouterActions.get_actions(d)
                elif 'Paramiko' in d.__class__.__name__:
                    driver_type = "unifi"
                    device_actions = UnifiAccessPointActions.get_actions(d)
                elif 'ServerAPI' in d.__class__.__name__:
                    driver_type = "server"
                    wazuh_api = self.wazuh_api if hasattr(self, 'wazuh_api') and self.wazuh_api is not None else None
                    device_actions = ServerActions.get_actions(d, self.wazuh_api)
                elif 'CiscoSSH' in d.__class__.__name__:
                    driver_type = "cisco_switch"
                    device_actions = CiscoSwitchActions.get_actions(d)
                elif 'RuijieCloud' in d.__class__.__name__:
                    driver_type = "ruijie_cloud"
                    device_actions = RuijieSwitchActions.get_actions(d)

        # Gabungkan semua actions
        all_actions = {**global_actions, **device_actions}

        if action not in all_actions:
            self.jobs.append_log(jid, f"ERROR: Unknown action '{action}'")
            raise ValueError(f"Unknown action: {action}")

        try:
            self.jobs.append_log(jid, f"Executing {action} with params: {params}")
            result = all_actions[action](params, logger=lambda s: self.jobs.append_log(jid, s))
            
            self.jobs.append_log(jid, f"{action} completed successfully")
            return result
        except Exception as e:
            self.jobs.append_log(jid, f"EXCEPTION in {action}: {str(e)}")
            self.jobs.append_log(jid, f"Exception type: {type(e).__name__}")
            import traceback
            tb_lines = traceback.format_exc().splitlines()
            for line in tb_lines:
                self.jobs.append_log(jid, f"   {line}")
            raise

    def auto_sync_servers(self):
        """Background thread untuk auto sync servers ke Prometheus"""
        import time
        from datetime import datetime
        
        print("Starting auto-sync service for Prometheus targets")
        
        while True:
            try:
                # Tunggu sebelum sync pertama
                hub.sleep(10)  # Tunggu 10 detik pertama
                
                while True:
                    try:
                        # Ambil devices dari database
                        from database.device_repository import DeviceRepository
                        devices = DeviceRepository.list_all()
                        
                        # Sync ke file JSON
                        count = self.server_file_manager.sync_from_database(devices)
                        
                        if count > 0:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Auto-synced {count} servers to Prometheus")
                        
                        # Tunggu 30 detik sebelum sync berikutnya
                        hub.sleep(30)
                        
                    except Exception as e:
                        print(f"Auto-sync error: {e}")
                        hub.sleep(60)  # Tunggu lebih lama jika error
                        
            except Exception as e:
                print(f"Fatal auto-sync error: {e}")
                hub.sleep(300)  # Tunggu 5 menit jika fatal error

class NorthboundApi(ControllerBase):
    def __init__(self, req, link, data, **config):
        super().__init__(req, link, data, **config)
        self.core: Orchestrator = data[API_INSTANCE_NAME]

    @route('jobs', '/jobs', methods=['POST'])
    def create_job(self, req, **kwargs):
        p = json.loads(req.body)
        jid = self.core.jobs.create(p)
        self.core.queue.put((jid, p))
        body = json.dumps({"job_id": jid, "status":"queued"})
        return self._resp(req, body)

    @route('jobs', '/jobs/{jid}', methods=['GET'])
    def get_job(self, req, jid, **kwargs):
        b = json.dumps(self.core.jobs.data.get(jid, {"error":"not found"}))
        return self._resp(req, b)
    
    @route('health', '/health', methods=['GET'])
    def health_controller_db(self, req, **kwargs):
        status = {
            "controller": "ok",
            "database": "unknown"
        }

        # cek koneksi database
        try:
            from database.db_connection import DBConnection

            with DBConnection.get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1;")
                cur.fetchone()
                cur.close()

            status["database"] = "ok"

        except Exception as e:
            status["database"] = "error"
            status["db_error"] = str(e)

        # status
        if status["database"] == "ok":
            return self._resp(req, json.dumps(status), status=200)
        else:
            return self._resp(req, json.dumps(status), status=500)

    # === Device Management ===
    # Create devices, disini ambil data dari payload agent_register
    @route('devices', '/devices', methods=['POST'])
    def create_device(self, req, **kwargs):
        """Register device dengan struktur sesuai skema database"""
        if not _check_api_key(req):
            return self._resp(req, json.dumps({"status": "error", "error": "unauthorized"}), status=401)
        
        data = json.loads(req.body)
        
        try:
            # === DETECT DEVICE TYPE ===
            southbound_type = data.get("southbound", "").lower()
            is_server = southbound_type in ["server", "server_api"]
            is_mikrotik = southbound_type in ["mikrotik", "routeros_api"]
            is_cisco = southbound_type in ["cisco", "paramiko"]
            is_unifi = southbound_type in ["unifi", "paramiko"]
            
            # === GENERATE CONSISTENT DEVICE ID ===
            def generate_device_id(device_data, registration_mode):
                import hashlib

                vendor = device_data.get("vendor", "unknown")
                device_type = device_data.get("device_type", "unknown")
                ip = device_data.get("ip") or device_data.get("main_ip_address", "unknown")
                serial = (
                    device_data.get("serial_number")
                    or device_data.get("serial-number")
                    or "unknown"
                )

                unique_components = [vendor, device_type, serial, ip]

                unique_str = "_".join(map(str, unique_components))
                digest = hashlib.sha256(unique_str.encode()).hexdigest()[:10]

                return f"dev_{digest}"

            device_type = None  
            if is_server:
                device_type = "server"
                registration_mode = "server_agent"
            elif is_mikrotik:
                info = self.core.detect_vendor(data)
                device_type = info.get("device_type", "router")
                registration_mode = "active_discovery"
            elif is_cisco:
                device_type = "switch" 
                registration_mode = "paramiko_discovery"
            elif is_unifi:
                device_type = "access_point" 
                registration_mode = "paramiko_discovery"
            else:
                return self._resp(req, json.dumps({
                    "status": "error", 
                    "error": f"Unknown southbound type: {southbound_type}"
                }), 400)
            
            # === HANDLE SERVER AGENT REGISTRATION ===
            if is_server:
                device_ip_from_body = data.get("main_ip_address")
                client_ip = req.remote_addr
                
                # Determine final IP (prioritize body IP)
                if device_ip_from_body and device_ip_from_body != '127.0.0.1':
                    final_ip = device_ip_from_body
                elif client_ip and client_ip != '127.0.0.1':
                    final_ip = client_ip
                else:
                    # Fallback to headers
                    forwarded_for = req.headers.get('X-Forwarded-For')
                    real_ip = req.headers.get('X-Real-IP')
                    if forwarded_for:
                        final_ip = forwarded_for.split(',')[0].strip()
                    elif real_ip and real_ip != '127.0.0.1':
                        final_ip = real_ip
                    else:
                        final_ip = device_ip_from_body or "unknown"
                
                data["ip"] = str(final_ip)
                data["main_ip_address"] = str(final_ip)
                
                # Generate device ID yang KONSISTEN berdasarkan IP + MAC
                device_id = generate_device_id(data, registration_mode)
                print(f"[CONTROLLER] Generated device_id: {device_id} for IP: {final_ip}")
                
                # Cek apakah device_id ini sudah ada di database
                existing_device = DeviceRepository.find_by_device_id(device_id)
                
                if existing_device:
                    print(f"[CONTROLLER] Found existing device {device_id}, updating...")
                    # Device sudah ada, lalu UPDATE
                else:
                    print(f"[CONTROLLER] Creating new device {device_id}")
                    # Device belum ada, lalu INSERT baru
                
                data["id"] = device_id
                data["device_id"] = device_id
                
                # Data langsung dari payload (bukan dari meta)
                server_data = {
                    "status": str(data.get("status", "active")),
                    "southbound": str(data.get("southbound", "server_api")),
                    "hostname": str(data.get("identity", data.get("hostname", "unknown"))),
                    "main_username": str(data.get("main_username", "unknown")),
                    "os_version": str(data.get("os", "unknown")),  # Map os -> os_version
                    "architecture": str(data.get("architecture", "")),
                    "architecture_bits": str(data.get("architecture_bits", "")),
                    "processor_type": str(data.get("processor_type", "")),
                    "vendor": str(data.get("vendor", "unknown")),
                    "serial_number": str(data.get("serial_number", "")),
                    "connected": True,
                    "main_ip_address": str(data.get("main_ip_address", "")),
                    "main_interface": str(data.get("main_interface", "unknown")),
                    "main_mac_address": str(data.get("main_mac_address", "unknown")),
                    "last_seen": to_postgresql_datetime(time.time())
                }

                # Hanya ambil dari meta yang diperlukan
                meta = data.get("meta", {})
                if meta and "virtualization" in meta:
                    virtualization_data = meta["virtualization"]
                    
                    # OPTION 1: Ambil hanya type saja (paling sederhana)
                    if isinstance(virtualization_data, dict):
                        # Ambil virtualization type, default "physical"
                        server_data["virtualization"] = str(virtualization_data.get("hypervisor", "physical"))
                    else:
                        server_data["virtualization"] = str(virtualization_data)
                else:
                    server_data["virtualization"] = "physical"
    
                # Update data dengan server_data
                data.update(server_data)

            # === HANDLE MIKROTIK/ACTIVE DISCOVERY REGISTRATION ===
            elif is_mikrotik:
                # Test connection first
                info = self.core.detect_vendor(data)
                
                if not info.get("connected", False):
                    return self._resp(req, json.dumps({
                        "status": "error",
                        "error": "Unable to connect to device or detect vendor",
                        "details": info
                    }), 400)
                
                device_id = generate_device_id(data, registration_mode)
                data["id"] = device_id
                data["device_id"] = device_id
                data.update(info)
                detected_device_type = info.get("device_type", "router")
                
                # Map MikroTik specific fields
                data.update({
                    "status": "active",
                    "southbound": "routeros_api",
                    "vendor": "MikroTik",
                    "identity": info.get("identity"),
                    "username": data.get("username", "admin"),
                    "os_version": info.get("version"),
                    "model": info.get("model"),
                    "board_name": info.get("board-name", ""),
                    "serial_number": info.get("serial-number"),
                    "main_ip_address": data.get("ip"),
                    "main_mac_address": info.get("mac-address"),
                    "main_interface": info.get("main_interface"),
                    "device_type": detected_device_type,
                })

                # AUTO ADD TO SNMP TARGETS (jika bukan access point)
                if detected_device_type != "access_point":
                    try:
                        snmp = SNMPFileManager()
                        snmp.add_device({
                            "device_id": device_id,
                            "ip": data["ip"],
                            "module": "mikrotik",  # Module khusus Mikrotik
                            "device_name": info.get("identity") or data.get("hostname", device_id),
                            "location": data.get("location", "Unknown"),
                            "community": data.get("snmp_community", "public")
                        })
                        data["snmp_target_status"] = "success"
                    except Exception as e:
                        data["snmp_target_status"] = f"failed: {str(e)}"
                else:
                    data["snmp_target_status"] = "skipped (access_point)"

            elif is_cisco:
                # Pakai CiscoSSHDriver untuk mendapatkan data REAL dari device
                try:
                    # Buat driver untuk test connection
                    cisco_driver = CiscoSSHDriver({
                        "ip": data['ip'],
                        "username": data.get("username", "admin"),
                        "password": data.get("password", ""),
                        "enable": True,
                        "device_id": ""  # Akan diisi nanti
                    })
                    
                    # Test connection dengan driver yang sudah diperbaiki
                    info = cisco_driver.get_device_info()
                    
                    # Validasi info sebelum dipakai
                    if info is None:
                        return self._resp(req, json.dumps({
                            "status": "error",
                            "error": "Driver failed to return device information (got None)"
                        }), 400)
                    
                    # Pastikan info adalah dictionary sebelum panggil .get()
                    if not isinstance(info, dict):
                        return self._resp(req, json.dumps({
                            "status": "error", 
                            "error": f"Driver returned invalid data type: {type(info)}"
                        }), 400)
                    
                    # Sekarang baru cek koneksi
                    if not info.get('connected', False):
                        return self._resp(req, json.dumps({
                            "status": "error",
                            "error": info.get('error', 'Device not connected'),
                            "details": info
                        }), 400)
                    
                    # Generate device ID
                    device_id = generate_device_id(data, registration_mode)
                    data["id"] = device_id
                    data["device_id"] = device_id
                    
                    # Update data dengan info REAL dari device (bukan generic)
                    data.update({
                        "status": "active",
                        "southbound": "paramiko",
                        "vendor": "Cisco",
                        "device_type": "switch",
                        "username": data.get("username", "admin"),
                        "password": data.get("password", ""),
                        "identity": info.get('identity', info.get('hostname', f"cisco-{data['ip']}")),
                        "os_version": info.get('os_version', info.get('ios_version', 'Unknown')),
                        "model": info.get('model', 'Unknown'),
                        "serial_number": info.get('serial_number', info.get('serial', '')),
                        "main_ip_address": info.get('main_ip_address', data['ip']),
                        "main_mac_address": info.get('main_mac_address', ''),
                        "main_interface": info.get('main_interface', 'eth0'),
                        "connected": True,
                        "last_seen": to_postgresql_datetime(time.time()),
                    })
                    try:
                        # Gunakan driver yang sama untuk konfigurasi SNMP
                        cisco_snmp_config = {
                            "enabled": True,
                            "community": "public",
                            "community_access": "RO",
                            "contact": "Network Admin",
                            "location": data.get("location", "Unknown"),
                            "add_to_prometheus": True  # Flag untuk SNMP target
                        }
                        
                        # Konfigurasi SNMP di switch
                        snmp_result = cisco_driver.snmp.configure_snmp(cisco_snmp_config, logger=self.core.logger.info)
                        
                        if snmp_result.get('status') != 'success':
                            self.core.logger.warning(f"SNMP configuration failed: {snmp_result}")
                            # Lanjutkan tanpa SNMP
                            data["snmp_configured"] = False
                        else:
                            data["snmp_configured"] = True
                            data["snmp_community"] = "public"
                            
                    except Exception as snmp_err:
                        self.core.logger.error(f"SNMP setup error: {snmp_err}")
                        data["snmp_configured"] = False

                    try:
                        snmp = SNMPFileManager()
                        # Gunakan default SNMP community untuk Cisco
                        community = data.get("snmp_community", "public")
                        
                        snmp.add_device({
                            "device_id": device_id,
                            "ip": data["ip"],
                            "module": "cisco",  # Pakai module "cisco" yang sudah ada di snmp.yml
                            "device_name": info.get('identity') or data.get('hostname', device_id),
                            "location": data.get("location", "Unknown"),
                            "community": community  # Opsional
                        })    
                        data["snmp_target_status"] = "success"
                    
                    except Exception as e:
                        data["snmp_target_status"] = f"failed: {str(e)}"
                        self.core.logger.error(f"Failed to add Cisco switch to SNMP targets: {e}")
                    
                except Exception as e:
                    print(f"Cisco registration error: {e}")
                    import traceback
                    traceback.print_exc()
                    return self._resp(req, json.dumps({
                        "status": "error",
                        "error": f"Registration failed: {str(e)}"
                    }), 400)
                
            # === HANDLE UNIFI ===
            elif is_unifi:
                # === CONNECT & COLLECT INFO ===
                driver = UnifiParamikoDriver(data)
                info = driver.get_device_info()

                if not info.get("connected"):
                    return self._resp(req, json.dumps({
                        "status": "error",
                        "error": "Unable to connect to UniFi device"
                    }), 400)

                # === GENERATE DEVICE ID ===
                device_id = generate_device_id(data, registration_mode)
                data["id"] = device_id
                data["device_id"] = device_id

                # === MERGE INFO ===
                data.update(info)

                data.update({
                    "device_type": "access_point",
                    "southbound": "paramiko",
                    "vendor": "unifi",
                    "identity": info.get("identity"),
                    "main_ip_address": info.get("main_ip_address") or data.get("ip"),
                    "main_mac_address": info.get("main_mac_address"),
                    "status": "active",
                    "connected": True
                })

                # AUTO ADD TO SNMP TARGETS
                try:
                    snmp = SNMPFileManager()
                    snmp.add_device({
                        "device_id": device_id,
                        "ip": data["ip"],
                        "module": info.get("vendor", "Unknown").lower(),
                        "device_name": info.get("identity") or data.get("hostname", device_id),
                        "location": data.get("location", "Unknown")
                    })
                except Exception as e:
                    data["snmp_target_status"] = f"failed: {str(e)}"

            else:
                return self._resp(req, json.dumps({
                    "status": "error", 
                    "error": "Unknown device type."
                }), 400)

            # === DATABASE REGISTRATION ===
            db_registered = False
            try:
                # Prepare common device data untuk network_devices table
                common_data = {
                    "device_id": device_id,
                    "device_type": device_type,
                    "southbound": data.get("southbound", "unknown"),
                    "status": "active",
                    "last_seen": to_postgresql_datetime(time.time())
                }
                
                # Check for duplicates by device_id
                existing = DeviceRepository.find_by_device_id(device_id)
                
                if existing: # Untuk Update data Existing
                    # Update existing device
                    DeviceRepository.update_network_device(device_id, common_data)
                    
                    # Update specific table
                    if device_type == "server":
                        server_data = {
                            "device_id": device_id,
                            "hostname": data.get("identity", data.get("hostname", "unknown")),
                            "main_username": data.get("main_username", "unknown"),
                            "os_version": data.get("os_version", "unknown"),
                            "architecture": data.get("architecture"),
                            "architecture_bits": data.get("architecture_bits"),
                            "processor_type": data.get("processor_type"),
                            "vendor": data.get("vendor", "unknown"),
                            "serial_number": data.get("serial_number", "unknown"),
                            "main_ip_address": data.get("main_ip_address"),
                            "main_mac_address": data.get("main_mac_address"),
                            "main_interface": data.get("main_interface"),
                            "southbound": data.get("southbound", "unknown"),
                            "status": "active",
                            "virtualization": data.get("virtualization"),
                            "last_seen": to_postgresql_datetime(time.time())
                        }
                        DeviceRepository.update_server(device_id, server_data)

                    if device_type == "router":  # router
                        router_data = {
                            "device_id": device_id,
                            "username": data.get("username", "unknown"),
                            "password": data.get("password", ""),
                            "identity": data.get("identity", "unknown"),
                            "os_version": data.get("version") or data.get("os_version", "unknown"),
                            "model": data.get("model") or data.get("model-name"),
                            "serial_number": data.get("serial_number") or data.get("serial-number"),
                            "vendor": data.get("vendor", "MikroTik"),
                            "main_ip_address": data.get("main_ip_address") or data.get("ip"),
                            "main_mac_address": data.get("main_mac_address") or data.get("mac-address"),
                            "main_interface": data.get("main_interface"),
                            "southbound": data.get("southbound", "routeros_api"),
                            "status": "active",
                            "last_seen": to_postgresql_datetime(time.time())
                        }
                        DeviceRepository.update_router(device_id, router_data)

                    elif device_type == "switch":
                        switch_data = {
                            "device_id": device_id,
                            "username": data.get("username", "unknown"),
                            "password": data.get("password", ""),
                            "identity": data.get("identity", "unknown"),
                            "os_version": data.get("os_version", "unknown"),
                            "model": data.get("model", "unknown"),
                            "serial_number": data.get("serial_number", "unknown"),
                            "vendor": data.get("vendor", "Cisco"),
                            "main_ip_address": data.get("main_ip_address") or data.get("ip"),
                            "main_mac_address": data.get("main_mac_address", ""),
                            "main_interface": data.get("main_interface", ""),
                            "southbound": data.get("southbound", "paramiko"),
                            "status": "active",
                            "last_seen": to_postgresql_datetime(time.time())
                        }    
                        DeviceRepository.update_switch(device_id, switch_data)
                        
                    elif device_type == "access_point":  # access point
                        access_point_data = {
                            "device_id": device_id,
                            "username": data.get("username", "unknown"),
                            "password": data.get("password", ""),
                            "identity": data.get("identity", "unknown"),
                            "os_version": data.get("version") or data.get("os_version", "unknown"),
                            "model": data.get("model") or data.get("model-name"),
                            "serial_number": data.get("serial_number") or data.get("serial-number"),
                            "vendor": data.get("vendor", "unknown"),
                            "main_ip_address": data.get("main_ip_address") or data.get("ip"),
                            "main_mac_address": data.get("main_mac_address"),
                            "main_interface": data.get("main_interface", "unknown"),
                            "southbound": data.get("southbound", "unknown"),
                            "status": data.get("status", "active"),
                            "last_seen": to_postgresql_datetime(time.time())
                        }
                        DeviceRepository.update_access_point(device_id, access_point_data)
                    
                    self.core.logger.info(f"Updated existing device in database: {device_id}")
                    
                else: # Jika tidak ada data existing
                    # Insert new device
                    # First insert to network_devices
                    network_id = DeviceRepository.insert_network_device(common_data)
                    
                    # Then insert to specific table
                    if device_type == "server":
                        server_data = {
                            "device_id": device_id,
                            "hostname": str(data.get("hostname", "unknown")),
                            "main_username": str(data.get("main_username", "unknown")),
                            "os_version": str(data.get("os_version", "unknown")),
                            "architecture": str(data.get("architecture", "")),
                            "architecture_bits": str(data.get("architecture_bits", "")),
                            "processor_type": str(data.get("processor_type", "")),
                            "vendor": str(data.get("vendor", "unknown")),
                            "serial_number": str(data.get("serial_number", "unknown")),
                            "main_ip_address": str(data.get("main_ip_address", "")),
                            "main_mac_address": str(data.get("main_mac_address", "unknown")),
                            "main_interface": str(data.get("main_interface", "unknown")),
                            "southbound": str(data.get("southbound", "server_api")),
                            "status": str(data.get("status", "active")),
                            "virtualization": str(data.get("virtualization", "physical")),
                        }
                        server_id = DeviceRepository.insert_server(server_data)

                    elif device_type == "router":  # router
                        router_data = {
                            "device_id": device_id,
                            "username": data.get("username", "unknown"),
                            "password": data.get("password", ""),
                            "identity": data.get("identity", "unknown"),
                            "os_version": data.get("os_version", "unknown"),
                            "model": data.get("model") or data.get("model-name"),
                            "serial_number": data.get("serial_number") or data.get("serial-number"),
                            "vendor": data.get("vendor", "MikroTik"),
                            "main_ip_address": data.get("main_ip_address") or data.get("ip"),
                            "main_mac_address": data.get("main_mac_address") or data.get("mac-address"),
                            "main_interface": data.get("main_interface"),
                            "southbound": data.get("southbound", "routeros_api"),
                            "status": "active",
                        }
                        DeviceRepository.insert_router(router_data)
                    elif device_type == "switch":
                        switch_data = {
                            "device_id": device_id,
                            "username": data.get("username", "unknown"),
                            "password": data.get("password", ""),
                            "identity": data.get("identity", "unknown"),
                            "os_version": data.get("os_version", "unknown"),
                            "model": data.get("model", "unknown"),
                            "serial_number": data.get("serial_number", "unknown"),
                            "vendor": data.get("vendor", "Cisco"),
                            "main_ip_address": data.get("main_ip_address") or data.get("ip"),
                            "main_mac_address": data.get("main_mac_address", ""),
                            "main_interface": data.get("main_interface", ""),
                            "southbound": data.get("southbound", "paramiko"),
                            "status": "active",
                            "last_seen": to_postgresql_datetime(time.time())
                        }    
                        DeviceRepository.insert_switch(switch_data)

                    elif device_type == "access_point":  # access_point
                        access_point_data = {
                            "device_id": device_id,
                            "username": data.get("username", "unknown"),
                            "password": data.get("password", ""),
                            "identity": data.get("identity", "unknown"),
                            "os_version": data.get("os_version", "unknown"),
                            "model": data.get("model") or data.get("model-name"),
                            "serial_number": data.get("serial_number", "unknown") or data.get("serial-number", "unknown"),
                            "vendor": data.get("vendor", "unknown"),
                            "main_ip_address": data.get("main_ip_address") or data.get("ip"),
                            "main_mac_address": data.get("main_mac_address"),
                            "main_interface": data.get("main_interface", "unknown"),
                            "southbound": data.get("southbound", "paramiko"),
                            "status": data.get("status", "active"),
                        }
                        DeviceRepository.insert_access_point(access_point_data)
                    
                    self.core.logger.info(f"Registered new device in database: {device_id}")
                
                db_registered = True
                    
            except Exception as db_error:
                self.core.logger.warning(f"Database registration failed, using memory fallback: {db_error}")
                db_registered = False

            # === MEMORY REGISTRY (FALLBACK/COMPATIBILITY) ===
            memory_registered = False
            try:
                # Initialize memory registry if not exists
                if not hasattr(self.core, 'devices'):
                    class MemoryDeviceRegistry:
                        def __init__(self): self.db = {}
                        def create(self, data): 
                            self.db[data["id"]] = data
                            return data
                        def get(self, did): return self.db.get(did)
                        def list(self): return list(self.db.values())
                    
                    self.core.devices = MemoryDeviceRegistry()
                
                # Save to memory registry
                memory_result = self.core.devices.create(data)
                memory_registered = True
                
                device_type_str = "Server Agent" if is_server else "Mikrotik/Active"
                self.core.logger.info(f"{device_type_str} Device registered in memory: {device_id}")

            except Exception as memory_error:
                self.core.logger.error(f"Memory registration also failed: {memory_error}")
                memory_registered = False

            # === SUCCESS RESPONSE ===
            response_data = {
                "status": "ok",
                "device": { 
                    "device_id": device_id,
                    "device_type": device_type,
                    "southbound": data.get("southbound", "unknown"),
                    "hostname": data.get("identity", data.get("hostname", "unknown")),
                    "main_ip_address": data.get("main_ip_address"),
                    "status": "active"
                },
                "registration_type": registration_mode,
                "database_registered": db_registered,
                "memory_registered": memory_registered
            }

            return self._resp(req, json.dumps(response_data), 200)

        except Exception as e:
            import traceback
            self.core.logger.error(f"Device registration failed: {str(e)}\n{traceback.format_exc()}")
            return self._resp(req, json.dumps({
                "status": "error",
                "error": str(e)
            }), 500)

    def _resp(self, req, body, status=200):
        if isinstance(body, str):
            body = body.encode('utf-8')
        return Response(content_type='application/json', body=body, status=status)

    @route('devices', '/devices', methods=['GET'])
    def list_devices(self, req, **kwargs):
        try:
            # Prioritaskan database dengan error handling
            try:
                db_devices = DeviceRepository.list_all()
                
                # Jika ada devices di database, format sesuai skema
                if db_devices:
                    clean_devices = []
                    for i, dev in enumerate(db_devices, 1):
                        # Base device info dari network_devices
                        # Konversi datetime ke string untuk JSON serialization
                        created_at = dev.get("created_at")
                        updated_at = dev.get("updated_at")
                        last_seen = dev.get("last_seen")
                        
                        if isinstance(created_at, datetime):
                            created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
                        if isinstance(updated_at, datetime):
                            updated_at = updated_at.strftime('%Y-%m-%d %H:%M:%S')
                        if isinstance(last_seen, datetime):
                            last_seen = last_seen.strftime('%Y-%m-%d %H:%M:%S')
                        
                        clean_dev = {
                            "id": i,
                            "device_id": dev.get("device_id"),
                            "device_type": dev.get("device_type", "unknown"),
                            "southbound": dev.get("southbound", "unknown"),
                            "status": dev.get("status", "active"),
                            "created_at": created_at,
                            "updated_at": updated_at,
                            "last_seen": last_seen
                        }
                        
                        # Tambahkan field spesifik berdasarkan device_type
                        if dev.get("device_type") == "server":
                            clean_dev.update({
                                "hostname": dev.get("hostname", "unknown"),
                                "main_username": dev.get("main_username", "unknown"),
                                "os_version": dev.get("os_version", "unknown"),
                                "architecture": dev.get("architecture"),
                                "architecture_bits": dev.get("architecture_bits"),
                                "processor_type": dev.get("processor_type"),
                                "vendor": dev.get("vendor", "unknown"),
                                "serial_number": dev.get("serial_number", "unknown"),
                                "main_ip_address": dev.get("main_ip_address"),
                                "main_mac_address": dev.get("main_mac_address"),
                                "main_interface": dev.get("main_interface"),
                                "virtualization": dev.get("virtualization"),
                            })
                        elif dev.get("device_type") == "router":
                            clean_dev.update({
                                "username": dev.get("username", "unknown"),
                                "identity": dev.get("identity", "unknown"),
                                "os_version": dev.get("os_version", "unknown"),
                                "model": dev.get("model"),
                                "serial_number": dev.get("serial_number"),
                                "vendor": dev.get("vendor", "unknown"),
                                "main_ip_address": dev.get("main_ip_address"),
                                "main_mac_address": dev.get("main_mac_address"),
                                "main_interface": dev.get("main_interface")
                            })
                        elif dev.get("device_type") == "switch":
                            clean_dev.update({
                                "username": dev.get("username", "unknown"),
                                "identity": dev.get("identity", "unknown"),
                                "os_version": dev.get("os_version", "unknown"),
                                "model": dev.get("model", "unknown"),
                                "serial_number": dev.get("serial_number"),
                                "vendor": dev.get("vendor", "Cisco"),
                                "main_ip_address": dev.get("main_ip_address"),
                                "main_mac_address": dev.get("main_mac_address"),
                                "main_interface": dev.get("main_interface")
                            })
                        
                        elif dev.get("device_type") == "access_point":
                            clean_dev.update({
                                "username": dev.get("username", "unknown"),
                                "identity": dev.get("identity", "unknown"),
                                "os_version": dev.get("os_version", "unknown"),
                                "model": dev.get("model"),
                                "serial_number": dev.get("serial_number"),
                                "vendor": dev.get("vendor", "unknown"),
                                "main_ip_address": dev.get("main_ip_address"),
                                "main_mac_address": dev.get("main_mac_address"),
                                "main_interface": dev.get("main_interface", "unknown")
                            })
                        
                        clean_devices.append(clean_dev)
                    
                    self.core.logger.info(f"Listed {len(clean_devices)} devices from database")
                    return self._resp(req, json.dumps(clean_devices))
                    
            except Exception as db_error:
                self.core.logger.warning(f"Database access failed: {db_error}. Using memory registry.")
            
            # Fallback ke memory registry
            if hasattr(self.core, 'devices'):
                memory_devices = self.core.devices.list()
                clean_devices = []
                for i, dev in enumerate(memory_devices, 1):
                    # Convert memory format ke database format
                    southbound = dev.get("southbound", "")
                    vendor = (dev.get("vendor") or "").lower()
                    # default
                    device_type = "unknown"

                    if southbound == "server_api":
                        device_type = "server"

                    elif southbound in ["router_api", "routeros", "router"]:
                        device_type = "router"

                    elif southbound in ["paramiko", "ssh"]:
                        if vendor in ["ubiquiti", "unifi"]:
                            device_type = "access_point"
                        elif vendor in ["mikrotik", "cisco", "aruba", "juniper", "hp"]:
                            device_type = "switch"
                        else:
                            device_type = "unknown"

                    elif southbound in ["unifi_switch", "switch"]:
                        device_type = "switch"
                    
                    # Konversi datetime untuk memory registry
                    last_seen = dev.get("last_seen")
                    if isinstance(last_seen, (int, float)):
                        last_seen = datetime.fromtimestamp(last_seen).strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(last_seen, datetime):
                        last_seen = last_seen.strftime('%Y-%m-%d %H:%M:%S')
                    
                    clean_dev = {
                        "id": i,
                        "device_id": dev.get("id"),
                        "device_type": device_type,
                        "southbound": dev.get("southbound", "unknown"),
                        "status": dev.get("status", "active"),
                        "last_seen": last_seen
                    }
                    
                    if device_type == "server":
                        clean_dev.update({
                            "hostname": dev.get("hostname", "unknown"),
                            "main_username": dev.get("main_username", "unknown"),
                            "os_version": dev.get("os", "unknown"),
                            "architecture": dev.get("architecture"),
                            "architecture_bits": dev.get("architecture_bits"),
                            "processor_type": dev.get("processor_type"),
                            "vendor": dev.get("vendor", "unknown"),
                            "serial_number": dev.get("serial_number", "unknown"),
                            "main_ip_address": dev.get("main_ip_address"),
                            "main_mac_address": dev.get("main_mac_address"),
                            "main_interface": dev.get("main_interface"),
                            "virtualization": dev.get("virtualization"),
                        })

                    elif device_type == "router":  # router
                        clean_dev.update({
                            "username": dev.get("username", "unknown"),
                            "identity": dev.get("identity", dev.get("hostname", "unknown")),
                            "os_version": dev.get("version", "unknown"),
                            "model": dev.get("model"),
                            "serial_number": dev.get("serial-number"),
                            "vendor": dev.get("vendor", "unknown"),
                            "main_ip_address": dev.get("ip"),
                            "main_mac_address": dev.get("mac-address"),
                            "main_interface": dev.get("main_interface")
                        })
                    elif device_type == "switch":
                        clean_dev.update({
                            "username": dev.get("username", "unknown"),
                            "identity": dev.get("identity", dev.get("hostname", "unknown")),
                            "os_version": dev.get("os_version", dev.get("version", "unknown")),
                            "model": dev.get("model", "unknown"),
                            "serial_number": dev.get("serial_number"),
                            "vendor": dev.get("vendor", "Cisco"),
                            "main_ip_address": dev.get("ip"),
                            "main_mac_address": dev.get("mac_address", ""),
                            "main_interface": dev.get("main_interface", "")
                        })
                    
                    elif device_type == "access_point":  # access_point
                        clean_dev.update({
                            "username": dev.get("username", "unknown"),
                            "identity": dev.get("identity", dev.get("hostname", "unknown")),
                            "os_version": dev.get("version", "unknown"),
                            "model": dev.get("model"),
                            "serial_number": dev.get("serial-number"),
                            "vendor": dev.get("vendor", "unknown"),
                            "main_ip_address": dev.get("ip"),
                            "main_mac_address": dev.get("mac-address"),
                            "main_interface": dev.get("main_interface", "unknown")
                        })
                    else:
                        clean_dev.update({
                            "username": dev.get("username", "unknown"),
                            "identity": dev.get("identity", dev.get("hostname", "unknown")),
                            "os_version": dev.get("version", "unknown"),
                            "model": dev.get("model"),
                            "serial_number": dev.get("serial-number"),
                            "vendor": dev.get("vendor", "Mikrotik"),
                            "main_ip_address": dev.get("ip"),
                            "main_mac_address": dev.get("mac-address"),
                            "main_interface": dev.get("main_interface")
                        })

                    clean_devices.append(clean_dev)
                
                self.core.logger.info(f"Listed {len(clean_devices)} devices from memory registry")
                return self._resp(req, json.dumps(clean_devices))
            
            # No devices found
            return self._resp(req, json.dumps([]))
            
        except Exception as e:
            self.core.logger.error(f"Error listing devices: {e}")
            return self._resp(req, json.dumps({"error": str(e)}), 500)
    
    # Panggil device berdasarkan ID
    @route('devices', '/devices/{device_id}', methods=['GET'])
    def get_device(self, req, device_id, **kwargs):
        """Get specific device by ID from database"""
        try:
            # 1. Coba ambil dari database dulu
            try:
                db_device = DeviceRepository.find_by_device_id(device_id)
                if db_device:
                    # Konversi datetime ke string untuk JSON serialization
                    created_at = db_device.get("created_at")
                    updated_at = db_device.get("updated_at")
                    last_seen = db_device.get("last_seen")
                    
                    if isinstance(created_at, datetime):
                        created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
                    if isinstance(updated_at, datetime):
                        updated_at = updated_at.strftime('%Y-%m-%d %H:%M:%S')
                    if isinstance(last_seen, datetime):
                        last_seen = last_seen.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Build response berdasarkan device_type
                    device_type = db_device.get("device_type", "unknown")
                    clean_dev = {
                        "id": device_id,
                        "device_id": db_device.get("device_id"),
                        "device_type": device_type,
                        "southbound": db_device.get("southbound", "unknown"),
                        "status": db_device.get("status", "active"),
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "last_seen": last_seen
                    }
                    
                    # Tambahkan field spesifik berdasarkan device_type
                    if device_type == "server":
                        clean_dev.update({
                            "hostname": db_device.get("hostname", "unknown"),
                            "main_username": db_device.get("main_username", "unknown"),
                            "os_version": db_device.get("os_version", "unknown"),
                            "architecture": db_device.get("architecture"),
                            "architecture_bits": db_device.get("architecture_bits"),
                            "processor_type": db_device.get("processor_type"),
                            "vendor": db_device.get("vendor", "unknown"),
                            "serial_number": db_device.get("serial_number", "unknown"),
                            "main_ip_address": db_device.get("main_ip_address"),
                            "main_mac_address": db_device.get("main_mac_address"),
                            "main_interface": db_device.get("main_interface"),
                            "virtualization": db_device.get("virtualization"),
                        })
                    elif device_type == "router":
                        clean_dev.update({
                            "username": db_device.get("username", "unknown"),
                            "identity": db_device.get("identity", "unknown"),
                            "os_version": db_device.get("os_version", "unknown"),
                            "model": db_device.get("model"),
                            "serial_number": db_device.get("serial_number"),
                            "vendor": db_device.get("vendor", "unknown"),
                            "main_ip_address": db_device.get("main_ip_address"),
                            "main_mac_address": db_device.get("main_mac_address"),
                            "main_interface": db_device.get("main_interface")
                        })
                    elif device_type == "switch":
                        clean_dev.update({
                            "username": db_device.get("username", "unknown"),
                            "identity": db_device.get("identity", "unknown"),
                            "os_version": db_device.get("os_version", "unknown"),
                            "model": db_device.get("model", "unknown"),
                            "serial_number": db_device.get("serial_number"),
                            "vendor": db_device.get("vendor", "Cisco"),
                            "main_ip_address": db_device.get("main_ip_address"),
                            "main_mac_address": db_device.get("main_mac_address"),
                            "main_interface": db_device.get("main_interface")
                        })
                    elif device_type == "access_point":
                        clean_dev.update({
                            "username": db_device.get("username", "unknown"),
                            "identity": db_device.get("identity", "unknown"),
                            "os_version": db_device.get("os_version", "unknown"),
                            "model": db_device.get("model", "unknown"),
                            "serial_number": db_device.get("serial_number"),
                            "vendor": db_device.get("vendor", "unknown"),
                            "main_ip_address": db_device.get("main_ip_address"),
                            "main_mac_address": db_device.get("main_mac_address"),
                            "main_interface": db_device.get("main_interface")
                        })
                    return self._resp(req, json.dumps(clean_dev))
                    
            except Exception as db_error:
                self.core.logger.warning(f"Database lookup failed: {db_error}")
            
            # 2. Fallback ke memory registry
            try:
                device = self.core.devices.get(device_id)
                if device:
                    # Convert memory format ke database format
                    southbound = device.get("southbound", "")
                    if southbound == "server_api":
                        device_type = "server"
                    elif southbound == "routeros_api":
                        device_type = "router"
                    elif southbound == "paramiko":
                        device_type = "switch"
                    else:
                        device_type = "unknown"
                    
                    # Konversi datetime untuk memory registry
                    last_seen = device.get("last_seen")
                    if isinstance(last_seen, (int, float)):
                        last_seen = datetime.fromtimestamp(last_seen).strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(last_seen, datetime):
                        last_seen = last_seen.strftime('%Y-%m-%d %H:%M:%S')
                    
                    clean_dev = {
                        "id": device.get("id"),
                        "device_id": device.get("id"),
                        "device_type": device_type,
                        "southbound": device.get("southbound", "unknown"),
                        "status": device.get("status", "active"),
                        "last_seen": last_seen
                    }
                    
                    if device_type == "server":
                        clean_dev.update({
                            "hostname": device.get("hostname", "unknown"),
                            "main_username": device.get("main_username", "unknown"),
                            "os_version": device.get("os", "unknown"),
                            "architecture": device.get("architecture"),
                            "architecture_bits": device.get("architecture_bits"),
                            "processor_type": device.get("processor_type"),
                            "vendor": device.get("vendor", "unknown"),
                            "serial_number": device.get("serial_number", "unknown"),
                            "main_ip_address": device.get("main_ip_address"),
                            "main_mac_address": device.get("main_mac_address"),
                            "main_interface": device.get("main_interface"),
                            "virtualization": device.get("virtualization"),
                        })
                    elif device_type == "router":  # router
                        clean_dev.update({
                            "username": device.get("username", "unknown"),
                            "identity": device.get("identity", device.get("hostname", "unknown")),
                            "os_version": device.get("version", "unknown"),
                            "model": device.get("model"),
                            "serial_number": device.get("serial-number"),
                            "vendor": device.get("vendor", "unknown"),
                            "main_ip_address": device.get("ip"),
                            "main_mac_address": device.get("mac-address"),
                            "main_interface": device.get("main_interface")
                        })
                    elif device_type == "switch":
                        clean_dev.update({
                            "username": device.get("username", "unknown"),
                            "identity": device.get("identity", device.get("hostname", "unknown")),
                            "os_version": device.get("os_version", device.get("version", "unknown")),
                            "model": device.get("model", "unknown"),
                            "serial_number": device.get("serial_number"),
                            "vendor": device.get("vendor", "Cisco"),
                            "main_ip_address": device.get("ip"),
                            "main_mac_address": device.get("mac_address", ""),
                            "main_interface": device.get("main_interface", "")
                        })
                    elif device_type == "access_point":  # access_point
                        clean_dev.update({
                            "username": device.get("username", "unknown"),
                            "identity": device.get("identity", device.get("hostname", "unknown")),
                            "os_version": device.get("version", "unknown"),
                            "model": device.get("model"),
                            "serial_number": device.get("serial-number"),
                            "vendor": device.get("vendor", "unknown"),
                            "main_ip_address": device.get("ip"),
                            "main_mac_address": device.get("mac-address"),
                            "main_interface": device.get("main_interface", "unknown")
                        })
                    return self._resp(req, json.dumps(clean_dev))
                    
            except KeyError:
                pass  # Device not found in memory registry either
            
            # 3. Device not found
            return self._resp(req, json.dumps({"error": "Device not found"}), 404)
            
        except Exception as e:
            self.core.logger.error(f"Error getting device {device_id}: {e}")
            return self._resp(req, json.dumps({"error": str(e)}), 500)
    
    @route('devices', '/devices/{did}/heartbeat', methods=['POST'])
    def heartbeat(self, req, did, **kwargs):
        if not _check_api_key(req):
            return self._resp(req, json.dumps({"status":"error","error":"unauthorized"}), status=401)
        
        try:
            # Update di database
            DeviceRepository.update_device_status(
                did, 
                'active',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            # Update di memory registry (fallback)
            try:
                dev = self.core.devices.get(did)
                dev['last_seen'] = time.time()
                dev['connected'] = True
            except:
                pass  # Skip jika tidak ada di memory
            
            self.core.logger.info(f"Heartbeat received from {did}")
            
            return self._resp(req, json.dumps({
                "status": "ok", 
                "device": did,
                "timestamp": datetime.now().isoformat()
            }))
            
        except Exception as e:
            self.core.logger.error(f"Heartbeat error for {did}: {e}")
            return self._resp(req, json.dumps({"status":"error","error":str(e)}), 500)