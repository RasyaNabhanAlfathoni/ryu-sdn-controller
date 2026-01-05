class MikroTikAPDhcpClientDriver:
    name = "mikrotikap_dhcp_client"

    def __init__(self, core_driver):
        self.core = core_driver

    # ============= ADD DHCP CLIENT =============
    def add_client(self, p, logger=print):
        """
        Contoh:
        {
            "interface": "ether1",
            "use_peer_dns": True,
            "use_peer_ntp": True,
            "add_default_route": "yes",
            "comment": "DHCP uplink"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/dhcp-client')
            payload = {
                "interface": p["interface"],
                "use-peer-dns": "yes" if p.get("use_peer_dns", True) else "no",
                "use-peer-ntp": "yes" if p.get("use_peer_ntp", True) else "no",
                "add-default-route": p.get("add_default_route", "yes"),
                "disabled": "no"
            }
            if "comment" in p:
                payload["comment"] = p["comment"]
            res.add(**payload)
            logger(f"DHCP Client added on {p['interface']}")
        except Exception as e:
            logger(f"Add DHCP Client failed: {str(e)}")
            raise Exception(f"Failed to add DHCP Client: {str(e)}")
        finally:
            pool.disconnect()

    # ============= EDIT DHCP CLIENT =============
    def edit_client(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/dhcp-client')
            recs = res.get()
            target = next((r for r in recs if r.get("interface") == p["interface"]), None)
            if not target:
                raise Exception(f"DHCP Client on {p['interface']} not found")

            record_id = target.get(".id") or target.get("id")

            update = {}
            if "use_peer_dns" in p:
                update["use-peer-dns"] = "yes" if p["use_peer_dns"] else "no"
            if "use_peer_ntp" in p:
                update["use-peer-ntp"] = "yes" if p["use_peer_ntp"] else "no"
            if "add_default_route" in p:
                update["add-default-route"] = p["add_default_route"]
            if "comment" in p:
                update["comment"] = p["comment"]

            res.set(numbers=record_id, **update)
            logger(f"DHCP Client on {p['interface']} updated")

        except Exception as e:
            logger(f"Edit DHCP Client failed: {str(e)}")
            raise Exception(f"Failed to edit DHCP Client: {str(e)}")

        finally:
            pool.disconnect()

    # ============= ENABLE / DISABLE / DELETE / COMMENT =============
    def enable_client(self, p, logger=print):
        self._set_disabled(p, logger, False)

    def disable_client(self, p, logger=print):
        self._set_disabled(p, logger, True)

    def _set_disabled(self, p, logger, disabled):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/dhcp-client')
            recs = res.get()
            target = next((r for r in recs if r.get("interface") == p["interface"]), None)
            if not target:
                raise Exception(f"DHCP Client on {p['interface']} not found")
            record_id = target.get(".id") or target.get("id")
            res.set(numbers=record_id, disabled="yes" if disabled else "no")
            logger(f"DHCP Client on {p['interface']} {'disabled' if disabled else 'enabled'}")
        except Exception as e:
            logger(f"Set disabled failed: {str(e)}")
            raise Exception(f"Failed to set disabled: {str(e)}")
        finally:
            pool.disconnect()

    def delete_client(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/dhcp-client')
            recs = res.get()
            target = next((r for r in recs if r.get("interface") == p["interface"]), None)
            if not target:
                raise Exception(f"DHCP Client on {p['interface']} not found")
            record_id = target.get(".id") or target.get("id")
            res.remove(numbers=record_id)
            logger(f"DHCP Client on {p['interface']} deleted")
        except Exception as e:
            logger(f"Delete DHCP Client failed: {str(e)}")
            raise Exception(f"Failed to delete DHCP Client: {str(e)}")
        finally:
            pool.disconnect()

    def comment_client(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/dhcp-client')
            recs = res.get()
            target = next((r for r in recs if r.get("interface") == p["interface"]), None)
            if not target:
                raise Exception(f"DHCP Client on {p['interface']} not found")
            record_id = target.get(".id") or target.get("id")
            res.set(numbers=record_id, comment=p["comment"])
            logger(f"Comment on DHCP Client {p['interface']} updated")
        except Exception as e:
            logger(f"Comment DHCP Client failed: {str(e)}")
            raise Exception(f"Failed to comment DHCP Client: {str(e)}")
        finally:
            pool.disconnect()

    def list_client(self, p=None, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/dhcp-client')
            data = res.get()

            out = []
            for item in data:
                row = {
                    "id": item.get(".id") or item.get("id"),
                    "interface": item.get("interface"),
                    "status": item.get("status"),
                    "address": item.get("address"),
                    "gateway": item.get("gateway"),
                    "use-peer-dns": item.get("use-peer-dns"),
                    "use-peer-ntp": item.get("use-peer-ntp"),
                    "add-default-route": item.get("add-default-route"),
                    "comment": item.get("comment"),
                    "disabled": item.get("disabled"),
                }
                out.append(row)

            logger("dhcp.client.list completed")
            return out

        finally:
            pool.disconnect()