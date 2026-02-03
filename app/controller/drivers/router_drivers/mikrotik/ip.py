class RouterOSIpDriver:
    name = "routerosapi_ip"

    def __init__(self, core_driver):
        self.core = core_driver

    def _get_by_id(self, res, record_id):
        """Helper to get record by ID"""
        recs = res.get(numbers=record_id)
        if not recs:
            raise Exception(f"Record with id {record_id} not found")
        return recs[0]

    def _get_id_from_address_interface(self, res, address=None, interface=None):
        """
        Helper to get record ID from address and/or interface
        Returns the actual ID if found, raises Exception if not found
        """
        if address:
            recs = res.get(address=address)
        elif interface:
            recs = res.get(interface=interface)
        else:
            raise Exception("Either address or interface must be provided")

        if not recs:
            raise Exception(f"No record found with {'address=' + address if address else 'interface=' + interface}")

        # If multiple records found, return the first one
        record = recs[0]
        record_id = record.get(".id") or record.get("id")
        if not record_id:
            raise Exception("Record ID not found in API response")
        
        return record_id

    def list_addresses(self, p=None, logger=print):
        """
        List IP Address.

        Parameter opsional:
        {
            "interface": "ether3"
        }
        atau
        {
            "address": "10.10.10.1/24"
        }
        atau kosong / None untuk list semua
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/address')

            if p:
                if "address" in p:
                    records = res.get(address=p["address"])
                elif "interface" in p:
                    records = res.get(interface=p["interface"])
                else:
                    records = res.get()
            else:
                records = res.get()

            results = []
            for r in records or []:
                results.append({
                    "id": r.get(".id") or r.get("id"),
                    "address": r.get("address"),
                    "interface": r.get("interface"),
                    "network": r.get("network"),
                    "disabled": r.get("disabled") == "true" or r.get("disabled") == "yes",
                    "comment": r.get("comment")
                })

            return results

        except Exception as e:
            logger(f"❌ List failed: {str(e)}")
            raise Exception(f"Failed to list addresses: {str(e)}")

        finally:
            pool.disconnect()

    def add_address(self, p, logger=print):
        """
        Add new IP address.
        Required parameters:
        {
            "address": "10.10.10.1/24",
            "interface": "ether1"
        }
        Optional: "comment"
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/address')

            # Cek apakah IP sudah ada di interface
            existing = res.get(interface=p["interface"])
            if existing:
                for rec in existing:
                    if rec.get("address") == p["address"]:
                        logger(f"⚠️ IP {p['address']} sudah ada di {p['interface']}, skip add.")
                        return

            # Tambahkan IP baru
            payload = {
                "address": p["address"],
                "interface": p["interface"]
            }
            if "comment" in p:
                payload["comment"] = p["comment"]

            res.add(**payload)
            logger(f"✅ Added new IP {p['address']} on {p['interface']}")

        except Exception as e:
            logger(f"❌ Add failed: {str(e)}")
            raise Exception(f"Failed to add address: {str(e)}")

        finally:
            pool.disconnect()

    def remove_address(self, p, logger=print):
        """
        Remove IP address by ID.
        
        Required parameters (choose one):
        {
            "id": "*1"  # Preferred method
        }
        or (backup method if ID not known):
        {
            "address": "10.10.10.1/24"
        }
        or
        {
            "interface": "ether1"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/address')

            # Determine the ID to use
            if "id" in p:
                record_id = p["id"]
                # Validate the ID exists
                self._get_by_id(res, record_id)
            else:
                # Get ID from address or interface
                address = p.get("address")
                interface = p.get("interface")
                record_id = self._get_id_from_address_interface(res, address, interface)

            # Remove the record
            res.remove(numbers=record_id)
            logger(f"🗑️ Removed IP Address ID {record_id}")

        except Exception as e:
            logger(f"❌ Remove failed: {str(e)}")
            raise Exception(f"Failed to remove address: {str(e)}")

        finally:
            pool.disconnect()

    def edit_address(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/address')

            if "id" in p:
                record_id = p["id"]
            else:
                if "address" not in p:
                    raise Exception("Either 'id' or 'address' must be provided")
                record_id = self._get_id_from_address_interface(
                    res,
                    address=p["address"],
                    interface=p.get("interface")
                )

            update_data = {"numbers": record_id}

            if "new_address" in p:
                update_data["address"] = p["new_address"]
            elif "address" in p and "id" in p:
                update_data["address"] = p["address"]

            if "interface" in p:
                update_data["interface"] = p["interface"]
            if "comment" in p:
                update_data["comment"] = p["comment"]

            res.set(**update_data)
            logger(f"✅ Updated IP Address ID {record_id}")

        except Exception as e:
            logger(f"❌ Edit failed: {str(e)}")
            raise Exception(f"Failed to edit address: {str(e)}")

        finally:
            pool.disconnect()

    def disable_address(self, p, logger=print):
        """
        Disable IP address by ID.
        
        Required parameters (choose one):
        {
            "id": "*1"  # Preferred method
        }
        or (backup method if ID not known):
        {
            "address": "10.10.10.1/24"
        }
        or
        {
            "interface": "ether1"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/address')

            # Determine the ID to use
            if "id" in p:
                record_id = p["id"]
                # Validate the ID exists
                self._get_by_id(res, record_id)
            else:
                # Get ID from address or interface
                address = p.get("address")
                interface = p.get("interface")
                record_id = self._get_id_from_address_interface(res, address, interface)

            # Disable the record
            res.set(numbers=record_id, disabled="yes")
            logger(f"🔴 Disabled IP Address ID {record_id}")

        except Exception as e:
            logger(f"❌ Disable failed: {str(e)}")
            raise Exception(f"Failed to disable address: {str(e)}")

        finally:
            pool.disconnect()

    def enable_address(self, p, logger=print):
        """
        Enable IP address by ID.
        
        Required parameters (choose one):
        {
            "id": "*1"  # Preferred method
        }
        or (backup method if ID not known):
        {
            "address": "10.10.10.1/24"
        }
        or
        {
            "interface": "ether1"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/address')

            # Determine the ID to use
            if "id" in p:
                record_id = p["id"]
                # Validate the ID exists
                self._get_by_id(res, record_id)
            else:
                # Get ID from address or interface
                address = p.get("address")
                interface = p.get("interface")
                record_id = self._get_id_from_address_interface(res, address, interface)

            # Enable the record
            res.set(numbers=record_id, disabled="no")
            logger(f"🟢 Enabled IP Address ID {record_id}")

        except Exception as e:
            logger(f"❌ Enable failed: {str(e)}")
            raise Exception(f"Failed to enable address: {str(e)}")

        finally:
            pool.disconnect()

    def comment_address(self, p, logger=print):
        """
        Update comment on IP address by ID.
        
        Required parameters (choose one):
        {
            "id": "*1",  # Preferred method
            "comment": "New comment"
        }
        or (backup method if ID not known):
        {
            "address": "10.10.10.1/24",
            "comment": "New comment"
        }
        or
        {
            "interface": "ether1",
            "comment": "New comment"
        }
        """
        pool, api = self.core.get_api()
        try:
            if "comment" not in p:
                raise Exception("Missing required parameter: comment")

            res = api.get_resource('/ip/address')

            # Determine the ID to use
            if "id" in p:
                record_id = p["id"]
                # Validate the ID exists
                self._get_by_id(res, record_id)
            else:
                # Get ID from address or interface
                address = p.get("address")
                interface = p.get("interface")
                record_id = self._get_id_from_address_interface(res, address, interface)

            # Update comment
            res.set(numbers=record_id, comment=p["comment"])
            logger(f"💬 Comment updated on IP Address ID {record_id}")

        except Exception as e:
            logger(f"❌ Comment update failed: {str(e)}")
            raise Exception(f"Failed to update comment: {str(e)}")

        finally:
            pool.disconnect()