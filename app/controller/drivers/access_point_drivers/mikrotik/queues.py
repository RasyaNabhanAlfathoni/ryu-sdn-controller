from routeros_api import RouterOsApiPool

class MikroTikAPQueuesDriver:
    name = "mikrotikap_queues"

    def __init__(self, core_driver):
        self.core = core_driver
        self.dev = core_driver.dev

    # =====================================================
    # API CONNECTOR
    # =====================================================
    def _api(self):
        pool = RouterOsApiPool(
            host=self.dev["ip"],
            username=self.dev["username"],
            password=self.dev["password"],
            plaintext_login=True
        )
        return pool, pool.get_api()

    # =====================================================
    # SIMPLE QUEUE SECTION
    # =====================================================

    def _get_queue(self, api, name):
        q = api.get_resource('/queue/simple').get(name=name)
        return q[0] if q else None

    def _combine_ud(self, d, key):
        if not d or key not in d:
            return None
        up = d[key].get("upload")
        down = d[key].get("download")
        if up is None or down is None:
            return None
        return f"{up}/{down}"

    def _build_payload(self, p):
        payload = {}

        # Name
        if "new_name" in p:
            payload["name"] = p["new_name"]
        elif "name" in p:
            payload["name"] = p["name"]


        # Target
        if "target" in p:
            payload["target"] = ",".join(p["target"]) if isinstance(p["target"], list) else p["target"]

        # Dst
        if "dst" in p:
            payload["dst"] = p["dst"]

        # Max limit
        max_lim = self._combine_ud(p, "max_limit")
        if max_lim:
            payload["max-limit"] = max_lim

        # Burst fields
        burst = p.get("burst", {})
        for field, key in {
            "limit": "burst-limit",
            "threshold": "burst-threshold",
            "time": "burst-time"
        }.items():
            v = self._combine_ud(burst, field)
            if v:
                payload[key] = v

        # Time
        if "time" in p:
            t = p["time"]
            if "from" in t and "to" in t:
                time_str = f"{t['from']}-{t['to']}"
                if "days" in t:
                    time_str += "," + ",".join(t["days"])
                payload["time"] = time_str

        # Advanced
        adv = p.get("advanced", {})
        if adv:
            if "packet_marks" in adv:
                payload["packet-marks"] = ",".join(adv["packet_marks"]) if isinstance(adv["packet_marks"], list) else adv["packet_marks"]

            for field, key in {
                "limit_at": "limit-at",
                "priority": "priority",
                "bucket_size": "bucket-size",
            }.items():
                v = self._combine_ud(adv, field)
                if v:
                    payload[key] = v

            if "queue_type" in adv:
                qt = adv["queue_type"]
                payload["queue"] = f"{qt['upload']}/{qt['download']}"

            if "parent" in adv:
                payload["parent"] = adv["parent"]

        # Total fields
        total = p.get("total")
        if total:
            mapping = {
                "limit_at": "total-limit-at",
                "max_limit": "total-max-limit",
                "priority": "total-priority",
                "burst_limit": "total-burst-limit",
                "burst_threshold": "total-burst-threshold",
                "burst_time": "total-burst-time",
                "queue_type": "total-queue"
            }
            for key, rkey in mapping.items():
                if key in total:
                    payload[rkey] = total[key]

        # Comment
        if "comment" in p:
            payload["comment"] = p["comment"]

        return payload

    # CRUD SIMPLE QUEUE
    def queue_simple_add(self, p, logger=print):
        pool, api = self._api()
        try:
            api.get_resource('/queue/simple').add(**self._build_payload(p))
            logger(f"Added simple queue {p['name']}")
        finally:
            pool.disconnect()

    def queue_simple_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            q = self._get_queue(api, p["name"])
            if not q:
                logger(f"Queue {p['name']} not found")
                return
            payload = self._build_payload(p)
            payload["id"] = q["id"]

            api.get_resource('/queue/simple').set(**payload)
            logger(f"Edited simple queue {p['name']}")
        finally:
            pool.disconnect()

    def queue_simple_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            q = self._get_queue(api, p["name"])
            if not q:
                logger(f"Queue {p['name']} not found")
                return
            api.get_resource('/queue/simple').remove(id=q["id"])
            logger(f"Deleted simple queue {p['name']}")
        finally:
            pool.disconnect()

    def queue_simple_enable(self, p, logger=print):
        pool, api = self._api()
        try:
            q = self._get_queue(api, p["name"])
            if not q:
                logger(f"Queue {p['name']} not found")
                return
            api.get_resource('/queue/simple').set(id=q["id"], disabled="no")
            logger(f"Enabled {p['name']}")
        finally:
            pool.disconnect()

    def queue_simple_disable(self, p, logger=print):
        pool, api = self._api()
        try:
            q = self._get_queue(api, p["name"])
            if not q:
                logger(f"Queue {p['name']} not found")
                return
            api.get_resource('/queue/simple').set(id=q["id"], disabled="yes")
            logger(f"Disabled {p['name']}")
        finally:
            pool.disconnect()

    def queue_simple_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource('/queue/simple').get()
        finally:
            pool.disconnect()

    # =====================================================
    # INTERFACE QUEUE SECTION
    # =====================================================

    def queue_interface_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource('/queue/interface').get()
        finally:
            pool.disconnect()

    def queue_interface_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            iface = p["interface"]
            qtype = p["queue"]  # <-- sudah fix pakai "queue"

            entries = api.get_resource("/queue/interface").get(interface=iface)
            if not entries:
                logger(f"Interface queue '{iface}' not found")
                return

            entry = entries[0]
            api.get_resource("/queue/interface").set(id=entry["id"], queue=qtype)

            logger(f"Updated interface queue for {iface} → {qtype}")
        finally:
            pool.disconnect()

    # =====================================================
    # QUEUE TREE SECTION (DIGABUNG)
    # =====================================================

    def _get_tree(self, api, name):
        items = api.get_resource("/queue/tree").get(name=name)
        return items[0] if items else None

    def _build_tree_payload(self, p):
        payload = {}

        # Name (support rename)
        if "new_name" in p:
            payload["name"] = p["new_name"]
        elif "name" in p:
            payload["name"] = p["name"]
        if "parent" in p:
            payload["parent"] = p["parent"]
        if "packet_mark" in p:
            payload["packet-mark"] = ",".join(p["packet_mark"]) if isinstance(p["packet_mark"], list) else p["packet_mark"]
        if "queue_type" in p:
            payload["queue"] = p["queue_type"]
        if "priority" in p:
            payload["priority"] = str(p["priority"])
        if "bucket_size" in p:
            payload["bucket-size"] = str(p["bucket_size"])

        limits = {
            "limit_at": "limit-at",
            "max_limit": "max-limit",
            "burst_limit": "burst-limit",
            "burst_threshold": "burst-threshold",
            "burst_time": "burst-time",
        }
        for key, rkey in limits.items():
            if key in p:
                payload[rkey] = p[key]

        # Comment
        if "comment" in p:
            payload["comment"] = p["comment"]

        return payload

    # CRUD TREE
    def queue_tree_add(self, p, logger=print):
        pool, api = self._api()
        try:
            api.get_resource("/queue/tree").add(**self._build_tree_payload(p))
            logger(f"Added queue-tree {p['name']}")
        finally:
            pool.disconnect()

    def queue_tree_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            q = self._get_tree(api, p["name"])
            if not q:
                logger(f"Queue-tree {p['name']} not found")
                return

            payload = self._build_tree_payload(p)
            payload["id"] = q["id"]
            api.get_resource("/queue/tree").set(**payload)
            logger(f"Edited queue-tree {p['name']}")
        finally:
            pool.disconnect()

    def queue_tree_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            q = self._get_tree(api, p["name"])
            if not q:
                logger(f"Queue-tree {p['name']} not found")
                return
            api.get_resource("/queue/tree").remove(id=q["id"])
            logger(f"Deleted queue-tree {p['name']}")
        finally:
            pool.disconnect()

    def queue_tree_enable(self, p, logger=print):
        pool, api = self._api()
        try:
            q = self._get_tree(api, p["name"])
            if not q:
                logger(f"Queue-tree {p['name']} not found")
                return
            api.get_resource("/queue/tree").set(id=q["id"], disabled="no")
            logger(f"Enabled queue-tree {p['name']}")
        finally:
            pool.disconnect()

    def queue_tree_disable(self, p, logger=print):
        pool, api = self._api()
        try:
            q = self._get_tree(api, p["name"])
            if not q:
                logger(f"Queue-tree {p['name']} not found")
                return
            api.get_resource("/queue/tree").set(id=q["id"], disabled="yes")
            logger(f"Disabled queue-tree {p['name']}")
        finally:
            pool.disconnect()

    def queue_tree_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource("/queue/tree").get()
        finally:
            pool.disconnect()

    # -----------------------
    # QUEUE TYPES SECTION (generic builder)
    # -----------------------
    def _get_queue_type(self, api, name):
        return self._get_by_resource_and_name(api, "/queue/type", name)

    def _snake_to_mikrotik(self, key):
        return key.replace("_", "-")

    def _normalize_value(self, v):
        if isinstance(v, bool):
            return "yes" if v else "no"
        if isinstance(v, (list, tuple)):
            return ",".join(v)
        return v

    def _get_by_resource_and_name(self, api, path, name):
        items = api.get_resource(path).get(name=name)
        return items[0] if items else None

    def _build_type_payload(self, p):
        payload = {}
        # name rename support
        if "new_name" in p:
            payload["name"] = p["new_name"]
        elif "name" in p:
            payload["name"] = p["name"]

        # kind is required for add/edit if provided
        if "kind" in p:
            payload["kind"] = p["kind"]

        # iterate other keys and translate
        for k, v in p.items():
            if k in ("name", "new_name", "kind"):
                continue
            mk = self._snake_to_mikrotik(k)
            val = self._normalize_value(v)
            if val is None or val == "":
                # skip empty
                continue
            payload[mk] = val
        return payload

    def queue_type_add(self, p, logger=print):
        pool, api = self._api()
        try:
            payload = self._build_type_payload(p)
            api.get_resource("/queue/type").add(**payload)
            logger(f"Added queue-type {p.get('name')}")
        finally:
            pool.disconnect()

    def queue_type_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            q = self._get_queue_type(api, p["name"])
            if not q:
                logger(f"Queue-type {p['name']} not found")
                return
            payload = self._build_type_payload(p)
            payload["id"] = q["id"]
            api.get_resource("/queue/type").set(**payload)
            logger(f"Edited queue-type {p['name']}")
        finally:
            pool.disconnect()

    def queue_type_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            q = self._get_queue_type(api, p["name"])
            if not q:
                logger(f"Queue-type {p['name']} not found")
                return
            api.get_resource("/queue/type").remove(id=q["id"])
            logger(f"Deleted queue-type {p['name']}")
        finally:
            pool.disconnect()

    def queue_type_list(self, p=None, logger=print):
        pool, api = self._api()
        try:
            return api.get_resource("/queue/type").get()
        finally:
            pool.disconnect()