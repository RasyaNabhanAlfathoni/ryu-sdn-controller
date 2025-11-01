from ryu.base import app_manager
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from ryu.lib import hub
from webob import Response
import json, uuid, time

from drivers.routeros_api import RouterOSApiDriver
from drivers.ip import RouterOSIpDriver
from drivers.interface import RouterOSInterfaceDriver
from drivers.vlan import RouterOSVlanDriver
from drivers.dhcp_server import RouterOSDhcpServerDriver
from drivers.dhcp_client import RouterOSDhcpClientDriver
from drivers.ip_pool import RouterOSIpPoolDriver
from drivers.dns_server import RouterOSDnsDriver
from drivers.neighbor import RouterOSNeighborDriver

API_INSTANCE_NAME = 'northbound_api'

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
        """
        Coba deteksi vendor & southbound API secara otomatis.
        1. Test RouterOS API (port 8728)
        2. [Future] Cisco RESTCONF
        3. [Future] Juniper NETCONF
        """
        # (Mikrotik, RouterOS API)
        from drivers.routeros_api import RouterOSApiDriver
        try:
            driver = RouterOSApiDriver(dev)
            info = driver.get_device_info()
            info["southbound"] = "routeros_api"
            info["vendor"] = "MikroTik"
            info["connected"] = True
            return info
        except Exception:
            pass  # Kalau gagal connect Mikrotik, lanjut test lain

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
        return self.dispatch(driver, action, params, jid)

    def pick_driver(self, dev):
        sb = dev.get("southbound", "api")
        return RouterOSApiDriver(dev)


    def dispatch(self, d, action, params, jid):
        fnmap = {
            # IP Address Management
            "ip.address.add": lambda p, logger: RouterOSIpDriver(d).add_address(p, logger),
            "ip.address.remove": lambda p, logger: RouterOSIpDriver(d).remove_address(p, logger),
            "ip.address.edit": lambda p, logger: RouterOSIpDriver(d).edit_address(p, logger),
            "ip.address.disable": lambda p, logger: RouterOSIpDriver(d).disable_address(p, logger),
            "ip.address.enable": lambda p, logger: RouterOSIpDriver(d).enable_address(p, logger),
            "ip.address.comment": lambda p, logger: RouterOSIpDriver(d).comment_address(p, logger),

            # IP POOL Management
            "ip.pool.add": lambda p, logger: RouterOSIpPoolDriver(d).add_pool(p, logger),
            "ip.pool.edit": lambda p, logger: RouterOSIpPoolDriver(d).edit_pool(p, logger),
            "ip.pool.delete": lambda p, logger: RouterOSIpPoolDriver(d).delete_pool(p, logger),
            "ip.pool.comment": lambda p, logger: RouterOSIpPoolDriver(d).comment_pool(p, logger),

            # Interface Management
            "interface.edit": lambda p, logger: RouterOSInterfaceDriver(d).edit_interface(p, logger),
            "interface.disable": lambda p, logger: RouterOSInterfaceDriver(d).disable_interface(p, logger),
            "interface.enable": lambda p, logger: RouterOSInterfaceDriver(d).enable_interface(p, logger),
            "interface.comment": lambda p, logger: RouterOSInterfaceDriver(d).comment_interface(p, logger),
            "interface.cable_test": lambda p, logger: RouterOSInterfaceDriver(d).cable_test(p, logger),

            # VLAN Management
            "vlan.add": lambda p, logger: RouterOSVlanDriver(d).add_vlan(p, logger),
            "vlan.edit": lambda p, logger: RouterOSVlanDriver(d).edit_vlan(p, logger),
            "vlan.delete": lambda p, logger: RouterOSVlanDriver(d).delete_vlan(p, logger),
            "vlan.enable": lambda p, logger: RouterOSVlanDriver(d).enable_vlan(p, logger),
            "vlan.disable": lambda p, logger: RouterOSVlanDriver(d).disable_vlan(p, logger),
            "vlan.comment": lambda p, logger: RouterOSVlanDriver(d).comment_vlan(p, logger),

            # DHCP SERVER
            "dhcp.server.add": lambda p, logger: RouterOSDhcpServerDriver(d).add_server(p, logger),
            "dhcp.server.edit": lambda p, logger: RouterOSDhcpServerDriver(d).edit_server(p, logger),
            "dhcp.server.enable": lambda p, logger: RouterOSDhcpServerDriver(d).enable_server(p, logger),
            "dhcp.server.disable": lambda p, logger: RouterOSDhcpServerDriver(d).disable_server(p, logger),
            "dhcp.server.delete": lambda p, logger: RouterOSDhcpServerDriver(d).delete_server(p, logger),
            "dhcp.network.edit": lambda p, logger: RouterOSDhcpServerDriver(d).edit_network(p, logger),

            # DHCP CLIENT
            "dhcp.client.add": lambda p, logger: RouterOSDhcpClientDriver(d).add_client(p, logger),
            "dhcp.client.edit": lambda p, logger: RouterOSDhcpClientDriver(d).edit_client(p, logger),
            "dhcp.client.enable": lambda p, logger: RouterOSDhcpClientDriver(d).enable_client(p, logger),
            "dhcp.client.disable": lambda p, logger: RouterOSDhcpClientDriver(d).disable_client(p, logger),
            "dhcp.client.delete": lambda p, logger: RouterOSDhcpClientDriver(d).delete_client(p, logger),
            "dhcp.client.comment": lambda p, logger: RouterOSDhcpClientDriver(d).comment_client(p, logger),

            # DNS Configuration
            "dns.edit": lambda p, logger: RouterOSDnsDriver(d).edit_dns(p, logger),
            "dns.flush": lambda p, logger: RouterOSDnsDriver(d).flush_cache(p, logger),
            "dns.static.add": lambda p, logger: RouterOSDnsDriver(d).add_static(p, logger),
            "dns.static.edit": lambda p, logger: RouterOSDnsDriver(d).edit_static(p, logger),
            "dns.static.enable": lambda p, logger: RouterOSDnsDriver(d).enable_static(p, logger),
            "dns.static.disable": lambda p, logger: RouterOSDnsDriver(d).disable_static(p, logger),
            "dns.static.comment": lambda p, logger: RouterOSDnsDriver(d).comment_static(p, logger),
            "dns.static.delete": lambda p, logger: RouterOSDnsDriver(d).delete_static(p, logger),

            # Neighbor List
            "neighbor.get": lambda p, logger: RouterOSNeighborDriver(d).get_neighbors(p, logger),
            "neighbor.discovery.get": lambda p, logger: RouterOSNeighborDriver(d).get_discovery_settings(p, logger),
            "neighbor.discovery.edit": lambda p, logger: RouterOSNeighborDriver(d).edit_discovery_settings(p, logger),

            # Identity
            "identity.set": d.set_identity,

            # Interface / Route (legacy)
            "route.add": d.add_route,
            "raw.run": d.run_raw
        }

        if action not in fnmap: 
            self.jobs.append_log(jid, f"ERROR: Unknown action '{action}'")
            raise ValueError(f"Unknown action: {action}")

        try:
            self.jobs.append_log(jid, f"Executing {action} with params: {params}")
            result = fnmap[action](params, logger=lambda s: self.jobs.append_log(jid, s))
            self.jobs.append_log(jid, f"{action} completed successfully")
            self.jobs.set(jid, result=result)
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
        body = json.dumps(devices)
        return self._resp(req, body)

    @route('devices', '/devices', methods=['POST'])
    def create_device(self, req, **kwargs):
        data = json.loads(req.body)
        try:
            # Generate ID otomatis
            new_id = f"r{len(self.core.devices.db) + 1}"
            data["id"] = new_id

            # Tes Koneksi & deteksi vendor otomatis
            info = self.core.detect_vendor(data)
            data.update(info)

            # Simpan DeviceRegistry
            result = self.core.devices.create(data)

            # Response sukses
            body = json.dumps({
                "status": "ok",
                "device": result
            })

        except Exception as e:
            # Response Error
            body = json.dumps({
                "status": "error",
                "error": str(e)
            })

        # Pastikan UTF-8 encoded biar gak error di WebOb
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
