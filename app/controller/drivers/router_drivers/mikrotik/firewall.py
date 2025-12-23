from routeros_api import RouterOsApiPool

class RouterOSFirewallDriver:
    name = "routerosapi_firewall"

    def __init__(self, core_driver):
        self.core = core_driver
        self.dev = core_driver.dev

    # ============================
    # API CONNECTOR
    # ============================
    def _api(self):
        pool = RouterOsApiPool(
            host=self.dev["ip"],
            username=self.dev["username"],
            password=self.dev["password"],
            plaintext_login=True
        )
        return pool, pool.get_api()

    # ============================
    # GENERIC HELPERS
    # ============================
    def _snake_to_mikrotik(self, name: str):
        return name.replace("_", "-")

    def _normalize_value(self, value):
        if value is None:
            return None
        if isinstance(value, bool):
            return "yes" if value else "no"
        if isinstance(value, list):
            return ",".join(str(v) for v in value)
        return str(value)

    def _build_rule_payload(self, p: dict):
        payload = {}

        for key, value in p.items():
            if key == "id":      # id tidak dikirim ke RouterOS
                continue

            mk = self._snake_to_mikrotik(key)
            norm = self._normalize_value(value)

            if norm not in (None, ""):
                payload[mk] = norm

        return payload

    # ============================
    # FILTER RULES
    # ============================
    def filter_add(self, p, logger=print):
        pool, api = self._api()
        try:
            pl = self._build_rule_payload(p)
            api.get_resource("/ip/firewall/filter").add(**pl)
            logger("Added firewall filter rule")
        finally:
            pool.disconnect()

    def filter_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: filter.edit requires id")
                return

            pl = self._build_rule_payload(p)
            pl["id"] = p["id"]

            api.get_resource("/ip/firewall/filter").set(**pl)
            logger(f"Edited filter rule {p['id']}")
        finally:
            pool.disconnect()

    def filter_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: filter.delete requires id")
                return

            api.get_resource("/ip/firewall/filter").remove(id=p["id"])
            logger(f"Deleted filter rule {p['id']}")
        finally:
            pool.disconnect()

    def filter_enable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: filter.enable requires id")
                return
            api.get_resource("/ip/firewall/filter").set(id=p["id"], disabled="no")
            logger(f"Enabled filter rule {p['id']}")
        finally:
            pool.disconnect()

    def filter_disable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: filter.disable requires id")
                return
            api.get_resource("/ip/firewall/filter").set(id=p["id"], disabled="yes")
            logger(f"Disabled filter rule {p['id']}")
        finally:
            pool.disconnect()

    def filter_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource("/ip/firewall/filter").get()
        finally:
            pool.disconnect()

    # ============================
    # NAT SECTION
    # ============================
    def nat_add(self, p, logger=print):
        pool, api = self._api()
        try:
            pl = self._build_rule_payload(p)
            api.get_resource("/ip/firewall/nat").add(**pl)
            logger("Added NAT rule")
        finally:
            pool.disconnect()

    def nat_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: nat.edit requires id")
                return

            pl = self._build_rule_payload(p)
            pl["id"] = p["id"]

            api.get_resource("/ip/firewall/nat").set(**pl)
            logger(f"Edited NAT rule {p['id']}")
        finally:
            pool.disconnect()

    def nat_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: nat.delete requires id")
                return

            api.get_resource("/ip/firewall/nat").remove(id=p["id"])
            logger(f"Deleted NAT rule {p['id']}")
        finally:
            pool.disconnect()

    def nat_enable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: nat.enable requires id")
                return
            api.get_resource("/ip/firewall/nat").set(id=p["id"], disabled="no")
            logger(f"Enabled NAT rule {p['id']}")
        finally:
            pool.disconnect()

    def nat_disable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: nat.disable requires id")
                return
            api.get_resource("/ip/firewall/nat").set(id=p["id"], disabled="yes")
            logger(f"Disabled NAT rule {p['id']}")
        finally:
            pool.disconnect()

    def nat_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource("/ip/firewall/nat").get()
        finally:
            pool.disconnect()

    # ============================
    # MANGLE SECTION (NEW)
    # ============================
    def mangle_add(self, p, logger=print):
        pool, api = self._api()
        try:
            pl = self._build_rule_payload(p)
            api.get_resource("/ip/firewall/mangle").add(**pl)
            logger("Added Mangle rule")
        finally:
            pool.disconnect()

    def mangle_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: mangle.edit requires id")
                return

            pl = self._build_rule_payload(p)
            pl["id"] = p["id"]

            api.get_resource("/ip/firewall/mangle").set(**pl)
            logger(f"Edited Mangle rule {p['id']}")
        finally:
            pool.disconnect()

    def mangle_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: mangle.delete requires id")
                return

            api.get_resource("/ip/firewall/mangle").remove(id=p["id"])
            logger(f"Deleted Mangle rule {p['id']}")
        finally:
            pool.disconnect()

    def mangle_enable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: mangle.enable requires id")
                return

            api.get_resource("/ip/firewall/mangle").set(id=p["id"], disabled="no")
            logger(f"Enabled Mangle rule {p['id']}")
        finally:
            pool.disconnect()

    def mangle_disable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: mangle.disable requires id")
                return

            api.get_resource("/ip/firewall/mangle").set(id=p["id"], disabled="yes")
            logger(f"Disabled Mangle rule {p['id']}")
        finally:
            pool.disconnect()

    def mangle_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource("/ip/firewall/mangle").get()
        finally:
            pool.disconnect()

    # ============================
    # RAW SECTION (NEW)
    # ============================
    def raw_add(self, p, logger=print):
        pool, api = self._api()
        try:
            pl = self._build_rule_payload(p)
            api.get_resource("/ip/firewall/raw").add(**pl)
            logger("Added RAW rule")
        finally:
            pool.disconnect()

    def raw_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: raw.edit requires id")
                return

            pl = self._build_rule_payload(p)
            pl["id"] = p["id"]

            api.get_resource("/ip/firewall/raw").set(**pl)
            logger(f"Edited RAW rule {p['id']}")
        finally:
            pool.disconnect()

    def raw_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: raw.delete requires id")
                return

            api.get_resource("/ip/firewall/raw").remove(id=p["id"])
            logger(f"Deleted RAW rule {p['id']}")
        finally:
            pool.disconnect()

    def raw_enable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: raw.enable requires id")
                return

            api.get_resource("/ip/firewall/raw").set(id=p["id"], disabled="no")
            logger(f"Enabled RAW rule {p['id']}")
        finally:
            pool.disconnect()

    def raw_disable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: raw.disable requires id")
                return

            api.get_resource("/ip/firewall/raw").set(id=p["id"], disabled="yes")
            logger(f"Disabled RAW rule {p['id']}")
        finally:
            pool.disconnect()

    def raw_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource("/ip/firewall/raw").get()
        finally:
            pool.disconnect()

    # ============================
    # SERVICE PORTS SECTION
    # ============================
    def _get_service_port(self, api, name):
        """Service-port punya name unik, jadi get by name."""
        items = api.get_resource("/ip/firewall/service-port").get(name=name)
        return items[0] if items else None

    def service_port_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource("/ip/firewall/service-port").get()
        finally:
            pool.disconnect()

    def service_port_enable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "name" not in p:
                logger("ERROR: service-port.enable requires name")
                return

            sp = self._get_service_port(api, p["name"])
            if not sp:
                logger(f"Service-port '{p['name']}' not found")
                return

            api.get_resource("/ip/firewall/service-port").set(
                id=sp["id"], disabled="no"
            )
            logger(f"Enabled service-port {p['name']}")
        finally:
            pool.disconnect()

    def service_port_disable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "name" not in p:
                logger("ERROR: service-port.disable requires name")
                return

            sp = self._get_service_port(api, p["name"])
            if not sp:
                logger(f"Service-port '{p['name']}' not found")
                return

            api.get_resource("/ip/firewall/service-port").set(
                id=sp["id"], disabled="yes"
            )
            logger(f"Disabled service-port {p['name']}")
        finally:
            pool.disconnect()

    def service_port_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            if "name" not in p:
                logger("ERROR: service-port.edit requires name")
                return

            sp = self._get_service_port(api, p["name"])
            if not sp:
                logger(f"Service-port '{p['name']}' not found")
                return

            payload = {}

            # ports always editable (list/string)
            if "ports" in p:
                payload["ports"] = self._normalize_value(p["ports"])

            # SIP ONLY FIELDS
            if p["name"] == "sip":
                if "sip_direct_media" in p:
                    payload["sip-direct-media"] = self._normalize_value(
                        p["sip_direct_media"]
                    )
                if "sip_timeout" in p:
                    payload["sip-timeout"] = self._normalize_value(
                        p["sip_timeout"]
                    )

            payload["id"] = sp["id"]

            api.get_resource("/ip/firewall/service-port").set(**payload)
            logger(f"Edited service-port {p['name']}")
        finally:
            pool.disconnect()

    # ============================
    # CONNECTIONS SECTION
    # ============================

    def _build_connection_flags(self, item):
        """Generate Winbox-style connection flags"""
        flags = []

        # mapping boolean fields direct from RouterOS API
        flag_map = {
            "expected": "expected",
            "seen-reply": "seen reply",
            "assured": "assured",
            "confirmed": "confirmed",
            "dying": "dying",
            "fasttrack": "fasttrack",
            "srcnat": "srcnat",
            "dstnat": "dstnat"
        }

        for key, label in flag_map.items():
            if item.get(key) == "true" or item.get(key) == "yes":
                flags.append(label)

        return flags

    def conn_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            data = api.get_resource("/ip/firewall/connection").get()

            enriched = []
            for item in data:
                i = dict(item)
                i["flags"] = self._build_connection_flags(item)
                enriched.append(i)

            logger("fw.conn.list completed successfully")
            return enriched
        finally:
            pool.disconnect()

    def conn_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: conn.delete requires id")
                return

            api.get_resource("/ip/firewall/connection").remove(id=p["id"])
            logger(f"Deleted connection {p['id']}")
        finally:
            pool.disconnect()

    # ============================
    # ADDRESS-LIST SECTION
    # ============================

    def addrlist_add(self, p, logger=print):
        pool, api = self._api()
        try:
            addresses = p.get("address")
            list_name = p.get("name")

            if not list_name:
                logger("ERROR: addrlist.add requires name")
                return

            # Kalau address adalah list → loop and add one-by-one
            if isinstance(addresses, list):
                for addr in addresses:
                    payload = {
                        "list": list_name,
                        "address": addr
                    }

                    if "timeout" in p:
                        payload["timeout"] = p["timeout"]

                    if "comment" in p:
                        payload["comment"] = p["comment"]

                    api.get_resource("/ip/firewall/address-list").add(**payload)
                    logger(f"Added address-list entry: {list_name} -> {addr}")

            else:
                # Single-value address
                payload = {
                    "list": list_name,
                    "address": addresses
                }

                if "timeout" in p:
                    payload["timeout"] = p["timeout"]

                if "comment" in p:
                    payload["comment"] = p["comment"]

                api.get_resource("/ip/firewall/address-list").add(**payload)
                logger(f"Added address-list entry: {list_name} -> {addresses}")

        finally:
            pool.disconnect()

    def addrlist_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: addrlist.edit requires id")
                return

            payload = {}

            # Rename list name
            if "name" in p:
                payload["list"] = p["name"]

            # address
            if "address" in p:
                if isinstance(p["address"], list):
                    payload["address"] = ",".join(p["address"])
                else:
                    payload["address"] = p["address"]

            # timeout
            if "timeout" in p:
                payload["timeout"] = p["timeout"]

            # comment
            if "comment" in p:
                payload["comment"] = p["comment"]

            payload["id"] = p["id"]

            api.get_resource("/ip/firewall/address-list").set(**payload)
            logger(f"Edited address-list entry {p['id']}")
        finally:
            pool.disconnect()


    def addrlist_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: addrlist.delete requires id")
                return

            api.get_resource("/ip/firewall/address-list").remove(id=p["id"])
            logger(f"Deleted address-list entry {p['id']}")
        finally:
            pool.disconnect()


    def addrlist_enable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: addrlist.enable requires id")
                return

            api.get_resource("/ip/firewall/address-list").set(id=p["id"], disabled="no")
            logger(f"Enabled address-list entry {p['id']}")
        finally:
            pool.disconnect()


    def addrlist_disable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: addrlist.disable requires id")
                return

            api.get_resource("/ip/firewall/address-list").set(id=p["id"], disabled="yes")
            logger(f"Disabled address-list entry {p['id']}")
        finally:
            pool.disconnect()


    def addrlist_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            data = api.get_resource("/ip/firewall/address-list").get()

            # include creation-time (RouterOS gives .creation-time)
            result = []
            for item in data:
                x = dict(item)
                if ".creation-time" in item:
                    x["creation-time"] = item[".creation-time"]
                result.append(x)

            return result
        finally:
            pool.disconnect()

    # ============================
    # LAYER 7 PROTOCOLS
    # ============================

    def layer7_add(self, p, logger=print):
        pool, api = self._api()
        try:
            payload = {}

            if "name" in p:
                payload["name"] = p["name"]

            if "regexp" in p:
                payload["regexp"] = p["regexp"]

            api.get_resource("/ip/firewall/layer7-protocol").add(**payload)
            logger(f"Added Layer7 protocol {p.get('name')}")
        finally:
            pool.disconnect()

    def layer7_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: l7.edit requires id")
                return

            payload = {"id": p["id"]}

            if "name" in p:
                payload["name"] = p["name"]

            if "regexp" in p:
                payload["regexp"] = p["regexp"]

            if "comment" in p:
                payload["comment"] = p["comment"]

            api.get_resource("/ip/firewall/layer7-protocol").set(**payload)
            logger(f"Edited Layer7 protocol {p['id']}")
        finally:
            pool.disconnect()

    def layer7_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: l7.delete requires id")
                return

            api.get_resource("/ip/firewall/layer7-protocol").remove(id=p["id"])
            logger(f"Deleted Layer7 protocol {p['id']}")
        finally:
            pool.disconnect()

    def layer7_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            data = api.get_resource("/ip/firewall/layer7-protocol").get()
            return [dict(i) for i in data]
        finally:
            pool.disconnect()