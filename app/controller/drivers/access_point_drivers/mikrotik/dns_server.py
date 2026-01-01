class MikroTikAPDnsDriver:
    name = "mikrotikap_dns"

    def __init__(self, core_driver):
        self.core = core_driver

    # ====================================================
    # GLOBAL DNS CONFIG
    # ====================================================
    def edit_dns(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            sys_res = api.get_resource('/system/resource')
            version_str = sys_res.get()[0].get("version", "6.0")
            major = int(version_str.split(".")[0])
            minor = int(version_str.split(".")[1].split(" ")[0]) if "." in version_str else 0

            dns_res = api.get_resource('/ip/dns')
            update_data = {}

            if "servers" in p:
                update_data["servers"] = ",".join(p["servers"]) if isinstance(p["servers"], list) else p["servers"]

            if "allow_remote" in p:
                update_data["allow-remote-requests"] = "yes" if p["allow_remote"] else "no"

            if "use_doh" in p:
                if p["use_doh"]:
                    if not p.get("doh_server"):
                        raise Exception("Missing 'doh_server' URL for DoH mode.")
                    update_data["use-doh-server"] = p["doh_server"]
                    if (major == 7 and minor < 13) or major < 7:
                        if "verify_doh_cert" in p:
                            update_data["verify-doh-cert"] = "yes" if p["verify_doh_cert"] else "no"
                else:
                    update_data["use-doh-server"] = ""
                    if major < 7 or (major == 7 and minor < 13):
                        update_data["verify-doh-cert"] = "no"

            if not update_data:
                logger("No fields to update in DNS config.")
                return

            dns_res.set(**update_data)
            logger(f"Updated DNS config (RouterOS {version_str}): {update_data}")

        except Exception as e:
            logger(f"Edit DNS failed: {str(e)}")
            raise Exception(f"Failed to edit DNS config: {str(e)}")
        finally:
            pool.disconnect()

    # ====================================================
    # FLUSH CACHE
    # ====================================================
    def flush_cache(self, p=None, logger=print):
        pool, api = self.core.get_api()
        try:
            cache_res = api.get_resource('/ip/dns/cache')
            cache_res.call("flush")
            logger("Flushed DNS cache successfully.")
        except Exception as e:
            logger(f"Flush cache failed: {str(e)}")
            raise Exception(f"Failed to flush DNS cache: {str(e)}")
        finally:
            pool.disconnect()

    # ====================================================
    # DNS STATIC MANAGEMENT
    # ====================================================

    def add_static(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            dns_static = api.get_resource('/ip/dns/static')
            sys_res = api.get_resource('/system/resource')
            version_str = sys_res.get()[0].get("version", "6.0")
            major = int(version_str.split(".")[0])
            minor = int(version_str.split(".")[1].split(" ")[0]) if "." in version_str else 0
            is_v7 = major >= 7

            payload = {
                "type": p.get("type", "A"),
                "ttl": p.get("ttl", "1d"),
                "disabled": "no"
            }

            if "name" in p:
                payload["name"] = p["name"]
            if "regexp" in p:
                payload["regexp"] = p["regexp"]

            t = p.get("type", "A").upper()
            if t in ["A", "AAAA"]:
                payload["address"] = p.get("address")
            elif t == "CNAME":
                payload["cname"] = p.get("cname")
            elif t == "TXT":
                payload["text"] = p.get("text")
            elif t == "MX":
                payload["mx-exchange"] = p.get("mx_exchange")
                payload["mx-preference"] = p.get("mx_preference", 10)
            elif t == "NS":
                payload["ns"] = p.get("ns")
            elif t == "SRV":
                payload["srv-target"] = p.get("srv_target")
                payload["srv-port"] = p.get("srv_port")
                payload["srv-priority"] = p.get("srv_priority", 10)
                payload["srv-weight"] = p.get("srv_weight", 5)
            elif t == "FWD":
                payload["forward-to"] = p.get("forward_to")
            elif t == "NXDOMAIN":
                payload["type"] = "NXDOMAIN"

            if is_v7:
                if "match_subdomain" in p:
                    payload["match-subdomain"] = "yes" if p["match_subdomain"] else "no"
                if "address_list" in p:
                    payload["address-list"] = p["address_list"]

            if "comment" in p:
                payload["comment"] = p["comment"]

            dns_static.add(**payload)
            logger(f"Added DNS static record: {payload}")

        except Exception as e:
            logger(f"Add DNS static failed: {str(e)}")
            raise Exception(f"Failed to add DNS static record: {str(e)}")
        finally:
            pool.disconnect()

    # ====================================================
    # EDIT STATIC RECORD
    # ====================================================
    def edit_static(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            dns_static = api.get_resource('/ip/dns/static')
            old_name = p.get("old_name") or p.get("name")
            if not old_name:
                raise Exception("Parameter 'old_name' or 'name' required")

            recs = dns_static.get(name=old_name)
            if not recs or len(recs) == 0:
                raise Exception(f"DNS static '{old_name}' not found")

            rec = recs[0]
            record_id = rec.get(".id") or rec.get("id")

            # Fallback: cari manual
            if not record_id:
                all_records = dns_static.get()
                for r in all_records:
                    if r.get("name") == old_name:
                        record_id = r.get(".id") or r.get("id")
                        break

            if not record_id:
                raise Exception(f"Could not find record ID for '{old_name}'")

            update_data = {}

            # Field yang bisa diubah
            for k in ["ttl", "comment", "regexp", "address", "cname", "text",
                      "ns", "mx-exchange", "mx-preference", "srv-target",
                      "srv-port", "srv-priority", "srv-weight"]:
                if k in p:
                    update_data[k] = p[k]

            if "new_type" in p:
                update_data["type"] = p["new_type"]

            if "new_name" in p:
                update_data["name"] = p["new_name"]

            if not update_data:
                raise Exception("No fields to update in DNS static record")

            dns_static.set(numbers=record_id, **update_data)
            logger(f"Edited DNS static '{old_name}' (ID: {record_id}) successfully")

        except Exception as e:
            logger(f"Edit DNS static failed: {str(e)}")
            raise Exception(f"Failed to edit DNS static: {str(e)}")
        finally:
            pool.disconnect()

    # ====================================================
    # ENABLE / DISABLE STATIC RECORD
    # ====================================================
    def enable_static(self, p, logger=print):
        self._set_static_status(p, "no", logger)

    def disable_static(self, p, logger=print):
        self._set_static_status(p, "yes", logger)

    def _set_static_status(self, p, status, logger):
        pool, api = self.core.get_api()
        try:
            dns_static = api.get_resource('/ip/dns/static')
            recs = dns_static.get(name=p["name"]) if "name" in p else []
            if not recs or len(recs) == 0:
                raise Exception(f"DNS static '{p.get('name', '(unknown)')}' not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            if not record_id:
                raise Exception("Record ID not found")

            dns_static.set(numbers=record_id, disabled=status)
            logger(f"Set DNS static '{p.get('name', '(unknown)')}' disabled={status} (ID: {record_id})")
        except Exception as e:
            raise Exception(f"Failed to set DNS static status: {str(e)}")
        finally:
            pool.disconnect()

    # ====================================================
    # COMMENT STATIC RECORD
    # ====================================================
    def comment_static(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            dns_static = api.get_resource('/ip/dns/static')
            recs = dns_static.get(name=p["name"]) if "name" in p else []
            if not recs or len(recs) == 0:
                raise Exception(f"DNS static '{p.get('name', '(unknown)')}' not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            if not record_id:
                raise Exception("Record ID not found")

            dns_static.set(numbers=record_id, comment=p["comment"])
            logger(f"Updated comment for DNS static '{p['name']}' (ID: {record_id})")

        except Exception as e:
            logger(f"Comment DNS static failed: {str(e)}")
            raise Exception(f"Failed to update comment: {str(e)}")
        finally:
            pool.disconnect()

    # ====================================================
    # DELETE STATIC RECORD
    # ====================================================
    def delete_static(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            dns_static = api.get_resource('/ip/dns/static')
            recs = dns_static.get(name=p["name"]) if "name" in p else []
            if not recs or len(recs) == 0:
                raise Exception(f"DNS static '{p.get('name', '(unknown)')}' not found")

            record_id = recs[0].get(".id") or recs[0].get("id")
            if not record_id:
                raise Exception("Record ID not found")

            dns_static.remove(numbers=record_id)
            logger(f"Deleted DNS static '{p['name']}' (ID: {record_id})")

        except Exception as e:
            logger(f"Delete DNS static failed: {str(e)}")
            raise Exception(f"Failed to delete DNS static: {str(e)}")
        finally:
            pool.disconnect()

    def list_static(self, p=None, logger=print):
        pool, api = self.core.get_api()
        try:
            dns_static = api.get_resource('/ip/dns/static')
            data = dns_static.get()

            out = []
            for item in data:
                row = {
                    "id": item.get(".id") or item.get("id"),
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "address": item.get("address"),
                    "cname": item.get("cname"),
                    "text": item.get("text"),
                    "regexp": item.get("regexp"),
                    "forward_to": item.get("forward-to"),
                    "ttl": item.get("ttl"),
                    "comment": item.get("comment"),
                    "disabled": item.get("disabled"),
                }

                # DNS MX Fields
                if "mx-exchange" in item:
                    row["mx_exchange"] = item["mx-exchange"]
                if "mx-preference" in item:
                    row["mx_preference"] = item["mx-preference"]

                # SRV Fields
                if "srv-target" in item:
                    row["srv_target"] = item["srv-target"]
                if "srv-port" in item:
                    row["srv_port"] = item["srv-port"]
                if "srv-priority" in item:
                    row["srv_priority"] = item["srv-priority"]
                if "srv-weight" in item:
                    row["srv_weight"] = item["srv-weight"]

                # RouterOS v7 exclusive fields
                if "match-subdomain" in item:
                    row["match_subdomain"] = item["match-subdomain"]
                if "address-list" in item:
                    row["address_list"] = item["address-list"]

                out.append(row)

            logger("dns.static.list completed")
            return out

        finally:
            pool.disconnect()

