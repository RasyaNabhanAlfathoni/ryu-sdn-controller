import os, sys # cukurukuk
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

from ryu.base import app_manager
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from ryu.lib import hub
from webob import Response
import json, uuid, time, datetime
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

# === Wazuh Driver ===
from drivers.wazuh_drivers.wazuh_api import WazuhAPI

API_INSTANCE_NAME = 'northbound_api'

# Ini sesuaikan dengan secret key nya (Untuk Server Agent)
ALLOWED_API_KEYS = set([os.environ.get("RYU_API_KEY", "agent-secret-token-1")])

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

        # GLOBAL ACTION (SNMP & Wazuh Manager)
        if action in ["snmp.device.add", "snmp.metric.add", "snmp.test.oid"]:
            return self.dispatch(None, action, params, jid)
        
        # DEVICE-BASED ACTION
        device_id = p.get("device_id")
        if not device_id:
            raise ValueError("device_id is required")

        # Cari device - prioritaskan memory registry dulu (karena device ada di memory)
        dev_config = None
    
        # Method 1: Database lookup (fallback)
        if not dev_config:
            try:
                dev_row = DeviceRepository.find_by_device_id(device_id)
                if dev_row:
                    self.jobs.append_log(jid, f"Found in database: {dev_row.get('device_type')}")
                    dev_config = {
                        "id": dev_row["device_id"],
                        "device_id": dev_row["device_id"],
                        "ip": dev_row.get("main_ip_address"),
                        "main_ip_address": dev_row.get("main_ip_address"),
                        "username": dev_row.get("username") or dev_row.get("main_username", "unknown"),
                        "password": dev_row.get("password", ""),
                        "vendor": dev_row.get("vendor", "unknown"),
                        "device_type": dev_row.get("device_type", "unknown"),
                        "southbound": dev_row.get("southbound", "unknown"),
                        "hostname": dev_row.get("hostname", "unknown")
                    }
            except Exception as e:
                self.jobs.append_log(jid, f"Database lookup failed: {e}")

        # Method 2: Memory registry lookup (prioritas utama)
        if hasattr(self, 'devices'):
            memory_dev = self.devices.get(device_id)
            if memory_dev:
                self.jobs.append_log(jid, "Found device in memory registry")
                dev_config = memory_dev

        if not dev_config:
            self.jobs.append_log(jid, f"ERROR: Device {device_id} not found in any registry")
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
            # SNMP Actions
            "snmp.device.add": lambda p, logger: SNMPFileManager().add_device(p["module"], p),
            "snmp.metric.add": lambda p, logger: SNMPFileManager().add_metric(p["module"], p),
            "snmp.test.oid": lambda p, logger: SNMPFileManager().test_snmp(
                ip=p["ip"],
                community=p.get("community", "public"),
                oid=p["oid"],
                version=p.get("version")
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
                
                data["ip"] = final_ip
                data["main_ip_address"] = final_ip
                
                # Generate device ID
                device_id = generate_device_id(data, registration_mode)
                data["id"] = device_id
                data["device_id"] = device_id
                
                # Data langsung dari payload (bukan dari meta)
                server_data = {
                    "hostname": data.get("identity", data.get("hostname", "unknown")),
                    "main_ip_address": data.get("main_ip_address"),
                    "main_interface": data.get("main_interface", "unknown"),
                    "main_mac_address": data.get("main_mac_address", "unknown"),
                    "southbound": data.get("southbound", "server_api"),
                    "status": data.get("status", "active"),
                    "main_username": data.get("main_username", "unknown"),
                    "os_version": data.get("os", "unknown"),  # Map os -> os_version
                    "architecture": data.get("architecture"),
                    "architecture_bits": data.get("architecture_bits"),
                    "processor_type": data.get("processor_type"),
                    "cpu_cores": data.get("cpu_cores"),
                    "vendor": data.get("vendor", "unknown"),
                    "connected": True,
                    "last_seen": time.time()
                }

                # Hanya ambil dari meta yang diperlukan
                meta = data.get("meta", {})
                if meta:
                    # Hanya virtualization yang diambil dari meta
                    if "virtualization" in meta:
                        server_data["virtualization"] = meta["virtualization"]
                    
                    # Simpan meta terpisah jika perlu
                    server_data["meta"] = {
                        "interfaces": meta.get("interfaces", []),
                        "detected_ips": meta.get("detected_ips", []),
                        "interface_details": meta.get("interface_details", {})
                    }

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
                
                # Map MikroTik specific fields
                data.update({
                    "username": data.get("username", "admin"),
                    "identity": info.get("identity"),
                    "os_version": info.get("version"),
                    "board": info.get("board-name"),
                    "serial_number": info.get("serial-number"),
                    "vendor": "MikroTik",
                    "main_ip_address": data.get("ip"),
                    "main_mac_address": info.get("mac-address"),
                    "main_interface": info.get("main_interface"),
                    "southbound": "routeros_api",
                    "status": "active"
                })
                
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
                    "last_seen": time.time()
                }
                
                # Check for duplicates by device_id
                existing = DeviceRepository.find_by_device_id(device_id)
                
                if existing:
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
                            "cpu_cores": data.get("cpu_cores"),
                            "virtualization": data.get("virtualization"),
                            "last_seen": time.time()
                        }
                        DeviceRepository.update_server(device_id, server_data)
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
                            "last_seen": time.time()
                        }
                        DeviceRepository.update_router(device_id, router_data)
                    
                    self.core.logger.info(f"Updated existing device in database: {device_id}")
                    
                else:
                    # Insert new device
                    # First insert to network_devices
                    network_id = DeviceRepository.insert_network_device(common_data)
                    
                    # Then insert to specific table
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
                            "cpu_cores": data.get("cpu_cores"),
                            "virtualization": data.get("virtualization")
                        }
                        DeviceRepository.insert_server(server_data)
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
                        clean_dev = {
                            "id": i,
                            "device_id": dev.get("device_id"),
                            "device_type": dev.get("device_type", "unknown"),
                            "southbound": dev.get("southbound", "unknown"),
                            "status": dev.get("status", "active"),
                            "created_at": dev.get("created_at"),
                            "updated_at": dev.get("updated_at"),
                            "last_seen": dev.get("last_seen")
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
                                "cpu_cores": dev.get("cpu_cores"),
                                "memory_total": dev.get("memory_total"),
                                "disk_total": dev.get("disk_total"),
                                "virtualization": dev.get("virtualization")
                            })
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
                    
                    clean_dev = {
                        "id": i,
                        "device_id": dev.get("id"),
                        "device_type": device_type,
                        "southbound": dev.get("southbound", "unknown"),
                        "status": dev.get("status", "active"),
                        "last_seen": dev.get("last_seen")
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
                            "cpu_cores": dev.get("cpu_cores"),
                            "virtualization": dev.get("virtualization")
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

    @route('prometheus-targets', '/api/prometheus/server/targets', methods=['GET'])
    def prometheus_targets(self, req, **kwargs):
        """HTTP Service Discovery endpoint untuk Prometheus"""
        try:
            devices = self.core.devices.list()
            
            # Format response untuk Prometheus HTTP SD
            targets = []
            
            for device in devices:
                # Filter hanya server devices dengan southbound = server_api
                if device.get('southbound') == 'server_api':
                    # Ambil IP dari device - pakai main_ip atau ip
                    ip = device.get('main_ip') or device.get('ip')
                    hostname = device.get('hostname', 'unknown')
                    device_id = device.get('id', 'unknown')
                    
                    # Validasi IP
                    if ip and ip != '127.0.0.1' and ip != 'unknown':
                        target = {
                            "targets": [f"{ip}:9100"],  # Node Exporter port
                            "labels": {
                                "instance": ip,
                                "hostname": hostname,
                                "device_id": device_id,
                                "job": "node-exporter-servers",
                                "group": "servers",
                                "os": device.get('os', 'unknown'),
                                "architecture": device.get('architecture', 'unknown'),
                                "southbound": "server_api"
                            }
                        }
                        targets.append(target)
                        
                        print(f"Prometheus-SD Added target: {ip} ({hostname})")
            
            print(f"Prometheus-SD Generated {len(targets)} targets from {len(devices)} total devices")
            
            body = json.dumps(targets)
            return self._resp(req, body)
            
        except Exception as e:
            import traceback
            print(f"Prometheus-SD Error generating targets: {e}")
            print(traceback.format_exc())
            
            # Return empty array jika error
            body = json.dumps([])
            return self._resp(req, body)