from ryu.base import app_manager
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from ryu.lib import hub
from webob import Response
import json, uuid, time, datetime
import os, sys, threading

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, root_dir)  # Gunakan insert(0) agar priority tinggi

# == Mikrotik Driver ==
# Import library driver mikrotik yang telah dibuat
from mikrotik.drivers.routeros_api import RouterOSApiDriver
from mikrotik.drivers.ip import RouterOSIpDriver
# from mikrotik.drivers.interface import RouterOSInterfaceDriver
# from mikrotik.drivers.vlan import RouterOSVlanDriver
#from drivers.routeros_ssh import RouterOSSshDriver
#from drivers.routeros_restv7 import RouterOSRestV7Driver

# == Server Driver ==
# Import library driver server yang telah dibuat 
from server.drivers.server_api import ServerAPI
from server.drivers.firewall import FirewallDriver
from server.drivers.ip import ServerIpDriver
from server.drivers.monitor import monitor_server

API_INSTANCE_NAME = 'northbound_api'

# Ini sesuaikan dengan secret key nya ya
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
        # Deteksi otomatis tipe perangkat: RouterOS API (MikroTik) dan Server (Linux)

        # (Mikrotik, RouterOS API)
        from mikrotik.drivers.routeros_api import RouterOSApiDriver
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
        from server.drivers.server_api import ServerAPI
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
        fnmap = {
            # IP Address Management
            "ip.address.add": lambda p, logger: RouterOSIpDriver(d).add_address(p, logger),
            "ip.address.remove": lambda p, logger: RouterOSIpDriver(d).remove_address(p, logger),
            "ip.address.edit": lambda p, logger: RouterOSIpDriver(d).edit_address(p, logger),
            "ip.address.disable": lambda p, logger: RouterOSIpDriver(d).disable_address(p, logger),
            "ip.address.enable": lambda p, logger: RouterOSIpDriver(d).enable_address(p, logger),
            "ip.address.comment": lambda p, logger: RouterOSIpDriver(d).comment_address(p, logger),

            # # Interface Management
            # "interface.edit": lambda p, logger: RouterOSInterfaceDriver(d).edit_interface(p, logger),
            # "interface.disable": lambda p, logger: RouterOSInterfaceDriver(d).disable_interface(p, logger),
            # "interface.enable": lambda p, logger: RouterOSInterfaceDriver(d).enable_interface(p, logger),
            # "interface.comment": lambda p, logger: RouterOSInterfaceDriver(d).comment_interface(p, logger),
            # "interface.cable_test": lambda p, logger: RouterOSInterfaceDriver(d).cable_test(p, logger),

            # # VLAN Management
            # "vlan.add": lambda p, logger: RouterOSVlanDriver(d).add_vlan(p, logger),
            # "vlan.edit": lambda p, logger: RouterOSVlanDriver(d).edit_vlan(p, logger),
            # "vlan.delete": lambda p, logger: RouterOSVlanDriver(d).delete_vlan(p, logger),
            # "vlan.enable": lambda p, logger: RouterOSVlanDriver(d).enable_vlan(p, logger),
            # "vlan.disable": lambda p, logger: RouterOSVlanDriver(d).disable_vlan(p, logger),
            # "vlan.comment": lambda p, logger: RouterOSVlanDriver(d).comment_vlan(p, logger),

            # # Identity
            # "identity.set": d.set_identity,

            # # Interface / Route (legacy)
            # "route.add": d.add_route,
            # "raw.run": d.run_raw,

            # === Server Commands ===
            # IP Management - SEKARANG PAKAI INSTANCE METHODS
            "server.ip.list_interfaces": lambda p, logger: d.list_interfaces(logger=logger),
            "server.ip.get_interface_details": lambda p, logger: d.get_interface_details(logger=logger),
            "server.ip.show_all": lambda p, logger: d.show_all(logger=logger),
            "server.ip.add": lambda p, logger: d.add_ip(p.get("iface"), p.get("ip_cidr"), logger=logger),
            "server.ip.remove": lambda p, logger: d.del_ip(p.get("iface"), p.get("ip_cidr"), logger=logger),
            "server.ip.enable_interface": lambda p, logger: d.enable_iface(p.get("iface"), logger=logger),
            "server.ip.disable_interface": lambda p, logger: d.disable_iface(p.get("iface"), logger=logger),
            "server.ip.get_single_interface": lambda p, logger: d.get_ip_info(p.get("iface"), logger=logger),
            "server.ip.get_interface_ips": lambda p, logger: d.get_interface_ips(p.get("iface"), logger=logger),
            "server.ip.get_interface_status": lambda p, logger: d.get_interface_status(p.get("iface"), logger=logger),

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

            # Monitor - TETAP STATIC KARENA SUDAH @staticmethod
            "server.monitor": lambda p, logger: d.get_utilization(logger=logger),

        }

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
            "hostname": dev.get("hostname"),
            "ip": dev.get("ip"),
            "role": dev.get("role", "agent"),
            "os": dev.get("os"),
            "southbound": dev.get("southbound"),
            "connected": dev.get("connected", False),
            "last_seen": dev.get("last_seen"),
            "username": dev.get("username", "root")
        }
        
        # Hanya tambahkan meta jika ada data penting ( yg ditambahkan di meta )
        if dev.get("meta") and dev.get("meta").get("detected_ips"):
            clean_dev["meta"] = {"detected_ips": dev["meta"]["detected_ips"]}
        if dev["meta"].get("mac_addresses"):
            clean_dev["mac_addresses"] = dev["meta"]["mac_addresses"]
        if dev["meta"].get("interface_details"):
            clean_dev["interface_details"] = dev["meta"]["interface_details"]
            
        clean_devices.append(clean_dev)
        
        body = json.dumps(clean_devices)
        return self._resp(req, body)
    
    # Panggil device berdasarkan ID
    @route('devices', '/devices/{device_id}', methods=['GET'])
    def get_device(self, req, device_id, **kwargs):
        """Get specific device by ID"""
        try:
            device = self.core.devices.get(device_id)
            body = json.dumps(device)
        except KeyError:
            body = json.dumps({"error": "Device not found"})
        
        return self._resp(req, body)

    @route('devices', '/devices', methods=['POST'])
    def create_device(self, req, **kwargs):
        if not _check_api_key(req):
            return self._resp(req, json.dumps({"status":"error","error":"unauthorized"}), status=401)
        
        data = json.loads(req.body)
        
        # Ambil IP dari connection source sebagai prioritas utama
        client_ip = req.remote_addr
        if client_ip and client_ip != '127.0.0.1':
            print(f"[CONTROLLER] Using client IP from connection: {client_ip}")
            data["ip"] = client_ip
        else:
            # Jika masih localhost, cari di headers (jika behind proxy)
            forwarded_for = req.headers.get('X-Forwarded-For')
            real_ip = req.headers.get('X-Real-IP')
            if forwarded_for:
                real_client_ip = forwarded_for.split(',')[0].strip()
                if real_client_ip and real_client_ip != '127.0.0.1':
                    print(f"[CONTROLLER] Using X-Forwarded-For IP: {real_client_ip}")
                    data["ip"] = real_client_ip
            elif real_ip and real_ip != '127.0.0.1':
                print(f"[CONTROLLER] Using X-Real-IP: {real_ip}")
                data["ip"] = real_ip
            else:
                print(f"[CONTROLLER] WARNING: Using IP from request body: {data.get('ip')}")
        
        try:
            # Generate device ID yang konsisten berdasarkan IP + Hostname
            import hashlib
            device_ip = data.get("ip", "unknown")
            device_hostname = data.get("meta", {}).get("hostname", "unknown")
            unique_str = f"{device_ip}_{device_hostname}"
            device_id = f"r{hashlib.md5(unique_str.encode()).hexdigest()[:8]}"
            data["id"] = device_id

            # Cek apakah device dengan IP ini sudah ada
            existing_device = next((d for d in self.core.devices.db.values() 
                                if d.get("ip") == device_ip), None)
            
            if existing_device:
                print(f"[CONTROLLER] Device with IP {device_ip} already exists: {existing_device.get('id')}")
                return self._resp(req, json.dumps({
                    "status": "ok", 
                    "device": existing_device,
                    "message": "Device already registered"
                }))
            
            data["id"] = device_id
            
            # info = self.core.detect_vendor(data)

            # ambil meta dari agent (kalau ada)
            meta = data.get("meta", {})

            # data dari Agent ( ini yang akan tampil saat curl device )
            data["hostname"] = meta.get("hostname", data.get("hostname", "unknown"))
            data["os"] = meta.get("os", data.get("os", "UnknownOS"))
            data["southbound"] = meta.get("southbound", data.get("southbound", "server_local"))
            data["role"] = data.get("role", "agent")  # Gunakan role dari agent
            data["connected"] = True
            data["username"] = data.get("username", "root")

             # Tambahkan interfaces dari meta jika ada
            if "interfaces" in meta:
                data["interfaces"] = meta["interfaces"]
            
            # Simpan meta yang dikirim agent
            if meta:
                data["meta"] = meta

            # data.update(info)
            
            # Simpan ke registry
            result = self.core.devices.create(data)

            # Start monitoring jika server agent
            if result.get("southbound") == "server_local" and result.get("role") == "agent":
                threading.Thread(
                    target=monitor_server,
                    args=({"id": result["id"], "ip": result["ip"]},),
                    daemon=True
                ).start()

            body = json.dumps({
                "status": "ok",
                "device": result
            })

        except Exception as e:
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
            dev_ip = dev.get("ip")  # Simpan IP sebelum mungkin exception
            self.core.logger.info(f"Heartbeat from {did} (IP: {dev_ip})")
        except Exception as e:
            self.core.logger.warning(f"Heartbeat: Device {did} not in registry: {e}")

        return self._resp(req, json.dumps({"status":"ok", "device": did}))

