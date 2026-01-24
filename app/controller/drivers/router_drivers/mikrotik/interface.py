class RouterOSInterfaceDriver:
    name = "routerosapi_interface"

    def __init__(self, core_driver):
        """
        core_driver = instance dari RouterOSApiDriver
        """
        self.core = core_driver

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

    def list_interface(self, p=None, logger=print):
        """
        Return:
        [
            {
                "id": "*1",
                "name": "ether1",
                "type": "ether",
                "mtu": "1500",
                "mac_address": "DC:2C:6E:XX:XX:XX",
                "running": "true",
                "disabled": "false",
                "comment": "Uplink ISP"
            }
        ]
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/interface')
            data = res.get()

            out = []
            for item in data:
                row = dict(item)

                # normalize ID
                row["id"] = item.get(".id") or item.get("id")

                # normalize fields
                row["name"] = item.get("name")
                row["type"] = item.get("type")
                row["mtu"] = item.get("mtu")
                row["mac_address"] = item.get("mac-address")
                row["running"] = item.get("running")
                row["disabled"] = item.get("disabled")
                row["comment"] = item.get("comment")

                out.append(row)

            logger("interface.list completed")
            return out

        finally:
            pool.disconnect()