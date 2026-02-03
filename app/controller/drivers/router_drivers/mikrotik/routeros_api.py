from drivers.router_drivers.mikrotik.snmp import RouterOSSNMPDriver
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
            model = "RouterOS"
            serial = "UNKNOWN"

            try:
                rb = api.get_resource('/system/routerboard').get()[0]
                model = rb.get("model", model)
                serial = rb.get("serial-number", serial)
            except Exception:
                # CHR / x86 tidak punya routerboard
                pass

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

            identity_row = next(api2("/system/identity/print"), {})
            identity = identity_row.get("name", "unknown")

            res = next(api2("/system/resource/print"), {})
            version = res.get("version", "UNKNOWN")

            rb = next(api2("/system/routerboard/print"), {})
            model = rb.get("model", "RouterOS")
            serial = rb.get("serial-number", "UNKNOWN")

            device_type = self.detect_device_type(
                model=model,
                board=res.get("board-name", "")
            )

            iface = None
            mac = None
            try:
                iface_row = next(api2("/interface/ethernet/print"), {})
                iface = iface_row.get("name")
                mac = iface_row.get("mac-address")
            except StopIteration:
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

    def set_identity(self, p, logger=print):
        pool, api = self.get_api()
        try:
            api.get_resource('/system/identity').set(name=p["name"])
            logger(f"identity set -> {p['name']}")
        finally:
            pool.disconnect()

    def run_raw(self, p, logger=print):
        raise NotImplementedError("raw.run not supported on API")

    def test_connection(self):
        pool, api = self.get_api()
        try:
            ident = api.get_resource('/system/identity').get()[0]["name"]
            return True, ident
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