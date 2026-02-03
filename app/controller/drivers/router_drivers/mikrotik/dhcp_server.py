class RouterOSDhcpServerDriver:
    name = "routerosapi_dhcp_server"

    def __init__(self, core_driver):
        self.core = core_driver
            
    def add_server(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            dhcp_res = api.get_resource('/ip/dhcp-server')
            net_res = api.get_resource('/ip/dhcp-server/network')
            pool_res = api.get_resource('/ip/pool')
            addr_res = api.get_resource('/ip/address')

            name = p.get("name")
            interface = p.get("interface")
            address_pool = p.get("address-pool")
            lease_time = p.get("lease-time", "10m")
            authoritative = p.get("authoritative", "yes")
            disabled = "yes" if p.get("disabled") else "no"

            if not name:
                raise Exception("name is required")
            if not interface:
                raise Exception("interface is required")
            if not address_pool:
                raise Exception("address-pool is required")

            if dhcp_res.get(name=name):
                logger(f"DHCP Server '{name}' already exists, skip add")
                return

            existing_pool = pool_res.get(name=address_pool)
            if not existing_pool:
                iface_addrs = addr_res.get(interface=interface)
                if not iface_addrs:
                    raise Exception(f"Interface {interface} has no IP address, cannot create pool")

                addr = iface_addrs[0].get("address")
                ip, prefix = addr.split("/")
                if prefix != "24":
                    raise Exception("Only /24 subnet supported for auto pool")

                base = ip.rsplit(".", 1)[0]
                start_ip = f"{base}.10"
                end_ip = f"{base}.254"
                if ip == start_ip:
                    start_ip = f"{base}.20"

                pool_res.add(
                    name=address_pool,
                    ranges=f"{start_ip}-{end_ip}"
                )
                logger(f"Auto-created IP pool {address_pool} {start_ip}-{end_ip}")

            payload = {
                "name": name,
                "interface": interface,
                "address-pool": address_pool,
                "lease-time": lease_time,
                "authoritative": authoritative,
                "disabled": disabled
            }

            dhcp_res.add(**payload)
            logger(f"Added DHCP server '{name}' on {interface} with pool {address_pool}")

        except Exception as e:
            logger(f"Add DHCP Server failed: {str(e)}")
            raise Exception(f"Failed to add DHCP Server: {str(e)}")
        finally:
            pool.disconnect()

    # ====================================================
    # EDIT DHCP SERVER
    # ====================================================
    def edit_server(self, p, logger=print):
        """
        Contoh payload:
        {
            "old_name": "DHCP_LANX",   # optional, kalau mau rename
            "name": "DHCP_OFFICE",     # bisa juga dipakai buat rename
            "interface": "bridge2",
            "address_pool": "POOL_MAIN",
            "lease_time": "1d",
            "authoritative": "after-2sec-delay"
        }
        """
        pool, api = self.core.get_api()
        try:
            dhcp_res = api.get_resource('/ip/dhcp-server')

            # 🔍 Tentukan mana yang dipakai buat cari server
            search_name = p.get("old_name") or p.get("name")

            recs = dhcp_res.get(name=search_name)
            if not recs:
                raise Exception(f"DHCP Server '{search_name}' not found")

            rec = recs[0]
            record_id = rec.get(".id") or rec.get("id")

            # 🧩 Siapkan update payload
            update_data = {}
            if "name" in p and p["name"] != search_name:
                update_data["name"] = p["name"]

            if "interface" in p:
                update_data["interface"] = p["interface"]

            if "address_pool" in p:
                update_data["address-pool"] = p["address_pool"]

            if "lease_time" in p:
                update_data["lease-time"] = p["lease_time"]

            if "authoritative" in p:
                update_data["authoritative"] = p["authoritative"]

            if "disabled" in p:
                update_data["disabled"] = p["disabled"]

            if not update_data:
                logger(f"⚠️ No update parameters provided for DHCP server '{search_name}'")
                return

            # 🛠 Apply update
            dhcp_res.set(**{"numbers": record_id, **update_data})

            new_name = update_data.get("name", search_name)
            logger(f"✏️ Updated DHCP server '{search_name}' successfully")
            if "name" in update_data:
                logger(f"🔁 Renamed to '{new_name}'")

        except Exception as e:
            logger(f"❌ Edit failed: {str(e)}")
            raise Exception(f"Failed to edit DHCP server: {str(e)}")
        finally:
            pool.disconnect()

    # ====================================================
    # EDIT DHCP NETWORK
    # ====================================================
    def edit_network(self, p, logger=print):
        """
        Contoh payload:
        {
            "address": "192.168.10.0/24",
            "gateway": "192.168.10.1",
            "dns_servers": "1.1.1.1,8.8.8.8",
            "domain": "office.local",
            "comment": "Updated LAN segment"
        }
        """
        pool, api = self.core.get_api()
        try:
            net_res = api.get_resource('/ip/dhcp-server/network')

            # 🔍 Cari network berdasarkan address
            recs = net_res.get(address=p["address"])
            if not recs:
                raise Exception(f"DHCP network {p['address']} not found")

            rec = recs[0]
            record_id = rec.get(".id") or rec.get("id")

            # Siapkan payload update
            update_data = {}
            if "gateway" in p:
                update_data["gateway"] = p["gateway"]
            if "dns_servers" in p:
                update_data["dns-server"] = p["dns_servers"]
            if "domain" in p:
                update_data["domain"] = p["domain"]
            if "comment" in p:
                update_data["comment"] = p["comment"]

            # Jalankan update
            net_res.set(**{"numbers": record_id, **update_data})
            logger(f"✏️ Updated DHCP network {p['address']} successfully")

        except Exception as e:
            logger(f"❌ Edit DHCP network failed: {str(e)}")
            raise Exception(f"Failed to edit DHCP network: {str(e)}")
        finally:
            pool.disconnect()

    # ====================================================
    # ENABLE / DISABLE
    # ====================================================
    def enable_server(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/dhcp-server')
            rec = res.get(name=p["name"])
            if not rec:
                raise Exception(f"DHCP server '{p['name']}' not found")

            record_id = rec[0].get(".id") or rec[0].get("id")
            res.set(numbers=record_id, disabled="no")
            logger(f"✅ Enabled DHCP server '{p['name']}'")
        except Exception as e:
            logger(f"❌ Enable failed: {str(e)}")
            raise Exception(f"Failed to enable DHCP server: {str(e)}")
        finally:
            pool.disconnect()

    def disable_server(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/dhcp-server')
            rec = res.get(name=p["name"])
            if not rec:
                raise Exception(f"DHCP server '{p['name']}' not found")

            record_id = rec[0].get(".id") or rec[0].get("id")
            res.set(numbers=record_id, disabled="yes")
            logger(f"🚫 Disabled DHCP server '{p['name']}'")
        except Exception as e:
            logger(f"❌ Disable failed: {str(e)}")
            raise Exception(f"Failed to disable DHCP server: {str(e)}")
        finally:
            pool.disconnect()

    # ====================================================
    # DELETE
    # ====================================================
    def delete_server(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/dhcp-server')
            rec = res.get(name=p["name"])
            if not rec:
                raise Exception(f"DHCP server '{p['name']}' not found")

            record_id = rec[0].get(".id") or rec[0].get("id")
            res.remove(numbers=record_id)
            logger(f"🗑️ Deleted DHCP server '{p['name']}'")
        except Exception as e:
            logger(f"❌ Delete failed: {str(e)}")
            raise Exception(f"Failed to delete DHCP server: {str(e)}")
        finally:
            pool.disconnect()

    def list_servers(self, p=None, logger=print):
        """
        List semua DHCP server:
        /ip/dhcp-server print
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/dhcp-server')
            data = res.get()

            out = []
            for item in data:
                row = dict(item)
                
                # Normalize ID
                row["id"] = item.get(".id") or item.get("id")

                # Normalize disabled
                row["disabled"] = item.get("disabled", "no")

                out.append(row)

            logger("dhcp.server.list completed")
            return out

        finally:
            pool.disconnect()

    def list_networks(self, p=None, logger=print):
        """
        List DHCP networks:
        /ip/dhcp-server/network print
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/dhcp-server/network')
            data = res.get()

            out = []
            for item in data:
                row = dict(item)
                row["id"] = item.get(".id") or item.get("id")

                out.append(row)

            logger("dhcp.network.list completed")
            return out

        finally:
            pool.disconnect()

    def list_leases(self, p=None, logger=print):
        """
        List DHCP leases:
        /ip/dhcp-server/lease print
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/dhcp-server/lease')
            data = res.get()

            out = []
            for item in data:
                row = dict(item)

                # Normalize ID
                row["id"] = item.get(".id") or item.get("id")

                # Normalize status
                row["status"] = item.get("status", item.get("active", "unknown"))

                out.append(row)

            logger("dhcp.lease.list completed")
            return out

        finally:
            pool.disconnect()
