class RouterOSVlanDriver:
    name = "routerosapi_vlan"

    def __init__(self, core_driver):
        """
        core_driver = instance dari RouterOSApiDriver
        """
        self.core = core_driver

    # =========================
    # ADD VLAN
    # =========================
    def add_vlan(self, p, logger=print):
        """
        Tambah VLAN baru.
        Contoh:
        {
            "name": "VLAN100",
            "vlan_id": 100,
            "interface": "ether2",
            "use_service_tag": True
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/interface/vlan')

            payload = {
                "name": p["name"],
                "vlan-id": str(p["vlan_id"]),
                "interface": p["interface"]
            }

            if "comment" in p:
                payload["comment"] = p["comment"]

            if "use_service_tag" in p:
                payload["use-service-tag"] = "yes" if p["use_service_tag"] else "no"

            res.add(**payload)
            logger(f"VLAN {p['name']} (id={p['vlan_id']}) added on {p['interface']}")

        except Exception as e:
            logger(f"Add VLAN failed: {str(e)}")
            raise Exception(f"Failed to add VLAN: {str(e)}")

        finally:
            pool.disconnect()

    # =========================
    # EDIT VLAN
    # =========================
    def edit_vlan(self, p, logger=print):
        """
        Edit VLAN yang sudah ada.
        Contoh:
        {
            "old_name": "VLAN100",
            "name": "VLAN_Office",
            "vlan_id": 200,
            "interface": "ether3",
            "use_service_tag": False
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/interface/vlan')
            recs = res.get(name=p["old_name"])
            if not recs:
                raise Exception(f"VLAN {p['old_name']} not found")

            record_id = recs[0].get(".id") or recs[0].get("id")

            payload = {}
            if "name" in p:
                payload["name"] = p["name"]
            if "vlan_id" in p:
                payload["vlan-id"] = str(p["vlan_id"])
            if "interface" in p:
                payload["interface"] = p["interface"]
            if "comment" in p:
                payload["comment"] = p["comment"]
            if "use_service_tag" in p:
                payload["use-service-tag"] = "yes" if p["use_service_tag"] else "no"

            res.set(numbers=record_id, **payload)
            logger(f"VLAN {p['old_name']} updated")

        except Exception as e:
            logger(f"Edit VLAN failed: {str(e)}")
            raise Exception(f"Failed to edit VLAN: {str(e)}")

        finally:
            pool.disconnect()

    # =========================
    # DELETE VLAN
    # =========================
    def delete_vlan(self, p, logger=print):
        """
        Hapus VLAN.
        Contoh:
        {
            "name": "VLAN100"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/interface/vlan')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"VLAN {p['name']} not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            res.remove(numbers=record_id)
            logger(f"VLAN {p['name']} deleted")

        except Exception as e:
            logger(f"Delete VLAN failed: {str(e)}")
            raise Exception(f"Failed to delete VLAN: {str(e)}")

        finally:
            pool.disconnect()

    # =========================
    # ENABLE VLAN
    # =========================
    def enable_vlan(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/interface/vlan')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"VLAN {p['name']} not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            res.set(numbers=record_id, disabled="no")
            logger(f"VLAN {p['name']} enabled")

        except Exception as e:
            logger(f"Enable VLAN failed: {str(e)}")
            raise Exception(f"Failed to enable VLAN: {str(e)}")

        finally:
            pool.disconnect()

    # =========================
    # DISABLE VLAN
    # =========================
    def disable_vlan(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/interface/vlan')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"VLAN {p['name']} not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            res.set(numbers=record_id, disabled="yes")
            logger(f"VLAN {p['name']} disabled")

        except Exception as e:
            logger(f"Disable VLAN failed: {str(e)}")
            raise Exception(f"Failed to disable VLAN: {str(e)}")

        finally:
            pool.disconnect()

    # =========================
    # COMMENT VLAN
    # =========================
    def comment_vlan(self, p, logger=print):
        """
        Tambahkan atau ubah comment VLAN.
        Contoh:
        {
            "name": "VLAN100",
            "comment": "Office network"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/interface/vlan')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"VLAN {p['name']} not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            res.set(numbers=record_id, comment=p["comment"])
            logger(f"VLAN {p['name']} comment updated: {p['comment']}")

        except Exception as e:
            logger(f"Comment VLAN failed: {str(e)}")
            raise Exception(f"Failed to comment VLAN: {str(e)}")

        finally:
            pool.disconnect()
