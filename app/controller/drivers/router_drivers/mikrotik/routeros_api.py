from drivers.router_drivers.mikrotik.snmp import RouterOSSNMPDriver
from database.device_repository import DeviceRepository
from routeros_api import RouterOsApiPool
from librouteros import connect

class RouterOSApiDriver:
    name = "routeros_api"

    def __init__(self, dev):
        self.dev = dev
        self.host = dev["ip"]
        self.user = dev["username"]
        self.pw = dev["password"]
        self.ssl = dev.get("use_ssl", False)

    # routeros_api
    def get_api(self):
        pool = RouterOsApiPool(
            self.host,
            username=self.user,
            password=self.pw,
            use_ssl=self.ssl,
            plaintext_login=not self.ssl
        )
        return pool, pool.get_api()

    # librouteros
    def get_libapi(self):
        return connect(
            host=self.host,
            username=self.user,
            password=self.pw,
            port=8728,
            use_ssl=False
        )

    def detect_device_type(self, model: str = "", board: str = "") -> str:
        text = f"{model} {board}".lower()

        ap_keywords = [
            "cap",          # cAP, cAP lite, cAP ac
            "cap lite",
            "cap ac",
            "access point",
        ]

        for k in ap_keywords:
            if k in text:
                return "access_point"

        router_keywords = [
            "rb",           # RB4011, RB750, dll
            "routerboard",
        ]

        for k in router_keywords:
            if k in text:
                return "router"
        return "router"

        switch_keywords = [
            "css",           # RB4011, RB750, dll
            "switchboard",
            "switch",
            "crs",
            "swos"           # cloud router switch
        ]

        for k in switch_keywords:
            if k in text:
                return "switch"
        return "switch"

    def get_device_info(self):
        # api v1 routeros_api

        pool = None
        try:
            pool, api = self.get_api()

            identity = api.get_resource('/system/identity').get()[0]["name"]
            res = api.get_resource('/system/resource').get()[0]

            version = res.get("version")
            model = api.get_resource('/system/routerboard').get()[0].get("model", "RouterOS")

            try:
                rb = api.get_resource('/system/routerboard').get()[0]
                serial = rb.get("serial-number", "UNKNOWN")
            except:
                serial = "UNKNOWN"

            ip_rows = api.get_resource('/ip/address').get()
            matched_iface = None

            for r in ip_rows:
                if self.host in r.get("address", ""):
                    matched_iface = r.get("interface")
                    break

            iface_rows = api.get_resource('/interface/ethernet').get()
            if not matched_iface and iface_rows:
                matched_iface = iface_rows[0].get("name")

            mac = None
            for r in iface_rows:
                if r.get("name") == matched_iface:
                    mac = r.get("mac-address")
                    break

            device_type = self.detect_device_type(model=model, board=res.get("board-name", ""))

            pool.disconnect()

            return {
                "identity": identity,
                "version": version,
                "model": model,
                "serial-number": serial,
                "vendor": "MikroTik",
                "mac-address": mac,
                "main_interface": matched_iface,
                "device_type": device_type,
                "connected": True
            }

        except Exception:
            # ke api2
            pass

        finally:
            if pool:
                pool.disconnect()

        # api2 librouteros
        try:
            api2 = self.get_libapi()

            identity = api2("/system/identity/print")[0].get("name")
            res = api2("/system/resource/print")[0]

            version = res.get("version", "UNKNOWN")
            model = api2("/system/routerboard/print")[0].get("model", "RouterOS")
            serial = res.get("serial-number", "UNKNOWN")

            # v7 API tidak expose IP-address → interface mapping dibatasi
            iface_list = None
            mac = None
            iface = None

            device_type = self.detect_device_type(model=model, board=res.get("board-name", ""))

            try:
                iface_list = api2("/interface/ethernet/print")
                if iface_list:
                    iface = iface_list[0].get("name")
                    mac = iface_list[0].get("mac-address")
            except:
                pass

            return {
                "identity": identity,
                "version": version,
                "model": model,
                "serial-number": serial,
                "vendor": "MikroTik",
                "mac-address": mac,
                "main_interface": iface,
                "device_type": device_type,
                "connected": True
            }

        except Exception as e:
            raise Exception(f"[API v1 & v2 FAILED] Cannot read RouterOS: {e}")

    def set_identity(self, p, logger=None):
        pool, api = self.get_api()
        try:
            api.get_resource('/system/identity').set(name=p["name"])
            if logger:
                logger(f"identity set on device -> {p['name']}")
            old = DeviceRepository.find_by_device_id(self.dev["device_id"])
            if not old:
                if logger:
                    logger("[DB] router not found, skip db update")
                return
            old["identity"] = p["name"]
            DeviceRepository.update_router(self.dev["device_id"], old)
            if logger:
                logger(f"[DB] identity updated -> {p['name']}")

        finally:
            pool.disconnect()

    def run_raw(self, p, logger=print):
        raise NotImplementedError("raw.run not supported on API")

    def test_connection(self):
        pool, api = self.get_api()
        try:
            identity = api.get_resource('/system/identity').get()[0]["name"]

            rb = api.get_resource('/system/routerboard').get()
            serial = rb[0].get("serial-number", "UNKNOWN") if rb else "UNKNOWN"

            return True, {
                "identity": identity,
                "serial-number": serial
            }

        finally:
            pool.disconnect()

    def auto_configured_snmp(self, logger=print):
        """
        Auto provision SNMP default on MikroTik
        """

        logger(f"[SNMP-AUTO] Configuring SNMP on {self.host}")

        snmp = RouterOSSNMPDriver(self)

        snmp.edit_snmp_config({
            "enabled": "yes",
            "trap-community": "public",
            "trap-version": "1",
        }, logger=logger)

        snmp.add_community({
            "name": "public",
            "addresses": "::/0",
            "security": "none",
            "read-access": "yes",
            "write-access": "no",
            "comment": "Auto configured by SDN Controller"
        }, logger=logger)

        logger("[SNMP-AUTO] MikroTik SNMP configured successfully")

    def update_device(self, p, logger=None):
        old = DeviceRepository.find_by_device_id(self.dev["device_id"])
        if not old:
            raise Exception("device not found in database")

        new_ip = p.get("ip") or old["main_ip_address"]
        new_user = p.get("username") or old["username"]
        new_pw = p.get("password") or old["password"]

        if ("username" in p) ^ ("password" in p):
            raise Exception("username and password must be updated together")

        if logger:
            logger(f"[UPDATE] trying connect to {new_ip}")

        test_dev = {
            **old,
            "ip": new_ip,
            "username": new_user,
            "password": new_pw
        }
        test_driver = RouterOSApiDriver(test_dev)

        ok, conn_info = test_driver.test_connection()

        if not ok:
            raise Exception("cannot connect using new credentials")

        new_serial = conn_info.get("serial-number")
        identity = conn_info.get("identity")

        old_serial = old.get("serial-number")

        status = "success"

        if old_serial and new_serial and old_serial != new_serial:
            status = "warning"
            if logger:
                logger(
                    f"[WARNING] connected to different device "
                    f"(old serial={old_serial}, new serial={new_serial})"
                )
        else:
            if logger:
                logger("[OK] connected to same device")

        old["main_ip_address"] = new_ip
        old["username"] = new_user
        old["password"] = new_pw
        old["identity"] = identity
        old["serial-number"] = new_serial

        DeviceRepository.update_router(old["device_id"], old)

        if logger:
            logger("[DB] device info updated")

        return {
            "status": status,
            "connected_identity": identity,
            "serial_old": old_serial,
            "serial_new": new_serial
        }