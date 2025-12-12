import os, sys 
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

from ryu.base import app_manager
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from ryu.lib import hub
from webob import Response
import json, uuid, time
from datetime import datetime
import socket

# === Database Integration ===
from database.device_repository import DeviceRepository

# === SNMP Driver ===
from drivers.snmp_file_manager import SNMPFileManager

# === Router Driver ===
from drivers.router_drivers.mikrotik.routeros_api import RouterOSApiDriver
from actions.routers.mikrotik import MikrotikRouterActions

# === Switch Driver ===
# from drivers.switch_drivers.netconf import NetconfApiDriver
# from actions.switch.cisco import CiscoSwitchActions
# from actions.switch.mikrotik import MikrotikSwitchActions

# === Access-Point Driver ===
# from actions.access_point.tplink import TPLinkAccessPointActions

# === Server Driver ===
from drivers.server_drivers.server_api import ServerAPI
from actions.servers.server import ServerActions
from drivers.server_file_manager import ServerFileManager

# === Wazuh Driver ===
from drivers.wazuh_drivers.wazuh_api import WazuhAPI

API_INSTANCE_NAME = 'northbound_api'

# Ini sesuaikan dengan secret key nya (Untuk Server Agent)
ALLOWED_API_KEYS = set([os.environ.get("RYU_API_KEY", "agent-secret-token-1")])

def to_mysql_datetime(ts):
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

        # Inisialisasi server metrics manager
        self.server_file_manager = ServerFileManager()
        # Start auto-sync thread (setiap 30 detik)
        self.sync_thread = hub.spawn(self.auto_sync_servers)

        # Initialize Wazuh integration
        try:
            wazuh_api_url = os.getenv('WAZUH_API_URL')
            wazuh_user = os.getenv('WAZUH_USER') 
            wazuh_password = os.getenv('WAZUH_PASSWORD')
            
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

    def detect_vendor(self, dev):
        # == Deteksi otomatis tipe perangkat ==

        # (Mikrotik, RouterOS API)
        try:
            driver = RouterOSApiDriver(dev)
            info = driver.get_device_info()
            info["southbound"] = "routeros_api"
            info["vendor"] = "MikroTik"
            info["connected"] = True
            return info
        except Exception:
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

        # WAZUH MANAGER ACTIONS (GLOBAL - TIDAK BUTUH device_id)
        wazuh_global_actions = [
            "wazuh.manager.info", "wazuh.manager.stats", "wazuh.manager.configuration",
            "wazuh.agent.list", "wazuh.agent.detail", "wazuh.agent.status", "wazuh.agent.config",
            "wazuh.security.sca", "wazuh.security.fim", "wazuh.security.threat_hunting",
            "wazuh.logs.discover", "wazuh.system.hardware", "wazuh.system.processes",
            "wazuh.config.assessment"
        ]
        
        # SNMP ACTIONS (GLOBAL - TIDAK BUTUH device_id)
        snmp_global_actions = [
            "snmp.device.add", "snmp.metric.add", "snmp.test.oid",
            "snmp.metric.delete", "snmp.metric.edit", "snmp.device.delete", 
            "snmp.device.edit"
        ]
        
        # GLOBAL ACTIONS = WAJUH MANAGER + SNMP
        global_actions = wazuh_global_actions + snmp_global_actions
        
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
                    "board": dev_row.get("board", ""),
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
        sb = dev.get("southbound", "")
        if sb == "routeros_api":
            return RouterOSApiDriver(dev)
        elif sb == "server_api":
            return ServerAPI(dev)
        else:
            raise ValueError(f"Unknown southbound driver: {sb}")

    def dispatch(self, d, action, params, jid):
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
            "wazuh.agent.list": lambda p, logger: self.wazuh_api.get_agents(
                filters=p.get("filters", {}),
                logger=logger
            ),
            "wazuh.agent.detail": lambda p, logger: self.wazuh_api.get_agent_detail(
                agent_id=p.get("agent_id"),
                logger=logger
            ),
            "wazuh.agent.status": lambda p, logger: self.wazuh_api.get_agent_status(
                agent_id=p.get("agent_id"),
                logger=logger
            ),
            "wazuh.agent.config": lambda p, logger: self.wazuh_api.get_agent_config(
                agent_id=p.get("agent_id"),
                logger=logger
            ),
            "wazuh.security.sca": lambda p, logger: self.wazuh_api.get_security_configuration_assessment(
                agent_id=p.get("agent_id"),
                logger=logger
            ),
            "wazuh.security.fim": lambda p, logger: self.wazuh_api.get_fim_data(
                agent_id=p.get("agent_id"),
                filters=p.get("filters", {}),
                logger=logger
            ),
            "wazuh.security.threat_hunting": lambda p, logger: self.wazuh_api.get_threat_hunting(
                query=p.get("query", {}),
                logger=logger
            ),
            "wazuh.logs.discover": lambda p, logger: self.wazuh_api.get_logs(
                agent_id=p.get("agent_id"),
                query=p.get("query", {}),
                logger=logger
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
        }

        # Device-based actions
        device_actions = {}
        
        if d is not None:
            # Deteksi tipe driver
            driver_type = "unknown"
            if hasattr(d, '__class__'):
                if 'RouterOS' in d.__class__.__name__:
                    driver_type = "mikrotik"
                    device_actions = MikrotikRouterActions.get_actions(d)
                elif 'ServerAPI' in d.__class__.__name__:
                    driver_type = "server"
                    wazuh_api = self.wazuh_api if hasattr(self, 'wazuh_api') and self.wazuh_api is not None else None
                    device_actions = ServerActions.get_actions(d, self.wazuh_api)

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
            
            # === GENERATE CONSISTENT DEVICE ID ===
            def generate_device_id(device_data, registration_mode):
                import hashlib
                
                if registration_mode == "server_agent":
                    ip = device_data.get('main_ip_address', device_data.get('ip', 'unknown'))
                    hostname = device_data.get('hostname', 'unknown')
                    device_type = "server"
                else:  # active_discovery
                    ip = device_data.get('ip', 'unknown')
                    hostname = device_data.get('hostname', 'unknown')
                    device_type = "router"
                
                unique_components = [device_type, ip, hostname, registration_mode]
                unique_str = "_".join(str(c) for c in unique_components)
                hash_digest = hashlib.sha256(unique_str.encode()).hexdigest()[:10]
                
                return f"dev_{hash_digest}"

            device_type = "server" if is_server else "router"
            registration_mode = "server_agent" if is_server else "active_discovery"
            
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
                
                # Generate device ID
                device_id = generate_device_id(data, registration_mode)
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
                    "connected": True,
                    "main_ip_address": str(data.get("main_ip_address", "")),
                    "main_interface": str(data.get("main_interface", "unknown")),
                    "main_mac_address": str(data.get("main_mac_address", "unknown")),
                    "last_seen": to_mysql_datetime(time.time())
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

                # Handle interfaces data (outside meta)
                if "interfaces" in data:
                    # Pastikan interfaces adalah dict
                    if isinstance(data["interfaces"], dict):
                        data["_interfaces_data"] = data["interfaces"]
                    else:
                        data["_interfaces_data"] = {}
                    # Hapus dari data utama agar tidak tercampur
                    del data["interfaces"]
                
                # Handle firewall data (outside meta)
                if "firewall" in data:
                    # Pastikan firewall adalah dict
                    if isinstance(data["firewall"], dict):
                        data["_firewall_data"] = data["firewall"]
                    else:
                        data["_firewall_data"] = {}
                    # Hapus dari data utama agar tidak tercampur
                    del data["firewall"]

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
                
                # Map MikroTik specific fields
                data.update({
                    "status": "active",
                    "southbound": "routeros_api",
                    "vendor": "MikroTik",
                    "identity": info.get("identity"),
                    "username": data.get("username", "admin"),
                    "os_version": info.get("version"),
                    "board": info.get("board-name"),
                    "serial_number": info.get("serial-number"),
                    "main_ip_address": data.get("ip"),
                    "main_mac_address": info.get("mac-address"),
                    "main_interface": info.get("main_interface"),
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
                    "last_seen": to_mysql_datetime(time.time())
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
                            "main_ip_address": data.get("main_ip_address"),
                            "main_mac_address": data.get("main_mac_address"),
                            "main_interface": data.get("main_interface"),
                            "southbound": data.get("southbound", "unknown"),
                            "status": "active",
                            "virtualization": data.get("virtualization"),
                            "last_seen": to_mysql_datetime(time.time())
                        }
                        DeviceRepository.update_server(device_id, server_data)
                        server_id = DeviceRepository.get_server_id(device_id)

                        # INSERT/UPDATE INTERFACES DATA (jika ada)
                        if "_interfaces_data" in data:
                            try:
                                if server_id:
                                    # Delete existing interfaces first
                                    DeviceRepository.delete_server_interfaces(device_id)
                                    
                                    # Insert new interfaces
                                    for iface_name, iface_data in data["_interfaces_data"].items():
                                        # Skip loopback dan docker/bridge interfaces
                                        if iface_name.startswith(('lo', 'docker', 'br-', 'virbr')):
                                            continue
                                        
                                        # Ambil data IPv4 pertama (jika ada)
                                        ipv4_data = {}
                                        ipv4_list = iface_data.get("ipv4", [])
                                        if isinstance(ipv4_list, list) and len(ipv4_list) > 0:
                                            ipv4_data = ipv4_list[0]  # Ambil IP pertama
                                        
                                        # Insert interface dengan data IP
                                        interface_id = DeviceRepository.insert_server_interface({
                                            "server_id": server_id,  
                                            "interface_name": str(iface_name),
                                            "mac_address": str(iface_data.get("mac_address", "unknown")),
                                            "ip_address": str(ipv4_data.get("address", "")),
                                            "ip_netmask": str(ipv4_data.get("netmask", "")),
                                            "ip_broadcast": str(ipv4_data.get("broadcast", "")),
                                            "ip_version": "ipv4"
                                        })
                            except Exception as e:
                                self.core.logger.warning(f"Failed to save interfaces: {e}")
                        
                        # INSERT/UPDATE FIREWALL DATA (jika ada)
                        if "_firewall_data" in data:
                            try:
                                firewall_data = data["_firewall_data"]
                                DeviceRepository.upsert_server_firewall({
                                    "server_id": server_id,
                                    "firewall_type": firewall_data.get("firewall_type"),
                                    "status": firewall_data.get("status"),
                                    "default_zone": firewall_data.get("default_zone"),
                                    "active_zones": json.dumps(firewall_data.get("active_zones", [])),
                                    "rules_count": firewall_data.get("rules_count", 0),
                                    "last_checked": firewall_data.get("last_checked")
                                })
                            except Exception as e:
                                self.core.logger.warning(f"Failed to save firewall: {e}")

                    else:  # router
                        router_data = {
                            "device_id": device_id,
                            "username": data.get("username", "unknown"),
                            "password": data.get("password", ""),
                            "identity": data.get("identity", "unknown"),
                            "os_version": data.get("version") or data.get("os_version", "unknown"),
                            "board": data.get("board") or data.get("board-name"),
                            "serial_number": data.get("serial_number") or data.get("serial-number"),
                            "vendor": data.get("vendor", "MikroTik"),
                            "main_ip_address": data.get("main_ip_address") or data.get("ip"),
                            "main_mac_address": data.get("main_mac_address") or data.get("mac-address"),
                            "main_interface": data.get("main_interface"),
                            "southbound": data.get("southbound", "routeros_api"),
                            "status": "active",
                            "last_seen": to_mysql_datetime(time.time())
                        }
                        DeviceRepository.update_router(device_id, router_data)
                    
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
                            "main_ip_address": str(data.get("main_ip_address", "")),
                            "main_mac_address": str(data.get("main_mac_address", "unknown")),
                            "main_interface": str(data.get("main_interface", "unknown")),
                            "southbound": str(data.get("southbound", "server_api")),
                            "status": str(data.get("status", "active")),
                            "virtualization": str(data.get("virtualization", "physical")),
                        }
                        server_id = DeviceRepository.insert_server(server_data)
                        try:
                            # Insert new interfaces
                            for iface_name, iface_data in data["_interfaces_data"].items():
                                # Skip loopback dan docker/bridge interfaces jika mau
                                if iface_name.startswith(('lo', 'docker', 'br-', 'virbr')):
                                    continue
                                    
                                # Ambil data IPv4 pertama (jika ada)
                                ipv4_data = {}
                                ipv4_list = iface_data.get("ipv4", [])
                                if isinstance(ipv4_list, list) and len(ipv4_list) > 0:
                                    ipv4_data = ipv4_list[0]  # Ambil IP pertama
                                
                                # Insert interface dengan semua data sekaligus
                                interface_id = DeviceRepository.insert_server_interface({
                                    "server_id": server_id,
                                    "interface_name": str(iface_name),
                                    "mac_address": str(iface_data.get("mac_address", "unknown")),
                                    "ip_address": str(ipv4_data.get("address", "")),
                                    "ip_netmask": str(ipv4_data.get("netmask", "")),
                                    "ip_broadcast": str(ipv4_data.get("broadcast", "")),
                                    "ip_version": "ipv4"
                                }) 
                        except Exception as e:
                            self.core.logger.warning(f"Failed to save interfaces: {e}")
                        
                        # INSERT FIREWALL DATA (jika ada)
                        if "_firewall_data" in data:
                            try:
                                firewall_data = data["_firewall_data"]
                                DeviceRepository.upsert_server_firewall({
                                    "server_id": server_id,
                                    "firewall_type": str(firewall_data.get("firewall_type")),
                                    "status": str(firewall_data.get("status")),
                                    "default_zone": str(firewall_data.get("default_zone")),
                                    "active_zones": json.dumps(firewall_data.get("active_zones", [])),
                                    "rules_count": str(firewall_data.get("rules_count", 0)),
                                    "last_checked": str(firewall_data.get("last_checked"))
                                })
                            except Exception as e:
                                self.core.logger.warning(f"Failed to save firewall: {e}")

                    else:  # router
                        router_data = {
                            "device_id": device_id,
                            "username": data.get("username", "unknown"),
                            "password": data.get("password", ""),
                            "identity": data.get("identity", "unknown"),
                            "os_version": data.get("os_version", "unknown"),
                            "board": data.get("board") or data.get("board-name"),
                            "serial_number": data.get("serial_number") or data.get("serial-number"),
                            "vendor": data.get("vendor", "MikroTik"),
                            "main_ip_address": data.get("main_ip_address") or data.get("ip"),
                            "main_mac_address": data.get("main_mac_address") or data.get("mac-address"),
                            "main_interface": data.get("main_interface"),
                            "southbound": data.get("southbound", "routeros_api"),
                            "status": "active",
                        }
                        DeviceRepository.insert_router(router_data)
                    
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
                                "main_ip_address": dev.get("main_ip_address"),
                                "main_mac_address": dev.get("main_mac_address"),
                                "main_interface": dev.get("main_interface"),
                                "virtualization": dev.get("virtualization"),
                            })
                            # FETCH INTERFACES DARI TABEL TERPISAH
                            try:
                                interfaces = DeviceRepository.get_server_interfaces(dev.get("device_id"))
                                if interfaces:
                                    # Format interfaces
                                    formatted_interfaces = []
                                    for iface in interfaces:
                                        iface_created = iface.get("created_at")
                                        iface_updated = iface.get("updated_at")
                                        
                                        if isinstance(iface_created, datetime):
                                            iface_created = iface_created.strftime('%Y-%m-%d %H:%M:%S')
                                        if isinstance(iface_updated, datetime):
                                            iface_updated = iface_updated.strftime('%Y-%m-%d %H:%M:%S')
                                        
                                        formatted_iface = {
                                            "interface_name": iface.get("interface_name"),
                                            "mac_address": iface.get("mac_address"),
                                            "ip_address": iface.get("ip_address"),
                                            "ip_netmask": iface.get("ip_netmask"),
                                            "ip_broadcast": iface.get("ip_broadcast"),
                                            "ip_version": iface.get("ip_version"),
                                            "created_at": iface_created,
                                            "updated_at": iface_updated
                                        }
                                        formatted_interfaces.append(formatted_iface)
                                    
                                    clean_dev["interfaces"] = formatted_interfaces
                                else:
                                    clean_dev["interfaces"] = []
                            except Exception as e:
                                self.core.logger.warning(f"Failed to fetch interfaces for {dev.get('device_id')}: {e}")
                                clean_dev["interfaces"] = []
                            
                            # FETCH FIREWALL DARI TABEL TERPISAH
                            try:
                                firewall = DeviceRepository.get_server_firewall(dev.get("device_id"))
                                if firewall:
                                    # Konversi datetime untuk firewall
                                    firewall_created = firewall.get("created_at")
                                    firewall_updated = firewall.get("updated_at")
                                    firewall_last_checked = firewall.get("last_checked")
                                    
                                    if isinstance(firewall_created, datetime):
                                        firewall_created = firewall_created.strftime('%Y-%m-%d %H:%M:%S')
                                    if isinstance(firewall_updated, datetime):
                                        firewall_updated = firewall_updated.strftime('%Y-%m-%d %H:%M:%S')
                                    if isinstance(firewall_last_checked, datetime):
                                        firewall_last_checked = firewall_last_checked.strftime('%Y-%m-%d %H:%M:%S')
                                    
                                    clean_dev["firewall"] = {
                                        "firewall_type": firewall.get("firewall_type"),
                                        "status": firewall.get("status"),
                                        "default_zone": firewall.get("default_zone"),
                                        "active_zones": json.loads(firewall.get("active_zones", "[]")),
                                        "rules_count": firewall.get("rules_count", 0),
                                        "last_checked": firewall_last_checked,
                                        "created_at": firewall_created,
                                        "updated_at": firewall_updated
                                    }
                                else:
                                    clean_dev["firewall"] = None
                            except Exception as e:
                                self.core.logger.warning(f"Failed to fetch firewall for {dev.get('device_id')}: {e}")
                                clean_dev["firewall"] = None

                        elif dev.get("device_type") == "router":
                            clean_dev.update({
                                "username": dev.get("username", "unknown"),
                                "identity": dev.get("identity", "unknown"),
                                "os_version": dev.get("os_version", "unknown"),
                                "board": dev.get("board"),
                                "serial_number": dev.get("serial_number"),
                                "vendor": dev.get("vendor", "unknown"),
                                "main_ip_address": dev.get("main_ip_address"),
                                "main_mac_address": dev.get("main_mac_address"),
                                "main_interface": dev.get("main_interface")
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
                    device_type = "server" if dev.get("southbound") == "server_api" else "router"
                    
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
                            "main_ip_address": dev.get("main_ip_address"),
                            "main_mac_address": dev.get("main_mac_address"),
                            "main_interface": dev.get("main_interface"),
                            "virtualization": dev.get("virtualization"),
                            "interfaces": dev.get("_interfaces_data", {}),
                            "firewall": dev.get("_firewall_data")
                        })
                    else:  # router
                        clean_dev.update({
                            "username": dev.get("username", "unknown"),
                            "identity": dev.get("identity", dev.get("hostname", "unknown")),
                            "os_version": dev.get("version", "unknown"),
                            "board": dev.get("board"),
                            "serial_number": dev.get("serial-number"),
                            "vendor": dev.get("vendor", "unknown"),
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
        # Get specific device by ID
        try:
            device = self.core.devices.get(device_id)
            body = json.dumps(device)
        except KeyError:
            body = json.dumps({"error": "Device not found"})
        
        return self._resp(req, body)
    
    @route('devices', '/devices/{did}/heartbeat', methods=['POST'])
    def heartbeat(self, req, did, **kwargs):
        if not _check_api_key(req):
            return self._resp(req, json.dumps({"status":"error","error":"unauthorized"}), status=401)

        dev = None  # Inisialisasi explicit
        dev_ip = None  # Simpan IP terpisah

        # update in-memory registry
        try:
            dev = self.core.devices.get(did)
            dev['last_seen'] = time.time()
            dev['connected'] = True
            dev_ip = dev.get("ip")  # Simpan IP sebelum mungkin exception
            self.core.logger.info(f"Heartbeat from {did} (IP: {dev_ip})")
        except Exception as e:
            self.core.logger.warning(f"Heartbeat: Device {did} not in registry: {e}")

        return self._resp(req, json.dumps({"status":"ok", "device": did}))