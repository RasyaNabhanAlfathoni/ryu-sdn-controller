class RouterOSNeighborDriver:
    name = "routerosapi_neighbor"

    def __init__(self, core_driver):
        self.core = core_driver

    # =========================================================
    # GET NEIGHBOR LIST (v6 & v7 compatible)
    # =========================================================
    def get_neighbors(self, p=None, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource("/ip/neighbor")
            neighbors = res.get()

            parsed = []
            for n in neighbors:
                item = {
                    "interface": n.get("interface"),
                    "ip_address": n.get("address"),
                    "ipv6_address": n.get("ipv6-address"),
                    "mac_address": n.get("mac-address"),
                    "identity": n.get("identity"),
                    "platform": n.get("platform"),
                    "version": n.get("version"),
                    "board_name": n.get("board-name"),
                    "interface_name": n.get("interface-name"),
                    "software_id": n.get("software-id"),
                    "uptime": n.get("uptime"),
                    "age": n.get("age"),
                    "unpacking": n.get("unpacking")
                }

                # RouterOS v7 only: discovered-by
                if "discovered-by" in n and n["discovered-by"]:
                    item["discovered_by"] = [
                        x.strip() for x in n["discovered-by"].split(",")
                    ]

                parsed.append(item)

            logger(f"Found {len(parsed)} neighbors.")
            return parsed

        except Exception as e:
            logger(f"Failed to get neighbors: {str(e)}")
            raise
        finally:
            pool.disconnect()

    # =========================================================
    # GET DISCOVERY SETTINGS (global)
    # =========================================================
    def get_discovery_settings(self, p=None, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource("/ip/neighbor/discovery-settings")
            data = res.get()[0]

            result = {
                "protocols": data.get("protocol", "").split(",")
            }
            logger(f"Discovery settings: {result}")
            return result
        except Exception as e:
            logger(f"Failed to get discovery settings: {str(e)}")
            raise
        finally:
            pool.disconnect()

    # =========================================================
    # EDIT DISCOVERY SETTINGS (enable/disable protocol)
    # =========================================================
    def edit_discovery_settings(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource("/ip/neighbor/discovery-settings")
            update = {}

            # Only modify protocol field
            if "protocols" in p:
                if isinstance(p["protocols"], list):
                    update["protocol"] = ",".join(p["protocols"])
                elif isinstance(p["protocols"], str):
                    update["protocol"] = p["protocols"]
                else:
                    raise Exception("Invalid 'protocols' format")

            if not update:
                raise Exception("No fields to update in discovery settings.")

            res.set(**update)
            logger(f"Updated discovery settings: {update}")
            return update

        except Exception as e:
            logger(f"Edit discovery settings failed: {str(e)}")
            raise
        finally:
            pool.disconnect()
