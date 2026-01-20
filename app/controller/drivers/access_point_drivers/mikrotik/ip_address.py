class MikroTikAPIpDriver:
    name = "mikrotikapapi_ip"

    def __init__(self, core_driver):
        self.core = core_driver

    def add_address(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/address')

            # Cek apakah IP sudah ada di interface
            existing = res.get(interface=p["interface"])
            if existing:
                for rec in existing:
                    if rec.get("address") == p["address"]:
                        logger(f"⚠️ IP {p['address']} sudah ada di {p['interface']}, skip add.")
                        return  # keluar tanpa edit / add

            #  Kalau belum ada, tambahkan
            payload = {
                "address": p["address"],
                "interface": p["interface"]
            }
            if "comment" in p:
                payload["comment"] = p["comment"]

            res.add(**payload)
            logger(f"Added new IP {p['address']} on {p['interface']}")

        except Exception as e:
            logger(f"Add failed: {str(e)}")
            raise Exception(f"Failed to add address: {str(e)}")

        finally:
            pool.disconnect()

    def remove_address(self, p, logger=print):
        """
        Hapus IP Address tertentu dari interface.

        Contoh parameter:
        {
            "interface": "ether3",
            "address": "10.10.20.1/24"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/address')

            # 🎯 Cari record target berdasarkan address
            target = None

            if "address" in p:
                recs = res.get(address=p["address"])
                if recs:
                    target = recs[0]
            elif "interface" in p:
                recs = res.get(interface=p["interface"])
                if len(recs) == 1:
                    target = recs[0]
                else:
                    raise Exception(f"Multiple IPs found on {p['interface']}, specify 'address'")

            if not target:
                raise Exception(f"IP {p.get('address')} not found")

            # ✅ Ambil ID
            record_id = target.get(".id") or target.get("id")
            if not record_id:
                raise Exception("Record ID not found in API response")

            # 🧹 Hapus record
            res.remove(numbers=record_id)

            logger(f"🗑️ Removed IP {target['address']} from {target['interface']}")

        except Exception as e:
            logger(f"❌ Remove failed: {str(e)}")
            raise Exception(f"Failed to remove address: {str(e)}")

        finally:
            pool.disconnect()

    def edit_address(self, p, logger=print):
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/address')

            # Ambil semua IP address di interface
            records = res.get(interface=p["interface"])

            if not records:
                raise Exception(f"No IP found on interface {p['interface']}")

            # Kalau banyak IP di interface, harus tentukan old_address
            if len(records) > 1 and "old_address" not in p:
                available_ips = [r.get('address') for r in records]
                raise Exception(f"Multiple IPs found on {p['interface']}: {available_ips}. Specify 'old_address'")

            # Tentukan record target
            target_record = None
            if "old_address" in p:
                for r in records:
                    if r.get("address") == p["old_address"]:
                        target_record = r
                        break
            else:
                target_record = records[0]

            if not target_record:
                raise Exception(f"IP {p.get('old_address')} not found on interface {p['interface']}")

            # Ambil ID (gunakan fallback)
            record_id = target_record.get(".id") or target_record.get("id")
            if not record_id:
                # Fallback terakhir: ambil record via IP langsung biar pasti ada ID
                found = res.get(address=target_record["address"])
                if found and ".id" in found[0]:
                    record_id = found[0][".id"]
                elif found and "id" in found[0]:
                    record_id = found[0]["id"]
                else:
                    raise Exception("Record ID not found in API response")

            current_address = target_record.get("address")

            logger(f"Editing record: {current_address} -> {p.get('address')} (ID: {record_id})")

            # Siapkan payload update
            update_data = {}
            if "address" in p:
                update_data["address"] = p["address"]
            if "comment" in p:
                update_data["comment"] = p["comment"]

            # Jalankan update pakai numbers (bukan id)
            res.set(**{"numbers": record_id, **update_data})

            logger(f"Successfully updated IP on {p['interface']}")

        except Exception as e:
            logger(f"Edit failed: {str(e)}")
            raise Exception(f"Failed to update address: {str(e)}")

        finally:
            pool.disconnect()

    def disable_address(self, p, logger=print):
        """
        Nonaktifkan (disable) IP Address.
        Contoh parameter:
        {
            "interface": "ether3",
            "address": "10.10.10.1/24"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/address')

            # 🎯 Tentukan target record
            target = None
            if "address" in p:
                recs = res.get(address=p["address"])
                if recs:
                    target = recs[0]
            elif "interface" in p:
                recs = res.get(interface=p["interface"])
                if len(recs) == 1:
                    target = recs[0]
                else:
                    raise Exception(f"Multiple IPs found on {p['interface']}, specify 'address'")

            if not target:
                raise Exception(f"IP {p.get('address')} not found")

            record_id = target.get(".id") or target.get("id")
            if not record_id:
                raise Exception("Record ID not found")

            res.set(numbers=record_id, disabled="yes")
            logger(f"🚫 Disabled IP {target['address']} on {target['interface']}")

        except Exception as e:
            logger(f"❌ Disable failed: {str(e)}")
            raise Exception(f"Failed to disable address: {str(e)}")

        finally:
            pool.disconnect()

    def enable_address(self, p, logger=print):
        """
        Aktifkan (enable) IP Address.
        Contoh parameter:
        {
            "interface": "ether3",
            "address": "10.10.10.1/24"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/address')

            # 🎯 Cari record berdasarkan IP
            target = None
            if "address" in p:
                recs = res.get(address=p["address"])
                if recs:
                    target = recs[0]
            elif "interface" in p:
                recs = res.get(interface=p["interface"])
                if len(recs) == 1:
                    target = recs[0]
                else:
                    raise Exception(f"Multiple IPs found on {p['interface']}, specify 'address'")

            if not target:
                raise Exception(f"IP {p.get('address')} not found")

            record_id = target.get(".id") or target.get("id")
            if not record_id:
                raise Exception("Record ID not found")

            res.set(numbers=record_id, disabled="no")
            logger(f"✅ Enabled IP {target['address']} on {target['interface']}")

        except Exception as e:
            logger(f"❌ Enable failed: {str(e)}")
            raise Exception(f"Failed to enable address: {str(e)}")

        finally:
            pool.disconnect()

    def comment_address(self, p, logger=print):
        """
        Ubah atau tambahkan comment pada IP.
        Contoh parameter:
        {
            "interface": "ether3",
            "address": "10.10.10.1/24",
            "comment": "Edited by API"
        }
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource('/ip/address')

            # 🎯 Cari record berdasarkan address
            target = None
            if "address" in p:
                recs = res.get(address=p["address"])
                if recs:
                    target = recs[0]
            elif "interface" in p:
                recs = res.get(interface=p["interface"])
                if len(recs) == 1:
                    target = recs[0]
                else:
                    raise Exception(f"Multiple IPs found on {p['interface']}, specify 'address'")

            if not target:
                raise Exception(f"IP {p.get('address')} not found")

            record_id = target.get(".id") or target.get("id")
            if not record_id:
                raise Exception("Record ID not found")

            res.set(numbers=record_id, comment=p["comment"])
            logger(f"💬 Comment updated on {target['address']}: {p['comment']}")

        except Exception as e:
            logger(f"❌ Comment update failed: {str(e)}")
            raise Exception(f"Failed to update comment: {str(e)}")

        finally:
            pool.disconnect()
