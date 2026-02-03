from routeros_api import RouterOsApiPool

class RouterOSNetwatchDriver:

    def __init__(self, core_driver):
        self.core = core_driver
        self.dev = core_driver.dev

    def _api(self):
        pool = RouterOsApiPool(
            host=self.dev["ip"],
            username=self.dev["username"],
            password=self.dev["password"],
            plaintext_login=True
        )
        return pool, pool.get_api()

    # VERSION DETECTOR
    def _is_v7(self, api):
        ver = api.get_resource("/system/resource").get()
        if not ver:
            return False
        version = ver[0].get("version", "6.0")
        major = int(version.split(".")[0])
        return major >= 7

    # PAYLOAD BUILDER
    def _build_v6_payload(self, p):
        payload = {}
        if "host" in p:
            payload["host"] = p["host"]
        if "interval" in p:
            payload["interval"] = p["interval"]
        if "timeout" in p:
            payload["timeout"] = p["timeout"]
        if "up" in p:
            payload["up-script"] = p["up"]
        if "down" in p:
            payload["down-script"] = p["down"]
        if "comment" in p:
            payload["comment"] = p["comment"]
        return payload

    def _build_v7_payload(self, p):
        payload = {}
        mapping = {
            "name": "name",
            "host": "host",
            "type": "type",
            "src_address": "src-address",
            "interval": "interval",
            "timeout": "timeout",
            "start_delay": "start-delay",
            "startup_delay": "startup-delay",
            "up": "up-script",
            "down": "down-script",
            "test": "test-script",
            "comment": "comment"
        }

        for k, mk in mapping.items():
            if k in p:
                payload[mk] = p[k]

        return payload

    def netwatch_add(self, p, logger=print):
        pool, api = self._api()
        try:
            is_v7 = self._is_v7(api)
            r = api.get_resource("/tool/netwatch")

            payload = self._build_v7_payload(p) if is_v7 else self._build_v6_payload(p)
            r.add(**payload)
            logger(f"Added netwatch entry")
        finally:
            pool.disconnect()

    def netwatch_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: netwatch.edit requires id")
                return

            is_v7 = self._is_v7(api)
            payload = self._build_v7_payload(p) if is_v7 else self._build_v6_payload(p)
            payload["id"] = p["id"]

            api.get_resource("/tool/netwatch").set(**payload)
            logger(f"Edited netwatch entry {p['id']}")
        finally:
            pool.disconnect()

    def netwatch_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: netwatch.delete requires id")
                return

            api.get_resource("/tool/netwatch").remove(id=p["id"])
            logger(f"Deleted netwatch entry {p['id']}")
        finally:
            pool.disconnect()

    def netwatch_enable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: netwatch.enable requires id")
                return

            api.get_resource("/tool/netwatch").call("enable", {"id": p["id"]})
            logger(f"Enabled netwatch {p['id']}")
        finally:
            pool.disconnect()

    def netwatch_disable(self, p, logger=print):
        pool, api = self._api()
        try:
            if "id" not in p:
                logger("ERROR: netwatch.disable requires id")
                return

            api.get_resource("/tool/netwatch").call("disable", {"id": p["id"]})
            logger(f"Disabled netwatch {p['id']}")
        finally:
            pool.disconnect()

    def netwatch_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            is_v7 = self._is_v7(api)
            data = api.get_resource("/tool/netwatch").get()

            out = []
            for item in data:
                x = dict(item)

                # map creation-time if available
                if ".creation-time" in item:
                    x["creation-time"] = item[".creation-time"]

                # migrate boolean status fields
                if "status" in item:
                    x["status"] = item["status"]

                if is_v7:
                    # ensure v7 fields exist
                    x.setdefault("done-tests", item.get("done-tests", "0"))
                    x.setdefault("failed-tests", item.get("failed-tests", "0"))

                out.append(x)

            logger("netwatch.list completed")
            return out

        finally:
            pool.disconnect()