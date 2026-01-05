from routeros_api import RouterOsApiPool


class MikroTikAPLoggingDriver:
    name = "mikrotikap_logging"

    def __init__(self, core_driver):
        self.core = core_driver
        self.dev = core_driver.dev

    # API CONNECTOR
    def _api(self):
        pool = RouterOsApiPool(
            host=self.dev["ip"],
            username=self.dev["username"],
            password=self.dev["password"],
            plaintext_login=True
        )
        return pool, pool.get_api()

    # ACTION HELPERS
    def _get_action(self, api, p):
        # Prefer ID
        if "id" in p:
            items = api.get_resource("/system/logging/action").get(id=p["id"])
            if items:
                return items[0]

        # Fallback by name
        if "name" in p:
            items = api.get_resource("/system/logging/action").get(name=p["name"])
            if items:
                return items[0]

        return None

    # ACTION PAYLOAD BUILDER
    def _build_action_payload(self, p):
        payload = {}

        # Name / rename
        if "new_name" in p:
            payload["name"] = p["new_name"]
        elif "name" in p:
            payload["name"] = p["name"]

        # Target selector
        t = p.get("target")
        if t:
            payload["target"] = t

        # MEMORY
        if t == "memory":
            if "lines" in p:
                payload["memory-lines"] = str(p["lines"])
            if "stop_on_full" in p:
                payload["memory-stop-on-full"] = "yes" if p["stop_on_full"] else "no"

        # DISK
        if t == "disk":
            if "file_name" in p:
                payload["disk-file-name"] = p["file_name"]
            if "lines_per_file" in p:
                payload["disk-lines-per-file"] = str(p["lines_per_file"])
            if "file_count" in p:
                payload["disk-file-count"] = str(p["file_count"])
            if "stop_on_full" in p:
                payload["disk-stop-on-full"] = "yes" if p["stop_on_full"] else "no"

        # ECHO
        if t == "echo":
            if "save" in p:
                payload["echo"] = "yes" if p["save"] else "no"

        # EMAIL
        if t == "email":
            if "email" in p:
                payload["email-to"] = p["email"]
            if "start_tls" in p:
                payload["email-start-tls"] = "yes" if p["start_tls"] else "no"

        # REMOTE SYSLOG
        if t == "remote":
            if "remote_address" in p:
                payload["remote"] = p["remote_address"]
            if "remote_port" in p:
                payload["remote-port"] = str(p["remote_port"])
            if "src_address" in p:
                payload["src-address"] = p["src_address"]
            if "bsd_syslog" in p:
                payload["bsd-syslog"] = "yes" if p["bsd_syslog"] else "no"

            if p.get("bsd_syslog", False):
                if "facility" in p:
                    payload["syslog-facility"] = p["facility"]
                if "severity" in p:
                    payload["syslog-severity"] = p["severity"]

        return payload

    # ACTION CRUD
    def action_add(self, p, logger=print):
        pool, api = self._api()
        try:
            api.get_resource("/system/logging/action").add(**self._build_action_payload(p))
            logger(f"Added logging action {p['name']}")
        finally:
            pool.disconnect()

    def action_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            act = self._get_action(api, p)
            if not act:
                logger("Action not found")
                return

            payload = self._build_action_payload(p)
            payload["id"] = act["id"]

            api.get_resource("/system/logging/action").set(**payload)
            logger("Edited logging action")
        finally:
            pool.disconnect()

    def action_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            act = self._get_action(api, p)
            if not act:
                logger("Action not found")
                return

            api.get_resource("/system/logging/action").remove(id=act["id"])
            logger(f"Deleted action")
        finally:
            pool.disconnect()

    def action_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource("/system/logging/action").get()
        finally:
            pool.disconnect()

    # RULE HELPERS
    def _get_rule(self, api, p):
        # Prefer ID
        if "id" in p:
            items = api.get_resource("/system/logging").get(id=p["id"])
            if items:
                return items[0]

        # Fallback by action name
        if "action" in p:
            items = api.get_resource("/system/logging").get(action=p["action"])
            if items:
                return items[0]

        return None

    # RULE PAYLOAD BUILDER
    def _build_rule_payload(self, p):
        payload = {}

        # topics
        if "topics" in p:
            tlist = []
            for t in p["topics"]:
                if isinstance(t, dict):
                    tlist.append(("!" if t.get("not") else "") + t["name"])
                else:
                    tlist.append(t)
            payload["topics"] = ",".join(tlist)

        if "prefix" in p:
            payload["prefix"] = p["prefix"]

        if "action" in p:
            payload["action"] = p["action"]

        return payload

    # RULE CRUD
    def rule_add(self, p, logger=print):
        pool, api = self._api()
        try:
            api.get_resource("/system/logging").add(**self._build_rule_payload(p))
            logger(f"Added logging rule")
        finally:
            pool.disconnect()

    def rule_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            r = self._get_rule(api, p)
            if not r:
                logger("Rule not found")
                return

            payload = self._build_rule_payload(p)
            payload["id"] = r["id"]

            api.get_resource("/system/logging").set(**payload)
            logger("Edited rule")
        finally:
            pool.disconnect()

    def rule_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            r = self._get_rule(api, p)
            if not r:
                logger("Rule not found")
                return
            api.get_resource("/system/logging").remove(id=r["id"])
            logger("Deleted rule")
        finally:
            pool.disconnect()

    def rule_enable(self, p, logger=print):
        pool, api = self._api()
        try:
            r = self._get_rule(api, p)
            if not r:
                logger("Rule not found")
                return
            api.get_resource("/system/logging").set(id=r["id"], disabled="no")
            logger("Enabled rule")
        finally:
            pool.disconnect()

    def rule_disable(self, p, logger=print):
        pool, api = self._api()
        try:
            r = self._get_rule(api, p)
            if not r:
                logger("Rule not found")
                return
            api.get_resource("/system/logging").set(id=r["id"], disabled="yes")
            logger("Disabled rule")
        finally:
            pool.disconnect()

    def rule_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource("/system/logging").get()
        finally:
            pool.disconnect()