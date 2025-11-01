class RouterOSIpPoolDriver:
    name = "routerosapi_ip_pool"

    def __init__(self, core_driver):
        self.core = core_driver

    def add_pool(self, p, logger=print):
        """
        Contoh payload:
        {
            "name": "POOL_LAN",
            "ranges": [
                "192.168.10.2-192.168.10.50",
                "192.168.10.100-192.168.10.200"
            ],
            "next_pool": "POOL_BACKUP",
            "comment": "DHCP LAN range"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/pool')

            existing = res.get(name=p["name"])
            if existing:
                logger(f"Pool '{p['name']}' sudah ada, skip add.")
                return

            # Gabungkan multiple ranges jadi string CSV
            ranges = (
                ",".join(p["ranges"])
                if isinstance(p["ranges"], list)
                else p["ranges"]
            )

            payload = {
                "name": p["name"],
                "ranges": ranges
            }
            if "next_pool" in p:
                payload["next-pool"] = p["next_pool"]
            if "comment" in p:
                payload["comment"] = p["comment"]

            res.add(**payload)
            logger(f"Added IP pool '{p['name']}' with ranges {ranges}")

        except Exception as e:
            logger(f"Add pool failed: {str(e)}")
            raise Exception(f"Failed to add pool: {str(e)}")
        finally:
            pool.disconnect()

    def edit_pool(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/pool')

            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"Pool '{p['name']}' not found")

            record = recs[0]
            record_id = record.get(".id") or record.get("id")

            update_data = {}
            if "ranges" in p:
                update_data["ranges"] = (
                    ",".join(p["ranges"])
                    if isinstance(p["ranges"], list)
                    else p["ranges"]
                )
            if "comment" in p:
                update_data["comment"] = p["comment"]
            if "new_name" in p:
                update_data["name"] = p["new_name"]
            if "next_pool" in p:
                update_data["next-pool"] = p["next_pool"]

            res.set(**{"numbers": record_id, **update_data})
            logger(f"Updated pool '{p['name']}' successfully")

        except Exception as e:
            logger(f"Edit failed: {str(e)}")
            raise Exception(f"Failed to edit pool: {str(e)}")
        finally:
            pool.disconnect()

    def delete_pool(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/pool')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"Pool '{p['name']}' not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            res.remove(numbers=record_id)
            logger(f"Deleted pool '{p['name']}'")

        except Exception as e:
            logger(f"Delete failed: {str(e)}")
            raise Exception(f"Failed to delete pool: {str(e)}")
        finally:
            pool.disconnect()

    def comment_pool(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/pool')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"Pool '{p['name']}' not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            res.set(numbers=record_id, comment=p["comment"])
            logger(f"Updated comment for pool '{p['name']}': {p['comment']}")

        except Exception as e:
            logger(f"Comment update failed: {str(e)}")
            raise Exception(f"Failed to update pool comment: {str(e)}")
        finally:
            pool.disconnect()