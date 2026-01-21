class RouterOSInterfaceDriver:
    name = "routerosapi_interface"

    def __init__(self, core_driver):
        """
        core_driver = instance dari RouterOSApiDriver
        """
        self.core = core_driver

    def add_interface(self, p, logger=print):
        """
        Add logical interface (vlan, bridge, vrrp, bonding, dll).

        Minimal contract:
        {
            "type": "vlan|bridge|vrrp|bonding|..."
            "name": "interface-name",
            ... other params based on type ...
        }
        """
        pool, api = self.core.get_api()
        try:
            iface_type = p.get("type")
            if not iface_type:
                raise Exception("Missing interface type")

                resource_map = {
                    "vlan": "/interface/vlan",
                    "bridge": "/interface/bridge",
                    "bonding": "/interface/bonding",
                    "vrrp": "/interface/vrrp",
                    "vxlan": "/interface/vxlan",
                    "veth": "/interface/veth",
                    "eoip": "/interface/eoip",
                    "gre": "/interface/gre",
                    "wireguard": "/interface/wireguard",
                    "macsec": "/interface/macsec",
                    "pppoe-client": "/interface/pppoe-client",
                    "pppoe-server": "/interface/pppoe-server",
                    "l2tp-client": "/interface/l2tp-client",
                    "l2tp-server": "/interface/l2tp-server",
                    "sstp-client": "/interface/sstp-client",
                    "sstp-server": "/interface/sstp-server",
                    "pptp-client": "/interface/pptp-client",
                    "pptp-server": "/interface/pptp-server",
                }

            if iface_type not in resource_map:
                raise Exception(f"Unsupported interface type: {iface_type}")

            res = api.get_resource(resource_map[iface_type])

            payload = {k: v for k, v in p.items() if k != "type"}

            if "name" not in payload:
                raise Exception("Interface name is required")

            res.add(**payload)

            logger(f" Added {iface_type} interface: {payload.get('name')}")

            return {
                "type": iface_type,
                "name": payload.get("name"),
                "status": "created"
            }

        except Exception as e:
            logger(f" Add interface failed: {str(e)}")
            raise Exception(f"Failed to add interface: {str(e)}")

        finally:
            pool.disconnect()


    def edit_interface(self, p, logger=print):
        """
        Ganti nama interface.
        {
            "old_name": "ether3",
            "new_name": "LAN-Core"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/interface')
            recs = res.get(name=p["old_name"])
            if not recs:
                raise Exception(f"Interface {p['old_name']} not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            res.set(numbers=record_id, name=p["new_name"])
            logger(f" Renamed interface {p['old_name']} -> {p['new_name']}")

        except Exception as e:
            logger(f" Edit interface failed: {str(e)}")
            raise Exception(f"Failed to edit interface: {str(e)}")

        finally:
            pool.disconnect()

    def disable_interface(self, p, logger=print):
        """
        Disable interface.
        { "name": "ether3" }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/interface')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"Interface {p['name']} not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            res.set(numbers=record_id, disabled="yes")
            logger(f" Disabled interface {p['name']}")

        except Exception as e:
            logger(f" Disable failed: {str(e)}")
            raise Exception(f"Failed to disable interface: {str(e)}")

        finally:
            pool.disconnect()

    def enable_interface(self, p, logger=print):
        """
        Enable interface.
        { "name": "ether3" }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/interface')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"Interface {p['name']} not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            res.set(numbers=record_id, disabled="no")
            logger(f" Enabled interface {p['name']}")

        except Exception as e:
            logger(f" Enable failed: {str(e)}")
            raise Exception(f"Failed to enable interface: {str(e)}")

        finally:
            pool.disconnect()

    def comment_interface(self, p, logger=print):
        """
        Tambahkan / ubah comment interface.
        {
            "name": "ether3",
            "comment": "Uplink ke ISP"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/interface')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"Interface {p['name']} not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            res.set(numbers=record_id, comment=p["comment"])
            logger(f" Updated comment on {p['name']}: {p['comment']}")

        except Exception as e:
            logger(f" Comment failed: {str(e)}")
            raise Exception(f"Failed to comment interface: {str(e)}")

        finally:
            pool.disconnect()

    def cable_test(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            # 🔍 Cari interface
            res = api.get_resource('/interface/ethernet')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"Ethernet interface {p['name']} not found")

            record_id = recs[0].get(".id") or recs[0].get("id")

            # ⚡ Jalankan cable-test pakai koneksi mentah
            logger(f"🧩 Running cable-test on interface {p['name']} (id: {record_id})")

            conn = pool.get_connection()
            conn.write_sentence(['/interface/ethernet/cable-test', f'=numbers={record_id}'])

            parsed = {}
            while True:
                resp = conn.read_sentence()
                if not resp:
                    break

                if resp[0] == '!re':
                    for item in resp[1:]:
                        if item.startswith('='):
                            k, v = item[1:].split('=', 1)
                            parsed[k] = v

                if resp[0] == '!done':
                    break

            logger(f"📡 Cable test result: {parsed}")

            return {
                "interface": p["name"],
                "result": parsed
            }

        except Exception as e:
            logger(f"❌ Cable test failed: {str(e)}")
            raise Exception(f"Failed to run cable test: {str(e)}")

        finally:
            pool.disconnect()
