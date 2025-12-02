from routeros_api import RouterOsApiPool

class RouterOSApiDriver:
    name = "routeros_api"
    def __init__(self, dev):
        self.host = dev["ip"]; self.user = dev["username"]; self.pw = dev["password"]
        self.ssl = dev.get("use_ssl", False)
    def get_api(self):
        """
        Buka koneksi API ke RouterOS dan return (pool, api)
        Semua driver lain bisa pakai ini
        """
        pool = RouterOsApiPool(
            self.host,
            username=self.user,
            password=self.pw,
            use_ssl=self.ssl,
            plaintext_login=not self.ssl
        )
        return pool, pool.get_api()
    def set_identity(self, p, logger=print):
        pool, api = self.get_api()
        try:
            api.get_resource('/system/identity').set(name=p["name"])
            logger(f"identity set -> {p['name']}")
        finally:
            pool.disconnect()
    def add_route(self, p, logger=print):
        pool, api = self.get_api()
        try:
            payload = {"dst-address": p["dst"], "gateway": p["gateway"]}
            if "distance" in p: payload["distance"] = str(p["distance"])
            api.get_resource('/ip/route').add(**payload)
            logger("route added")
        finally:
            pool.disconnect()
    def run_raw(self, p, logger=print):
        # Untuk API murni tidak ada raw CLI; simpan untuk SSH driver.
        raise NotImplementedError("raw.run not supported on API")
    def test_connection(self):
        """
        Coba connect ke RouterOS dan ambil identity.
        Return True kalau berhasil, atau raise Exception kalau gagal.
        """
        pool, api = self.get_api()
        try:
            # Tes akses API: ambil system identity
            res = api.get_resource('/system/identity')
            identity = res.get()[0]['name']
            return True, identity
        except Exception as e:
            raise e
        finally:
            pool.disconnect()
            
    def get_device_info(self):
        pool, api = self.get_api()
        try:
            # Ambil identity & system resource
            identity = api.get_resource('/system/identity').get()[0]["name"]
            resource = api.get_resource('/system/resource').get()[0]
            version = resource.get("version")
            board = resource.get("board-name")

            # Ambil serial number dari routerboard
            rb = api.get_resource('/system/routerboard').get()[0]
            serial = rb.get("serial-number")

            # Ambil daftar IP address (untuk main interface)
            ip_addrs = api.get_resource('/ip/address').get()
            dev_ip = self.host
            matched_iface = None

            # Cari interface dengan IP yg sama
            for ipr in ip_addrs:
                addr = ipr.get("address", "")
                if dev_ip in addr:
                    matched_iface = ipr.get("interface")
                    break

            # Fallback interface
            interfaces = api.get_resource('/interface/ethernet').get()
            if not matched_iface and interfaces:
                matched_iface = interfaces[0].get("name")

            # Ambil mac address
            mac = None
            for iface in interfaces:
                if iface.get("name") == matched_iface:
                    mac = iface.get("mac-address")
                    break

            return {
                "identity": identity,
                "version": version,
                # "board-name": "RouterOS",
                "board-name": board,
                # "serial-number": "h1h1h1h1",
                "serial-number": serial,
                "vendor": "MikroTik",
                "mac-address": mac,
                "main_interface": matched_iface,
            }

        finally:
            pool.disconnect()