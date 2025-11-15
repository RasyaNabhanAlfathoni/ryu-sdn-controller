import os, sys, threading
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ryu.base import app_manager
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from ryu.lib import hub
from webob import Response
import json, uuid, time, datetime

# === MikroTik Driver ===
from drivers.snmp_file_manager import SNMPFileManager
from drivers.router_drivers.mikrotik.routeros_api import RouterOSApiDriver
from drivers.router_drivers.mikrotik.ip import RouterOSIpDriver
from drivers.router_drivers.mikrotik.interface import RouterOSInterfaceDriver
from drivers.router_drivers.mikrotik.vlan import RouterOSVlanDriver
from drivers.router_drivers.mikrotik.dhcp_server import RouterOSDhcpServerDriver
from drivers.router_drivers.mikrotik.dhcp_client import RouterOSDhcpClientDriver
from drivers.router_drivers.mikrotik.ip_pool import RouterOSIpPoolDriver
from drivers.router_drivers.mikrotik.dns_server import RouterOSDnsDriver
from drivers.router_drivers.mikrotik.neighbor import RouterOSNeighborDriver
from drivers.router_drivers.mikrotik.snmp import RouterOSSNMPDriver

# === Server Driver ===
from drivers.server_drivers.server_api import ServerAPI

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
        dev = self.devices.get(p["device_id"])
        driver = self.pick_driver(dev)
        action = p["action"]; params = p.get("params", {})
        self.jobs.append_log(jid, f"Use driver: {driver.name}")
        
        result = self.dispatch(driver, action, params, jid)
        
        # Simpan hasil ke jobs store
        self.jobs.set(jid, result=result)
        
        return result

    def pick_driver(self, dev):
        sb = dev.get("southbound", "")
        if sb == "routeros_api":
            return RouterOSApiDriver(dev)
        elif sb == "server_api":
            return ServerAPI(dev)
        else:
            raise ValueError(f"Unknown southbound driver: {sb}")

    def dispatch(self, d, action, params, jid):
        # Deteksi tipe driver berdasarkan class
        driver_type = "unknown"
        if hasattr(d, '__class__'):
            if 'RouterOS' in d.__class__.__name__:
                driver_type = "mikrotik"
            elif 'ServerAPI' in d.__class__.__name__:
                driver_type = "server"

        # === Buat fnmap berbeda berdasarkan driver type ===
        if driver_type == "mikrotik":
            fnmap = {
                # === Router MikroTik Commands ===

                # IP Address Management
                "mikrotik.ip.address.add": lambda p, logger: RouterOSIpDriver(d).add_address(p, logger),
                "mikrotik.ip.address.remove": lambda p, logger: RouterOSIpDriver(d).remove_address(p, logger),
                "mikrotik.ip.address.edit": lambda p, logger: RouterOSIpDriver(d).edit_address(p, logger),
                "mikrotik.ip.address.disable": lambda p, logger: RouterOSIpDriver(d).disable_address(p, logger),
                "mikrotik.ip.address.enable": lambda p, logger: RouterOSIpDriver(d).enable_address(p, logger),
                "mikrotik.ip.address.comment": lambda p, logger: RouterOSIpDriver(d).comment_address(p, logger),

                # IP POOL Management
                "mikrotik.ip.pool.add": lambda p, logger: RouterOSIpPoolDriver(d).add_pool(p, logger),
                "mikrotik.ip.pool.edit": lambda p, logger: RouterOSIpPoolDriver(d).edit_pool(p, logger),
                "mikrotik.ip.pool.delete": lambda p, logger: RouterOSIpPoolDriver(d).delete_pool(p, logger),
                "mikrotik.ip.pool.comment": lambda p, logger: RouterOSIpPoolDriver(d).comment_pool(p, logger),

                # Interface Management
                "mikrotik.interface.edit": lambda p, logger: RouterOSInterfaceDriver(d).edit_interface(p, logger),
                "mikrotik.interface.disable": lambda p, logger: RouterOSInterfaceDriver(d).disable_interface(p, logger),
                "mikrotik.interface.enable": lambda p, logger: RouterOSInterfaceDriver(d).enable_interface(p, logger),
                "mikrotik.interface.comment": lambda p, logger: RouterOSInterfaceDriver(d).comment_interface(p, logger),
                "mikrotik.interface.cable_test": lambda p, logger: RouterOSInterfaceDriver(d).cable_test(p, logger),

                # VLAN Management
                "mikrotik.vlan.add": lambda p, logger: RouterOSVlanDriver(d).add_vlan(p, logger),
                "mikrotik.vlan.edit": lambda p, logger: RouterOSVlanDriver(d).edit_vlan(p, logger),
                "mikrotik.vlan.delete": lambda p, logger: RouterOSVlanDriver(d).delete_vlan(p, logger),
                "mikrotik.vlan.enable": lambda p, logger: RouterOSVlanDriver(d).enable_vlan(p, logger),
                "mikrotik.vlan.disable": lambda p, logger: RouterOSVlanDriver(d).disable_vlan(p, logger),
                "mikrotik.vlan.comment": lambda p, logger: RouterOSVlanDriver(d).comment_vlan(p, logger),

                # DHCP SERVER
                "mikrotik.dhcp.server.add": lambda p, logger: RouterOSDhcpServerDriver(d).add_server(p, logger),
                "mikrotik.dhcp.server.edit": lambda p, logger: RouterOSDhcpServerDriver(d).edit_server(p, logger),
                "mikrotik.dhcp.server.enable": lambda p, logger: RouterOSDhcpServerDriver(d).enable_server(p, logger),
                "mikrotik.dhcp.server.disable": lambda p, logger: RouterOSDhcpServerDriver(d).disable_server(p, logger),
                "mikrotik.dhcp.server.delete": lambda p, logger: RouterOSDhcpServerDriver(d).delete_server(p, logger),
                "mikrotik.dhcp.network.edit": lambda p, logger: RouterOSDhcpServerDriver(d).edit_network(p, logger),

                # DHCP CLIENT
                "mikrotik.dhcp.client.add": lambda p, logger: RouterOSDhcpClientDriver(d).add_client(p, logger),
                "mikrotik.dhcp.client.edit": lambda p, logger: RouterOSDhcpClientDriver(d).edit_client(p, logger),
                "mikrotik.dhcp.client.enable": lambda p, logger: RouterOSDhcpClientDriver(d).enable_client(p, logger),
                "mikrotik.dhcp.client.disable": lambda p, logger: RouterOSDhcpClientDriver(d).disable_client(p, logger),
                "mikrotik.dhcp.client.delete": lambda p, logger: RouterOSDhcpClientDriver(d).delete_client(p, logger),
                "mikrotik.dhcp.client.comment": lambda p, logger: RouterOSDhcpClientDriver(d).comment_client(p, logger),

                # DNS Configuration
                "mikrotik.dns.edit": lambda p, logger: RouterOSDnsDriver(d).edit_dns(p, logger),
                "mikrotik.dns.flush": lambda p, logger: RouterOSDnsDriver(d).flush_cache(p, logger),
                "mikrotik.dns.static.add": lambda p, logger: RouterOSDnsDriver(d).add_static(p, logger),
                "mikrotik.dns.static.edit": lambda p, logger: RouterOSDnsDriver(d).edit_static(p, logger),
                "mikrotik.dns.static.enable": lambda p, logger: RouterOSDnsDriver(d).enable_static(p, logger),
                "mikrotik.dns.static.disable": lambda p, logger: RouterOSDnsDriver(d).disable_static(p, logger),
                "mikrotik.dns.static.comment": lambda p, logger: RouterOSDnsDriver(d).comment_static(p, logger),
                "mikrotik.dns.static.delete": lambda p, logger: RouterOSDnsDriver(d).delete_static(p, logger),

                # Neighbor List
                "mikrotik.neighbor.get": lambda p, logger: RouterOSNeighborDriver(d).get_neighbors(p, logger),
                "mikrotik.neighbor.discovery.get": lambda p, logger: RouterOSNeighborDriver(d).get_discovery_settings(p, logger),
                "mikrotik.neighbor.discovery.edit": lambda p, logger: RouterOSNeighborDriver(d).edit_discovery_settings(p, logger),

                # SNMP RouterOS native config
                "mikrotik.snmp.config.get": lambda p, logger: RouterOSSNMPDriver(d).get_snmp_config(p, logger),
                "mikrotik.snmp.config.edit": lambda p, logger: RouterOSSNMPDriver(d).edit_snmp_config(p, logger),
                "mikrotik.snmp.community.list": lambda p, logger: RouterOSSNMPDriver(d).list_communities(p, logger),
                "mikrotik.snmp.community.add": lambda p, logger: RouterOSSNMPDriver(d).add_community(p, logger),
                "mikrotik.snmp.community.edit": lambda p, logger: RouterOSSNMPDriver(d).edit_community(p, logger),
                "mikrotik.snmp.community.delete": lambda p, logger: RouterOSSNMPDriver(d).delete_community(p, logger),
                "mikrotik.snmp.community.enable": lambda p, logger: RouterOSSNMPDriver(d).enable_community(p, logger),
                "mikrotik.snmp.community.disable": lambda p, logger: RouterOSSNMPDriver(d).disable_community(p, logger),
                "mikrotik.snmp.device.add": lambda p, logger: SNMPFileManager().add_device(p),

                # Identity
                "mikrotik.identity.set": d.set_identity,

                # Interface / Route (legacy)
                "mikrotik.route.add": d.add_route,
                "mikrotik.raw.run": d.run_raw,
            }
        elif driver_type == "server":
            fnmap = {

            # === Server Commands ===

            # Network Management
            "server.network.list_interfaces": lambda p, logger: d.list_interfaces(logger=logger),
            "server.network.get_interface_details": lambda p, logger: d.get_interface_details(logger=logger),
            "server.network.ip.show_all": lambda p, logger: d.show_all(logger=logger),
            "server.network.ip.add": lambda p, logger: d.add_ip(p.get("iface"), p.get("ip_cidr"), logger=logger),
            "server.network.ip.remove": lambda p, logger: d.del_ip(p.get("iface"), p.get("ip_cidr"), logger=logger),
            "server.network.enable_interface": lambda p, logger: d.enable_iface(p.get("iface"), logger=logger),
            "server.network.disable_interface": lambda p, logger: d.disable_iface(p.get("iface"), logger=logger),
            "server.network.get_single_interface": lambda p, logger: d.get_ip_info(p.get("iface"), logger=logger),
            "server.network.get_interface_ips": lambda p, logger: d.get_interface_ips(p.get("iface"), logger=logger),
            "server.network.get_interface_status": lambda p, logger: d.get_interface_status(p.get("iface"), logger=logger),
            "server.network.connections": lambda p, logger: d.get_network_connections(logger=logger),
            "server.network.interface_counters": lambda p, logger: d.get_interface_counters(p.get("iface"), logger=logger),

            # Advanced Network Management 
            "server.network.port_scan": lambda p, logger: d.port_scan(p.get("target"), p.get("ports"), logger=logger),
            "server.network.routing_table": lambda p, logger: d.get_routing_table(logger=logger),
            "server.network.arp_table": lambda p, logger: d.get_arp_table(logger=logger),

            # Firewall Management - UFW
            "server.firewall.ufw_status": lambda p, logger: d.ufw_status(logger=logger),
            "server.firewall.ufw_enable": lambda p, logger: d.ufw_enable(logger=logger),
            "server.firewall.ufw_disable": lambda p, logger: d.ufw_disable(logger=logger),
            "server.firewall.ufw_reload": lambda p, logger: d.ufw_reload(logger=logger),
            "server.firewall.ufw_reset": lambda p, logger: d.ufw_reset(logger=logger),
            "server.firewall.ufw_allow": lambda p, logger: d.ufw_allow(p.get("port_proto"), logger=logger),
            "server.firewall.ufw_deny": lambda p, logger: d.ufw_deny(p.get("port_proto"), logger=logger),
            "server.firewall.ufw_delete": lambda p, logger: d.ufw_delete(p.get("rule"), logger=logger),
            "server.firewall.ufw_allow_in": lambda p, logger: d.ufw("allow", "in", p.get("port_proto"), logger=logger),
            "server.firewall.ufw_allow_out": lambda p, logger: d.ufw("allow", "out", p.get("port_proto"), logger=logger),
            "server.firewall.ufw_deny_in": lambda p, logger: d.ufw("deny", "in", p.get("port_proto"), logger=logger),
            "server.firewall.ufw_deny_out": lambda p, logger: d.ufw("deny", "out", p.get("port_proto"), logger=logger),
            
            # Firewall Management - Firewalld
            "server.firewall.firewalld_status": lambda p, logger: d.firewall_status(logger=logger),
            "server.firewall.firewalld_reload": lambda p, logger: d.firewall_reload(logger=logger),
            "server.firewall.firewalld_add_port": lambda p, logger: d.firewall_add_port(p.get("port_proto"), logger=logger),
            "server.firewall.firewalld_remove_port": lambda p, logger: d.firewall_remove_port(p.get("port_proto"), logger=logger),
            "server.firewall.firewalld_enable_masquerade": lambda p, logger: d.firewall_enable_masquerade(logger=logger),
            "server.firewall.firewalld_disable_masquerade": lambda p, logger: d.firewall_disable_masquerade(logger=logger),
            "server.firewall.firewalld_list_ports": lambda p, logger: d.firewall_cmd("--list-ports", logger=logger),
            "server.firewall.firewalld_list_services": lambda p, logger: d.firewall_cmd("--list-services", logger=logger),
            "server.firewall.firewalld_command": lambda p, logger: d.firewall_cmd(p.get("args"), logger=logger),
            
            # Firewall Management - NAT & General
            "server.firewall.nat.add": lambda p, logger: d.setup_nat(p.get("interface"), logger=logger),
            "server.firewall.nat.clear": lambda p, logger: d.clear_nat(logger=logger),
            "server.firewall.status_all": lambda p, logger: d.status_all(logger=logger),
            "server.firewall.detect_type": lambda p, logger: d.detect_firewall(logger=logger),

            # System Management - Monitor
            "server.system.monitor": lambda p, logger: d.get_utilization(logger=logger),
            "server.system.monitor_detailed": lambda p, logger: d.get_detailed_utilization(logger=logger),
            "server.system.info": lambda p, logger: d.get_system_info(logger=logger),
            "server.system.logs": lambda p, logger: d.get_logs(p.get("lines", 50), logger=logger),
            
            # System Services
            "server.system.services.list": lambda p, logger: d.list_services(logger=logger),
            "server.system.services.control": lambda p, logger: d.service_control(p.get("service"), p.get("action"), logger=logger),
            "server.system.services.status": lambda p, logger: d.service_status(p.get("service"), logger=logger),
            } 
        else:
            fnmap = {}

        if action not in fnmap:
            self.jobs.append_log(jid, f"ERROR: Unknown action '{action}'")
            raise ValueError(f"Unknown action: {action}")

        try:
            self.jobs.append_log(jid, f"Executing {action} with params: {params}")
            result = fnmap[action](params, logger=lambda s: self.jobs.append_log(jid, s))
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
    @route('devices', '/devices', methods=['GET'])
    def list_devices(self, req, **kwargs):
        devices = self.core.devices.list()

        # ubah setiap device biar lebih clean ( ini yg bakal tampil saat curl device )
        clean_devices = []
        for dev in devices:
            clean_dev = {
                "id": dev.get("id"),
                "status": dev.get("status", "ok"),
                "hostname": dev.get("hostname"),
                "main_username": dev.get("main_username"),
                "architecture": dev.get("architecture"),
                "architecture_bits": dev.get("architecture_bits"),
                "processor_type": dev.get("processor_type"),
                "main_ip": dev.get("ip"),
                "main_interface": dev.get("main_interface"),
                "main_mac_address": dev.get("main_mac_address"),
                "vendor": dev.get("vendor"),
                "os": dev.get("os"),
                "southbound": dev.get("southbound"),
                "last_seen": dev.get("last_seen"),   
            }
        
            # Hanya tambahkan meta jika ada data penting ( yg ditambahkan di meta )
            meta = dev.get("meta", {})
            if meta:
                clean_meta = {}
                
                # Include important meta fields
                if meta.get("detected_ips"):
                    clean_meta["detected_ips"] = meta["detected_ips"]
                if meta.get("interface_details"):
                    clean_meta["interface_details"] = meta["interface_details"]
                if meta.get("interfaces"):
                    clean_meta["interfaces"] = meta["interfaces"]
                if meta.get("virtualization"):
                    clean_meta["virtualization"] = meta["virtualization"]
                if meta.get("cpu_cores"):
                    clean_meta["cpu_cores"] = meta["cpu_cores"]
                
                if clean_meta:
                    clean_dev["meta"] = clean_meta
            
            clean_devices.append(clean_dev)
        
        body = json.dumps(clean_devices)
        return self._resp(req, body)
    
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

    # Create devices, disini ambil data dari payload agent_register
    @route('devices', '/devices', methods=['POST'])
    def create_device(self, req, **kwargs):
        # Cek API key untuk semua device (opsional, bisa disesuaikan)
        if not _check_api_key(req):
            return self._resp(req, json.dumps({"status":"error","error":"unauthorized"}), status=401)
        
        data = json.loads(req.body)
        
        # Deteksi tipe device berdasarkan southbound atau parameter lain
        southbound_type = data.get("southbound", "").lower()
        is_server = southbound_type in ["server", "server_api"]
        is_mikrotik = southbound_type in ["mikrotik", "routeros_api"]
        
        try:
            # === GENERATE CONSISTENT DEVICE ID (FIXED VERSION) ===
            def generate_device_id(device_data, registration_mode):
                """
                Generate consistent device ID untuk semua tipe device
                registration_mode: "server_agent" atau "active_discovery"
                """
                import hashlib
                
                # Extract unique identifiers berdasarkan registration mode
                if registration_mode == "server_agent":
                    ip = device_data.get('main_ip_address', 'unknown')
                    hostname = device_data.get('hostname', 'unknown')
                    device_type = "server"
                else:  # active_discovery (mikrotik)
                    ip = device_data.get('ip', 'unknown')
                    hostname = device_data.get('hostname', 'mikrotik_unknown')
                    device_type = "mikrotik"
                
                # Buat string unik yang konsisten
                unique_components = [
                    device_type,
                    ip,
                    hostname,
                    registration_mode
                ]
                unique_str = "_".join(str(c) for c in unique_components)
                
                # Generate hash yang konsisten
                hash_digest = hashlib.sha256(unique_str.encode()).hexdigest()[:10]
                
                return f"dev_{hash_digest}"

            # === MODE SERVER AGENT (Linux Server) ===
            if is_server:
                # PRIORITASkan IP dari body request (dari server agent)
                device_ip_from_body = data.get("main_ip_address")
                client_ip = req.remote_addr
                
                print(f"[CONTROLLER] Server Agent Registration - Body IP: {device_ip_from_body}, Client IP: {client_ip}")
                
                # Prioritaskan IP dari body (Server agent tahu IP-nya sendiri)
                if device_ip_from_body and device_ip_from_body != '127.0.0.1':
                    final_ip = device_ip_from_body
                    print(f"[CONTROLLER] Using IP from request body: {final_ip}")
                elif client_ip and client_ip != '127.0.0.1':
                    final_ip = client_ip
                    print(f"[CONTROLLER] Using client connection IP: {final_ip}")
                else:
                    # Fallback ke headers jika behind proxy
                    forwarded_for = req.headers.get('X-Forwarded-For')
                    real_ip = req.headers.get('X-Real-IP')
                    if forwarded_for:
                        final_ip = forwarded_for.split(',')[0].strip()
                        print(f"[CONTROLLER] Using X-Forwarded-For IP: {final_ip}")
                    elif real_ip and real_ip != '127.0.0.1':
                        final_ip = real_ip
                        print(f"[CONTROLLER] Using X-Real-IP: {final_ip}")
                    else:
                        final_ip = device_ip_from_body or "unknown"
                        print(f"[CONTROLLER] WARNING: Using fallback IP: {final_ip}")
                
                data["ip"] = final_ip
                data["main_ip_address"] = final_ip 
                
                # Generate device ID yang konsisten menggunakan generate_device_id
                device_id = generate_device_id(data, "server_agent")
                data["id"] = device_id

                # ambil meta dari server agent (kalau ada)
                meta = data.get("meta", {})

                # data dari Server Agent ( ini yang akan tampil saat curl device )
                data["hostname"] = data.get("hostname", meta.get("hostname", "unknown"))
                data["os"] = data.get("os", meta.get("os", "UnknownOS"))
                data["southbound"] = data.get("southbound", meta.get("southbound", "unknown"))
                data["connected"] = True
                data["username"] = data.get("main_username", meta.get("username", "unknown"))
                data["last_seen"] = time.time()

                 # Tambahkan field-field baru dari payload
                if "architecture" in data:
                    data["architecture"] = data["architecture"]
                if "architecture_bits" in data:
                    data["architecture_bits"] = data["architecture_bits"]
                if "processor_type" in data:
                    data["processor_type"] = data["processor_type"]
                if "vendor" in data:
                    data["vendor"] = data["vendor"]
                if "main_interface" in data:
                    data["main_interface"] = data["main_interface"]
                if "main_mac_address" in data:
                    data["main_mac_address"] = data["main_mac_address"]
                if "status" in data:
                    data["status"] = data["status"]

                # Tambahkan interfaces dari meta jika ada
                if "interfaces" in meta:
                    data["interfaces"] = meta["interfaces"]

                # Tambahkan cpu core dari meta jika ada
                if "cpu_cores" in meta:
                    data["cpu_cores"] = meta["cpu_cores"]

                # Tambahkan virtualization dari meta jika ada
                if "virtualization" in meta:
                    data["virtualization"] = meta["virtualization"]
                
                # Simpan meta yang dikirim server agent
                if meta:
                    data["meta"] = meta

            # === MODE MIKROTIK (Active Discovery) ===
            elif is_mikrotik:
                print(f"[CONTROLLER] Mikrotik/Active Discovery Registration - IP: {data.get('ip')}")
                
                # --- 1) Test koneksi & deteksi vendor dulu ---
                info = self.core.detect_vendor(data)

                # Jika gagal koneksi/deteksi, jangan buat device — return error
                if not info.get("connected", False):
                    body = json.dumps({
                        "status": "error",
                        "error": "Unable to connect to device or detect vendor",
                        "details": info
                    })
                    if isinstance(body, str):
                        body = body.encode('utf-8')
                    return Response(content_type='application/json', body=body, status=400)

                # --- 2) Kalau sukses: generate ID dan gabungkan info ---
                device_id = generate_device_id(data, "active_discovery")
                data["id"] = device_id
                data.update(info)
            
            else:
                # Handle unknown device type
                return self._resp(req, json.dumps({
                    "status": "error", 
                    "error": "Unknown device type."
                }), status=400)
            
            # === FINAL VALIDATION & REGISTRATION ===
        
            # Cek duplikasi device ID
            if data["id"] in self.core.devices.db:
                self.core.logger.warning(f"Device ID {data['id']} already exists, updating existing device")

            # Simpan ke registry (common untuk kedua mode)
            result = self.core.devices.create(data)

            device_type = "Server Agent" if is_server else "Mikrotik/Active"
            print(f"[CONTROLLER] {device_type} Device registered: {data['id']} - IP: {data.get('ip')} - Hostname: {data.get('hostname', 'unknown')}")

            body = json.dumps({
                "status": "ok",
                "device": result,
                "registration_type": "server_agent" if is_server else "active_discovery",
                "device_id": data["id"]
            })

        except Exception as e:
            import traceback
            self.core.logger.error(f"Device registration failed: {str(e)}\n{traceback.format_exc()}")
            body = json.dumps({
                "status": "error",
                "error": str(e)
            })

        if isinstance(body, str):
            body = body.encode('utf-8')

        return Response(
            content_type='application/json',
            body=body,
            status=200
        )

    def _resp(self, req, body, status=200):
        if isinstance(body, str):
            body = body.encode('utf-8')
        return Response(content_type='application/json', body=body, status=status)
    
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

