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
            payload = {
                "dst-address": str(p["dst-address"])
            }

            fields = {
                "gateway": "gateway",
                "check-gateway": "check-gateway",
                "type": "type",
                "distance": "distance",
                "scope": "scope",
                "target-scope": "target-scope",
                "routing-mark": "routing-mark",
                "pref-src": "pref-src",
                "vrf-interface": "vrf-interface",
                "comment": "comment"
            }

            for key, mik in fields.items():
                if key in p and p[key] not in ("", None):
                    payload[mik] = str(p[key])

            if p.get("blackhole") is True:
                payload["type"] = "blackhole"

            api.get_resource('/ip/route').add(**payload)
            logger(f"Added route {payload['dst-address']}")
        finally:
            pool.disconnect()

    # ======================================================
    #                     EDIT ROUTE (FORMAT LU)
    # ======================================================
    def edit_route(self, p, logger=print):
        pool, api = self._api()
        try:
            update = {".id": str(p["id"])}

            fields = {
                "dst-address": "dst-address",
                "gateway": "gateway",
                "check-gateway": "check-gateway",
                "type": "type",
                "distance": "distance",
                "scope": "scope",
                "target-scope": "target-scope",
                "routing-mark": "routing-mark",
                "pref-src": "pref-src",
                "vrf-interface": "vrf-interface",
                "comment": "comment"
            }

            for key, mik in fields.items():
                if key in p and p[key] not in ("", None):
                    update[mik] = str(p[key])

            api.get_resource('/ip/route').set(**update)
            logger(f"Edited route id={p['id']}")
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