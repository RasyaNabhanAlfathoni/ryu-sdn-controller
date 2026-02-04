from enum import auto
from librouteros import connect
from routeros_api import RouterOsApiPool
from ryu.lib.packet import dhcp


class RouterOSBridgeDriver:
    name = "routerosapi_bridge"

    def __init__(self, dev):
        self.dev = dev.dev if hasattr(dev, "dev") else dev
        self.version = self._detect_version()

    def _detect_version(self):
        v = self.dev.get("os_version", "")
        try:
            return int(v.split(".")[0])
        except:
            return 6

    def _libapi(self):
        return connect(
            host=self.dev["ip"],
            username=self.dev["username"],
            password=self.dev["password"],
            port=8728,
            use_ssl=False
        )

    def _api(self):
        pool = RouterOsApiPool(
            host=self.dev["ip"],
            username=self.dev["username"],
            password=self.dev["password"],
            plaintext_login=True
        )
        return pool, pool.get_api()

    BRIDGE_FIELDS = {
        6: {
            "mtu", "arp",
            "admin-mac", "auto-mac", "igmp-snooping", "name", "region-name",
            "ageing-time", "comment", "max-hops", "priority", "region-revision",
            "fast-forward", "max-message-age", "protocol-mode", "transmit-hold-count",
            "arp-timeout", "forward-delay", "pvid", "vlan-filtering"
        },
        7: {
            "add-dhcp-option82", "membership-interval", "admin-mac", "mld-version",
            "ageing-time", "mtu", "arp", "multicast-querier", "arp-timeout",
            "multicast-router", "auto-mac", "mvrp", "comment", "name",
            "dhcp-snooping", "port-cost-mode", "ether-type", "priority",
            "fast-forward", "protocol-mode", "forward-delay", "pvid",
            "forward-reserved-addresses", "querier-interval", "frame-types",
            "query-interval", "igmp-snooping", "query-response-interval",
            "igmp-version", "region-name", "ingress-filtering", "region-revision",
            "last-member-interval", "last-member-query-count", "startup-query-count",
            "startup-query-interval", "max-hops", "transmit-hold-count",
            "max-learned-entries", "vlan-filtering", "max-message-age"
        }
    }

    PORT_FIELDS = {
        6: {
            "auto-isolate", "frame-types", "internal-path-cost", "pvid",
            "bridge", "horizon", "learn", "restricted-role",
            "broadcast-flood", "hw", "path-cost", "restricted-tcn",
            "comment", "ingress-filtering", "point-to-point", "unknown-multicast-flood",
            "edge", "interface", "priority", "unknown-unicast-flood"
        },
        7: {
            "auto-isolate", "comment", "horizon", "internal-path-cost", "mvrp-registrar-state", "pvid", "trusted",
            "bpdu-guard", "edge", "hw", "learn", "path-cost", "restricted-role", "unknown-multicast-flood",
            "bridge", "fast-leave", "ingress-filtering", "multicast-router", "point-to-point", "restricted-tcn",
            "unknown-unicast-flood", "broadcast-flood", "frame-types", "interface", "mvrp-applicant-state",
            "priority",  "tag-stacking"
        }
    }

    # UTILITY
    def _filter_fields(self, payload, allowed_fields):
        out = {}
        for k, v in payload.items():
            mk = k.replace("_", "-")
            if mk in allowed_fields:
                out[mk] = v
        return out

    # BRIDGE
    def list_bridge(self, p=None, logger=print):
        api = self._libapi()
        data = api("/interface/bridge/print")

        out = []
        for b in data:
            out.append({
                "id": b.get(".id"),
                "name": b.get("name"),
                "mtu": b.get("mtu"),
                "protocol_mode": b.get("protocol-mode"),
                "vlan_filtering": b.get("vlan-filtering"),
                "igmp_snooping": b.get("igmp-snooping"),
                "fast_forward": b.get("fast-forward"),
                "running": b.get("running"),
                "disabled": b.get("disabled"),
                "comment": b.get("comment"),
            })

        logger("[BRIDGE] list completed")
        return out

    def add_bridge(self, p, logger=print):
        pool, api = self._api()
        try:
            raw = {k.replace("_", "-"): v for k, v in p.items()}
            payload = self._filter_fields(
                raw,
                self.BRIDGE_FIELDS.get(self.version, set())
            )
            api.get_resource("/interface/bridge").add(**payload)
            logger(f"[BRIDGE] added {p.get('name')}")
        finally:
            pool.disconnect()

    def edit_bridge(self, p, logger=print):
        pool, api = self._api()
        try:
            res = api.get_resource("/interface/bridge")
            rec = res.get(name=p["name"])
            if not rec:
                raise Exception("Bridge not found")

            raw = {k.replace("_", "-"): v for k, v in p.items() if k != "name"}
            payload = self._filter_fields(
                raw,
                self.BRIDGE_FIELDS.get(self.version, set())
            )

            res.set(numbers=rec[0][".id"], **payload)
            logger(f"[BRIDGE] updated {p['name']}")
        finally:
            pool.disconnect()

    def enable_bridge(self, p, logger=print):
        self._set_bridge_disabled(p["name"], False, logger)

    def disable_bridge(self, p, logger=print):
        self._set_bridge_disabled(p["name"], True, logger)

    def _set_bridge_disabled(self, name, disabled, logger):
        pool, api = self._api()
        try:
            res = api.get_resource("/interface/bridge")
            rec = res.get(name=name)
            res.set(numbers=rec[0][".id"], disabled="yes" if disabled else "no")
            logger(f"[BRIDGE] {name} {'disabled' if disabled else 'enabled'}")
        finally:
            pool.disconnect()

    def delete_bridge(self, p, logger=print):
        pool, api = self._api()
        try:
            res = api.get_resource("/interface/bridge")
            rec = res.get(name=p["name"])
            res.remove(numbers=rec[0][".id"])
            logger(f"[BRIDGE] deleted {p['name']}")
        finally:
            pool.disconnect()

    # PORT
    def list_ports(self, p=None, logger=print):
        api = self._libapi()
        data = api("/interface/bridge/port/print")

        out = []
        for r in data:
            out.append({
                "id": r.get(".id"),
                "interface": r.get("interface"),
                "bridge": r.get("bridge"),
                "pvid": r.get("pvid"),
                "frame_types": r.get("frame-types"),
                "ingress_filtering": r.get("ingress-filtering"),
                "edge": r.get("edge"),
                "point_to_point": r.get("point-to-point"),
                "horizon": r.get("horizon"),
                "trusted": r.get("trusted"),
                "disabled": r.get("disabled"),
                "comment": r.get("comment"),
            })

        logger("[BRIDGE-PORT] list completed")
        return out

    def add_port(self, p, logger=print):
        pool, api = self._api()
        try:
            raw = {k.replace("_", "-"): v for k, v in p.items()}
            payload = self._filter_fields(
                raw,
                self.PORT_FIELDS.get(self.version, set())
            )
            api.get_resource("/interface/bridge/port").add(**payload)
            logger(f"[BRIDGE-PORT] added {p.get('interface')}")
        finally:
            pool.disconnect()

    def edit_port(self, p, logger=print):
        pool, api = self._api()
        try:
            res = api.get_resource("/interface/bridge/port")
            rec = res.get(interface=p["interface"])
            if not rec:
                raise Exception("Bridge port not found")

            raw = {k.replace("_", "-"): v for k, v in p.items() if k != "interface"}
            payload = self._filter_fields(
                raw,
                self.PORT_FIELDS.get(self.version, set())
            )

            res.set(numbers=rec[0][".id"], **payload)
            logger(f"[BRIDGE-PORT] updated {p['interface']}")
        finally:
            pool.disconnect()

    def enable_port(self, p, logger=print):
        self._set_port_disabled(p["interface"], False, logger)

    def disable_port(self, p, logger=print):
        self._set_port_disabled(p["interface"], True, logger)

    def _set_port_disabled(self, iface, disabled, logger):
        pool, api = self._api()
        try:
            res = api.get_resource("/interface/bridge/port")
            rec = res.get(interface=iface)
            res.set(numbers=rec[0][".id"], disabled="yes" if disabled else "no")
            logger(f"[BRIDGE-PORT] {iface} {'disabled' if disabled else 'enabled'}")
        finally:
            pool.disconnect()

    def delete_port(self, p, logger=print):
        pool, api = self._api()
        try:
            res = api.get_resource("/interface/bridge/port")
            rec = res.get(interface=p["interface"])
            res.remove(numbers=rec[0][".id"])
            logger(f"[BRIDGE-PORT] removed {p['interface']}")
        finally:
            pool.disconnect()

    # VLAN            

    def vlan_list(self, p=None, logger=print):
        api = self._libapi()
        vlans = api("/interface/bridge/vlan/print")

        out = []
        for v in vlans:
            row = {
                "id": v.get(".id"),
                "bridge": v.get("bridge"),
                "vlan_ids": v.get("vlan-ids"),
                "tagged": v.get("tagged"),
                "untagged": v.get("untagged"),
                "disabled": v.get("disabled"),
                "comment": v.get("comment"),
            }

            if self.version >= 7:
                row["current_tagged"] = v.get("current-tagged")
                row["current_untagged"] = v.get("current-untagged")

            out.append(row)

        logger("[BRIDGE-VLAN] list completed")
        return out

    def vlan_add(self, p, logger=print):
        pool, api = self._api()
        try:
            payload = {}
            for k, v in p.items():
                key = k.replace("_", "-")
                payload[key] = ",".join(v) if isinstance(v, list) else v

            api.get_resource("/interface/bridge/vlan").add(**payload)
            logger(f"[BRIDGE-VLAN] added vlan {p.get('vlan_ids')}")
        finally:
            pool.disconnect()

    def vlan_edit(self, p, logger=print):
        pool, api = self._api()
        try:
            vid = p["id"]
            update = {}
            for k, v in p.items():
                if k == "id":
                    continue
                key = k.replace("_", "-")
                update[key] = ",".join(v) if isinstance(v, list) else v

            api.get_resource("/interface/bridge/vlan").set(numbers=vid, **update)
            logger(f"[BRIDGE-VLAN] updated {vid}")
        finally:
            pool.disconnect()

    def vlan_enable(self, p, logger=print):
        self._set_vlan_disabled(p["id"], False, logger)

    def vlan_disable(self, p, logger=print):
        self._set_vlan_disabled(p["id"], True, logger)

    def _set_vlan_disabled(self, vid, disabled, logger):
        pool, api = self._api()
        try:
            api.get_resource("/interface/bridge/vlan").set(
                numbers=vid,
                disabled="yes" if disabled else "no"
            )
            logger(f"[BRIDGE-VLAN] {vid} {'disabled' if disabled else 'enabled'}")
        finally:
            pool.disconnect()

    def vlan_delete(self, p, logger=print):
        pool, api = self._api()
        try:
            api.get_resource("/interface/bridge/vlan").remove(numbers=p["id"])
            logger(f"[BRIDGE-VLAN] deleted {p['id']}")
        finally:
            pool.disconnect()

    def mvrp_list(self, p=None, logger=print):
        if self.version < 7:
            logger("[MVRP] not supported on RouterOS < 7")
            return []

        api = self._libapi()
        rows = api("/interface/bridge/vlan/mvrp/print")

        out = []
        for r in rows:
            out.append({
                "id": r.get(".id"),
                "bridge": r.get("bridge"),
                "interface": r.get("interface"),
                "vlan_id": r.get("vlan-id"),
                "registrar_state": r.get("registrar-state"),
                "applicant_state": r.get("applicant-state"),
                "last_event": r.get("last-event"),
            })

        logger("bridge-mvrp attributes listed")
        return out