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

    # ===================================================================
    #                           DEVICE INFO (FIXED)
    # ===================================================================
    def get_device_info(self):
        # api v1 routeros_api

        pool = None
        try:
            pool, api = self.get_api()

            identity = api.get_resource('/system/identity').get()[0]["name"]
            res = api.get_resource('/system/resource').get()[0]

            version = res.get("version")
            board = res.get("board-name", "RouterOS")

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

            pool.disconnect()

            return {
                "identity": identity,
                "version": version,
                "board-name": board,
                "serial-number": serial,
                "vendor": "MikroTik",
                "mac-address": mac,
                "main_interface": matched_iface,
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
            board = res.get("board-name", "RouterOS")
            serial = res.get("serial-number", "UNKNOWN")

            # v7 API tidak expose IP-address → interface mapping dibatasi
            iface_list = None
            mac = None
            iface = None

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
                "board-name": board,
                "serial-number": serial,
                "vendor": "MikroTik",
                "mac-address": mac,
                "main_interface": iface,
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