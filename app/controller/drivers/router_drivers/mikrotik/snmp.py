class RouterOSSNMPDriver:
    """
    SNMP Configuration & Community Management for MikroTik RouterOS.
    Southbound: routeros_api
    """

    name = "routerosapi_snmp"

    def __init__(self, core_driver):
        self.core = core_driver

    # =====================================================
    # SNMP GLOBAL CONFIG
    # =====================================================
    def get_snmp_config(self, p=None, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/snmp')
            data = res.get()
            if not data:
                raise Exception("No SNMP configuration found.")
            logger("Fetched SNMP global config")
            return data[0]
        except Exception as e:
            logger(f"Get SNMP config failed: {str(e)}")
            raise Exception(f"Failed to fetch SNMP config: {str(e)}")
        finally:
            pool.disconnect()

    def edit_snmp_config(self, p, logger=print):
        """
        Example payload:
        {
            "enabled": "yes",
            "contact": "Network Admin",
            "location": "NOC Room",
            "trap-target": "10.10.10.10",
            "trap-community": "public",
            "trap-version": "2",
            "trap-generators": "interfaces,temp-exception",
            "trap-interfaces": "all",
            "src-address": "9.9.9.1",
            "vrf": "main"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/snmp')
            update = {}

            # SNMP config keys supported by RouterOS v6 & v7
            valid_fields = [
                "enabled", "contact", "location", "trap-target",
                "trap-community", "trap-version",
                "trap-generators", "trap-interfaces",
                "src-address", "vrf"
            ]

            for k in valid_fields:
                if k in p:
                    update[k] = p[k]

            if not update:
                raise Exception("No valid SNMP fields to update")

            res.set(**update)
            logger(f"SNMP configuration updated: {update}")

        except Exception as e:
            logger(f"Edit SNMP config failed: {str(e)}")
            raise Exception(f"Failed to update SNMP config: {str(e)}")
        finally:
            pool.disconnect()

    # =====================================================
    # SNMP COMMUNITY MANAGEMENT
    # =====================================================
    def list_communities(self, p=None, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/snmp/community')
            data = res.get()
            logger(f"Fetched {len(data)} SNMP communities")
            return data
        except Exception as e:
            logger(f"List communities failed: {str(e)}")
            raise Exception(f"Failed to list SNMP communities: {str(e)}")
        finally:
            pool.disconnect()

    def add_community(self, p, logger=print):
        """
        Example payload:
        {
            "name": "monitoring",
            "addresses": "::/0",
            "security": "none",
            "read-access": "yes",
            "write-access": "no",
            "authentication-protocol": "MD5",
            "encryption-protocol": "DES",
            "authentication-password": "1234",
            "encryption-password": "abcd",
            "comment": "Prometheus SNMP community"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/snmp/community')

            if "name" not in p:
                raise Exception("Missing 'name' in payload")

            existing = res.get(name=p["name"])
            if existing:
                logger(f"Community '{p['name']}' already exists. Skipping add.")
                return

            res.add(**p)
            logger(f"Added SNMP community: {p['name']}")
        except Exception as e:
            logger(f"Add community failed: {str(e)}")
            raise Exception(f"Failed to add community: {str(e)}")
        finally:
            pool.disconnect()

    def edit_community(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/snmp/community')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"Community '{p['name']}' not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            update = {k: v for k, v in p.items() if k != "name"}

            res.set(numbers=record_id, **update)
            logger(f"Updated SNMP community '{p['name']}'")

        except Exception as e:
            logger(f"Edit community failed: {str(e)}")
            raise Exception(f"Failed to edit community: {str(e)}")
        finally:
            pool.disconnect()

    def delete_community(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/snmp/community')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"Community '{p['name']}' not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            res.remove(numbers=record_id)
            logger(f"Deleted SNMP community '{p['name']}'")
        except Exception as e:
            logger(f"Delete community failed: {str(e)}")
            raise Exception(f"Failed to delete community: {str(e)}")
        finally:
            pool.disconnect()

    # =====================================================
    # ENABLE / DISABLE COMMUNITY
    # =====================================================
    def enable_community(self, p, logger=print):
        self._set_disabled(p, logger, False)

    def disable_community(self, p, logger=print):
        self._set_disabled(p, logger, True)

    def _set_disabled(self, p, logger, disabled):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/snmp/community')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"Community '{p['name']}' not found")
            record_id = recs[0].get(".id") or recs[0].get("id")

            res.set(numbers=record_id, disabled="yes" if disabled else "no")
            logger(f"Community '{p['name']}' {'disabled' if disabled else 'enabled'}")

        except Exception as e:
            logger(f"Enable/disable failed: {str(e)}")
            raise Exception(f"Failed to change state: {str(e)}")
        finally:
            pool.disconnect()

    # =====================================================
    # COMMENT COMMUNITY
    # =====================================================
    def comment_community(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/snmp/community')
            recs = res.get(name=p["name"])
            if not recs:
                raise Exception(f"Community '{p['name']}' not found")
            record_id = recs[0].get(".id") or recs[0].get("id")

            res.set(numbers=record_id, comment=p["comment"])
            logger(f"Updated comment for community '{p['name']}': {p['comment']}")

        except Exception as e:
            logger(f"Comment failed: {str(e)}")
            raise Exception(f"Failed to comment SNMP community: {str(e)}")
        finally:
            pool.disconnect()