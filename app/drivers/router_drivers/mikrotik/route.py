from librouteros import connect
from routeros_api import RouterOsApiPool


class RouterOSRouteDriver:
    def __init__(self, dev):
        # SUPPORT input dev = dict atau RouterOSApiDriver
        self.dev = dev.dev if hasattr(dev, "dev") else dev

    # =============== READ ONLY (LIBROUTEROS) ===============
    def _libapi(self):
        return connect(
            host=self.dev["ip"],
            username=self.dev["username"],
            password=self.dev["password"],
            port=8728,
            use_ssl=False
        )

    # =============== WRITE (routeros_api) ===============
    def _api(self):
        pool = RouterOsApiPool(
            host=self.dev["ip"],
            username=self.dev["username"],
            password=self.dev["password"],
            plaintext_login=True
        )
        return pool, pool.get_api()

    # ======================================================
    #                     LIST ROUTES
    # ======================================================
    def list_routes(self, p, logger=print):
        api = self._libapi()
        routes = api('/ip/route/print')

        cleaned = []
        for r in routes:
            cleaned.append(self.parse_route(r))

        return cleaned

    # ======================================================
    #                     PARSE ROUTE (PUNYA LU)
    # ======================================================
    def parse_route(self, r):
        def t(x):
            # normalisasi ke boolean
            return x is True or x == "true" or x == "yes" or x == "1"

        flags = ""
        if t(r.get("active")): flags += "A"
        if t(r.get("dynamic")): flags += "D"
        if t(r.get("static")): flags += "S"
        if t(r.get("connect")): flags += "C"
        if t(r.get("blackhole")): flags += "B"
        if t(r.get("unreachable")): flags += "U"
        if t(r.get("prohibit")): flags += "P"
        if t(r.get("hw-offloaded")): flags += "H"

        return {
            "id": r.get(".id"),
            "flags": flags,
            "dst_address": r.get("dst-address"),
            "gateway": r.get("gateway"),
            "distance": r.get("distance"),
            "scope": r.get("scope"),
            "target_scope": r.get("target-scope"),
            "type": r.get("type"),
            "routing_mark": r.get("routing-mark"),
            "pref_source": r.get("pref-src"),
            "vrf_interface": r.get("vrf-interface"),
            "comment": r.get("comment"),
            "disabled": t(r.get("disabled")),
        }


    # ======================================================
    #                     ADD ROUTE (FORMAT LU)
    # ======================================================
    def add_route(self, p, logger=print):
        pool, api = self._api()
        try:
            payload = {"dst-address": p["dst_address"]}

            fields = {
                "gateway": "gateway",
                "check_gateway": "check-gateway",
                "type": "type",
                "distance": "distance",
                "scope": "scope",
                "target_scope": "target-scope",
                "routing_mark": "routing-mark",
                "pref_source": "pref-src",
                "vrf_interface": "vrf-interface",
                "comment": "comment"
            }

            for key, mik in fields.items():
                if key in p and p[key] not in ("", None):
                    payload[mik] = p[key]

            if p.get("blackhole", False):
                payload["type"] = "blackhole"

            api.get_resource('/ip/route').add(**payload)
            logger(f"Added new route: {p['dst_address']}")
        finally:
            pool.disconnect()

    # ======================================================
    #                     EDIT ROUTE (FORMAT LU)
    # ======================================================
    def edit_route(self, p, logger=print):
        pool, api = self._api()
        try:
            rid = p["id"]
            update = {".id": rid}

            fields = {
                "dst_address": "dst-address",
                "gateway": "gateway",
                "check_gateway": "check-gateway",
                "type": "type",
                "distance": "distance",
                "scope": "scope",
                "target_scope": "target-scope",
                "routing_mark": "routing-mark",
                "pref_source": "pref-src",
                "vrf_interface": "vrf-interface",
                "comment": "comment"
            }

            for key, mik in fields.items():
                if key in p:
                    update[mik] = p[key]

            api.get_resource('/ip/route').set(**update)
            logger(f"Edited route id={rid}")
        finally:
            pool.disconnect()

    # ======================================================
    #                     DELETE ROUTE
    # ======================================================
    def delete_route(self, p, logger=print):
        pool, api = self._api()
        try:
            api.get_resource('/ip/route').remove(**{".id": p["id"]})
            logger(f"Removed route id={p['id']}")
        finally:
            pool.disconnect()

    # ======================================================
    #                     DISABLE ROUTE
    # ======================================================
    def disable_route(self, p, logger=print):
        pool, api = self._api()
        try:
            api.get_resource('/ip/route').set(**{".id": p["id"], "disabled": "yes"})
            logger(f"Disabled route id={p['id']}")
        finally:
            pool.disconnect()

    # ======================================================
    #                     ENABLE ROUTE
    # ======================================================
    def enable_route(self, p, logger=print):
        pool, api = self._api()
        try:
            api.get_resource('/ip/route').set(**{".id": p["id"], "disabled": "no"})
            logger(f"Enabled route id={p['id']}")
        finally:
            pool.disconnect()