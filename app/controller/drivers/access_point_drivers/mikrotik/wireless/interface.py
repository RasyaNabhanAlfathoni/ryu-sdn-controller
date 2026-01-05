class MikroTikAPWirelessInterfaceDriver:
    name = "mikrotikap_wireless_interface"

    def __init__(self, core):
        self.core = core
        
        # Mode yang tersedia di Mikrotik
        self.VALID_MODES = [
            "ap-bridge", "bridge", "station", "station-wds",
            "station-pseudobridge", "station-pseudobridge-clone",
            "wds-slave", "wds-master", "nv2-client", "nv2-ap"
        ]
        # Predefined valid options untuk beberapa field penting
        self.FIELD_OPTIONS = {
            "arp": ["disabled", "enabled", "local-proxy-arp", "proxy-arp", "reply-only"],
            "vlan_mode": ["no-tag", "use-tag", "use-service-tag"],
            "band": ["2ghz-b/g/n", "5ghz-a/n/ac", "2ghz-b/g", "5ghz-a/n"],
            "channel_width": ["20mhz", "20/40mhz", "40mhz", "80mhz", "160mhz"],
            "wds_mode": ["disabled", "static", "dynamic"],
            "tx_power_mode": ["default", "card-rates", "all-rates-fixed", "manual"],
            "antenna_mode": ["isotropic", "dipole", "custom"],
        }
        # Mode-specific required fields
        self.MODE_REQUIREMENTS = {
            "ap-bridge": ["ssid"],
            "bridge": ["ssid"],
            "wds-master": ["ssid"],
            "station": ["master_interface"],
            "station-wds": ["master_interface"],
            "station-pseudobridge": ["master_interface"],
            "station-pseudobridge-clone": ["master_interface"],
            "wds-slave": ["master_interface"],
        }

        self.RESOURCES = {
            "wireless": "/interface/wireless",
            "wds":      "/interface/wireless/wds",
            "nstreme":  "/interface/wireless/nstreme",
        }

    def list(self, p=None, logger=print):
        wtype = p.get("type", "wireless")
        if wtype not in self.RESOURCES:
            raise Exception("Invalid wireless type")
        pool, api = self.core.get_api()
        try:
            res = api.get_resource(self.RESOURCES[wtype])
            rows = res.get()

            data = []
            for idx, r in enumerate(rows):
                wireless_id = None
                
                if "id" in r:
                    wireless_id = r["id"]
                elif "name" in r and r["name"]:
                    wireless_id = f"wireless-{r['name']}"
                else:
                    wireless_id = f"wireless-{idx}"
                
                data.append({
                    "id": wireless_id,  # FIX: Jangan null lagi
                    
                    # Basic info
                    "name": r.get("name", ""),
                    "interface_type": r.get("interface-type", ""),
                    
                    # Status
                    "running": r.get("running", "") == "true",
                    "disabled": r.get("disabled", "") == "true",
                    
                    # Wireless settings
                    "mode": r.get("mode", ""),
                    "ssid": r.get("ssid", ""),
                    "frequency": r.get("frequency", ""),
                    "band": r.get("band", ""),
                    "channel_width": r.get("channel-width", ""),
                    "scan_list": r.get("scan-list", ""),
                    "wireless_protocol": r.get("wireless-protocol", ""),
                    
                    # VLAN settings
                    "vlan_mode": r.get("vlan-mode", ""),
                    "vlan_id": r.get("vlan-id", ""),
                    "bridge_mode": r.get("bridge-mode", ""),
                    
                    # WDS settings
                    "wds_mode": r.get("wds-mode", ""),
                    "wds_default_bridge": r.get("wds-default-bridge", ""),
                    "wds_ignore_ssid": r.get("wds-ignore-ssid", ""),
                    
                    # Security
                    "security_profile": r.get("security-profile", ""),
                    "hide_ssid": r.get("hide-ssid", "") == "true",
                    "default_authentication": r.get("default-authentication", "") == "true",
                    "default_forwarding": r.get("default-forwarding", "") == "true",
                    
                    # Limits
                    "default_ap_tx_limit": r.get("default-ap-tx-limit", ""),
                    "default_client_tx_limit": r.get("default-client-tx-limit", ""),
                    
                    # Network
                    "mtu": r.get("mtu", ""),
                    "l2mtu": r.get("l2mtu", ""),
                    "mac_address": r.get("mac-address", ""),
                    "arp": r.get("arp", ""),
                    "compression": r.get("compression", "") == "true",
                    "comment": r.get("comment", ""),
                    
                    "_original_data": r  # Hapus ini di production jika tidak perlu
                })

            logger(f"wireless.interface.list completed, found {len(data)} interfaces")
            return data

        finally:
            pool.disconnect()

    def enable(self, p, logger=print):
        wtype = p.get("type", "wireless")
        if wtype not in self.RESOURCES:
            raise Exception("Invalid wireless type")
        pool, api = self.core.get_api()
        try:
            res = api.get_resource(self.RESOURCES[wtype])
            
            # Cari interface berdasarkan name
            name = p.get("name")
            if not name:
                raise Exception("Interface name is required")
            
            recs = res.get(name=name)
            if not recs:
                raise Exception(f"Wireless interface '{name}' not found")
            
            record = recs[0]
            record_id = record.get(".id") or record.get("name")
            
            res.set(**{"numbers": record_id, "disabled": "no"})
            logger(f"Enabled wireless interface '{name}'")
            
            return {"status": "success", "interface": name, "action": "enabled"}
            
        except Exception as e:
            logger(f"Enable wireless interface failed: {str(e)}")
            raise Exception(f"Failed to enable wireless interface: {str(e)}")
        finally:
            pool.disconnect()

    def disable(self, p, logger=print):
        wtype = p.get("type", "wireless")
        if wtype not in self.RESOURCES:
            raise Exception("Invalid wireless type")
        pool, api = self.core.get_api()
        try:
            res = api.get_resource(self.RESOURCES[wtype])
            
            # Cari interface berdasarkan name
            name = p.get("name")
            if not name:
                raise Exception("Interface name is required")
            
            recs = res.get(name=name)
            if not recs:
                raise Exception(f"Wireless interface '{name}' not found")
            
            record = recs[0]
            record_id = record.get(".id") or record.get("name")
            
            res.set(**{"numbers": record_id, "disabled": "yes"})
            logger(f"Disabled wireless interface '{name}'")
            
            return {"status": "success", "interface": name, "action": "disabled"}
            
        except Exception as e:
            logger(f"Disable wireless interface failed: {str(e)}")
            raise Exception(f"Failed to disable wireless interface: {str(e)}")
        finally:
            pool.disconnect()

    def add_interface(self, p, logger=print):
        wtype = p.get("type", "wireless")
        if wtype not in self.RESOURCES:
            raise Exception("Invalid wireless type")
        pool, api = self.core.get_api()
        try:
            res = api.get_resource(self.RESOURCES[wtype])
            
            # === VALIDASI DASAR ===
            if not p.get("name"):
                raise Exception("Interface name is required")
            
            mode = p.get("mode", "ap-bridge")
            if mode not in self.VALID_MODES:
                raise Exception(f"Invalid mode. Must be one of: {', '.join(self.VALID_MODES)}")
            
            # Check if interface already exists
            existing = res.get(name=p["name"])
            if existing:
                raise Exception(f"Interface '{p['name']}' already exists")
            
            # === VALIDASI MODE-SPECIFIC ===
            if mode in self.MODE_REQUIREMENTS:
                for required_field in self.MODE_REQUIREMENTS[mode]:
                    if required_field not in p and required_field.replace('_', '-') not in p:
                        raise Exception(f"Field '{required_field}' is required for mode '{mode}'")
            
            # === BUILD MIKROTIK PAYLOAD ===
            mikrotik_payload = {}
            
            # Process all parameters
            for key, value in p.items():
                # Skip internal flags
                if key.startswith('_'):
                    continue
                
                # Convert value to Mikrotik format
                processed = self._process_parameter(key, value, logger)
                if processed:
                    mikrotik_key, mikrotik_value = processed
                    mikrotik_payload[mikrotik_key] = mikrotik_value
            
            # === ADD REQUIRED FIELDS IF MISSING ===
            if "name" not in mikrotik_payload:
                mikrotik_payload["name"] = p["name"]
            
            if "mode" not in mikrotik_payload:
                mikrotik_payload["mode"] = mode
            
            # === DEBUG LOGGING ===
            logger(f"Creating wireless interface '{p['name']}' with mode '{mode}'")
            logger(f"Total parameters to set: {len(mikrotik_payload)}")
            
            if len(mikrotik_payload) > 20:
                logger(f"First 20 parameters: {dict(list(mikrotik_payload.items())[:20])}")
            
            # === CREATE INTERFACE ===
            result = res.add(**mikrotik_payload)
            
            # === VERIFY CREATION ===
            created = res.get(name=p["name"])
            
            logger(f"Wireless interface '{p['name']}' created successfully")
            return {
                "status": "success",
                "interface": p["name"],
                "mode": mode,
                "parameters_set": len(mikrotik_payload),
                "result": result,
                "details": created[0] if created else {}
            }
            
        except Exception as e:
            logger(f"Failed to create wireless interface: {str(e)}")
            import traceback
            logger(f"Traceback: {traceback.format_exc()}")
            raise Exception(f"Failed to create wireless interface: {str(e)}")
        finally:
            pool.disconnect()

    def edit_interface(self, p, logger=print):
        wtype = p.get("type", "wireless")
        if wtype not in self.RESOURCES:
            raise Exception("Invalid wireless type")
        pool, api = self.core.get_api()
        try:
            res = api.get_resource(self.RESOURCES[wtype])
            rows = res.get()
            
            if not p.get("name"):
                raise Exception("Interface name is required")
            
            name = p["name"]
            
            # Check if interface exists
            recs = res.get(name=name)
            if not recs:
                raise Exception(f"Wireless interface '{name}' not found")
            
            record = recs[0]
            record_id = record.get(".id") or name
            
            # Build update payload
            update_payload = {}
            
            # Mapping from our field names to Mikrotik field names
            field_mapping = {
                "mtu": "mtu",
                "l2mtu": "l2mtu",
                "mac_address": "mac-address",
                "arp": "arp",
                "arp_timeout": "arp-timeout",
                "mode": "mode",
                "ssid": "ssid",
                "master_interface": "master-interface",
                "security_profile": "security-profile",
                "wps_mode": "wps-mode",
                "vlan_mode": "vlan-mode",
                "vlan_id": "vlan-id",
                "default_ap_tx_rate": "default-ap-tx-rate",
                "default_client_tx_rate": "default-client-tx-rate",
                "default_authenticate": "default-authenticate",
                "default_forward": "default-forward",
                "hide_ssid": "hide-ssid",
                "wds_mode": "wds-mode",
                "wds_default_bridge": "wds-default-bridge",
                "wds_ignore_ssid": "wds-ignore-ssid",
                "comment": "comment"
            }
            
            for our_field, mikrotik_field in field_mapping.items():
                if our_field in p and our_field != "name":
                    # Convert boolean to Mikrotik format
                    if isinstance(p[our_field], bool):
                        update_payload[mikrotik_field] = "yes" if p[our_field] else "no"
                    else:
                        update_payload[mikrotik_field] = str(p[our_field])
            
            if not update_payload:
                raise Exception("No fields to update")
            
            # Perform update
            res.set(**{"numbers": record_id, **update_payload})
            
            logger(f"Wireless interface '{name}' updated successfully")
            return {
                "status": "success",
                "interface": name,
                "updated_fields": list(update_payload.keys())
            }
            
        except Exception as e:
            logger(f"Failed to edit wireless interface: {str(e)}")
            raise Exception(f"Failed to edit wireless interface: {str(e)}")
        finally:
            pool.disconnect()

    def delete_interface(self, p, logger=print):
        wtype = p.get("type", "wireless")
        if wtype not in self.RESOURCES:
            raise Exception("Invalid wireless type")
        pool, api = self.core.get_api()
        try:
            res = api.get_resource(self.RESOURCES[wtype])
            rows = res.get()
            
            if not p.get("name"):
                raise Exception("Interface name is required")
            
            name = p["name"]
            
            # Check if interface exists
            recs = res.get(name=name)
            if not recs:
                raise Exception(f"Wireless interface '{name}' not found")
            
            record = recs[0]
            record_id = record.get(".id") or name
            
            res.remove(numbers=record_id)
            logger(f"Wireless interface '{name}' deleted successfully")
            
            return {"status": "success", "interface": name, "action": "deleted"}
            
        except Exception as e:
            logger(f"Failed to delete wireless interface: {str(e)}")
            raise Exception(f"Failed to delete wireless interface: {str(e)}")
        finally:
            pool.disconnect()

    def get_available_parameters(self, p=None, logger=print):
        """
        Get list of all available parameters for wireless interface.
        This can be used by frontend to build dynamic forms.
        
        Returns categorized parameters with metadata.
        """
        # This is a simplified version. In production, you might want to
        # dynamically fetch this from Mikrotik API or maintain a comprehensive list
        
        parameters = {
            "general": {
                "name": {"type": "string", "required": True, "description": "Interface name"},
                "mtu": {"type": "integer", "default": 1500, "range": [68, 65535]},
                "l2mtu": {"type": "integer", "default": 1600, "range": [576, 65535]},
                "mac-address": {"type": "mac", "description": "MAC address"},
                "arp": {"type": "select", "options": self.FIELD_OPTIONS["arp"], "default": "enabled"},
                "arp-timeout": {"type": "time", "default": "00:00:30"},
                "comment": {"type": "string", "description": "Interface comment"},
                "disabled": {"type": "boolean", "default": False},
            },
            "wireless_basic": {
                "mode": {"type": "select", "options": self.VALID_MODES, "required": True},
                "ssid": {"type": "string", "description": "Network name"},
                "band": {"type": "select", "options": self.FIELD_OPTIONS["band"], "default": "2ghz-b/g/n"},
                "frequency": {"type": "string", "description": "Frequency in MHz"},
                "channel-width": {"type": "select", "options": self.FIELD_OPTIONS["channel_width"], "default": "20mhz"},
                "scan-list": {"type": "string", "default": "default"},
                "wireless-protocol": {"type": "string", "default": "802.11"},
                "country": {"type": "string", "default": "indonesia"},
            },
            "security": {
                "security-profile": {"type": "string", "default": "default"},
                "wps-mode": {"type": "select", "options": ["disabled", "push-button", "pin"], "default": "disabled"},
                "hide-ssid": {"type": "boolean", "default": False},
                "default-authentication": {"type": "boolean", "default": True},
                "default-forwarding": {"type": "boolean", "default": True},
            },
            "advanced": {
                "tx-power": {"type": "integer", "range": [0, 30], "description": "Transmit power in dBm"},
                "tx-power-mode": {"type": "select", "options": self.FIELD_OPTIONS["tx_power_mode"], "default": "default"},
                "antenna-mode": {"type": "select", "options": self.FIELD_OPTIONS["antenna_mode"], "default": "isotropic"},
                "antenna-gain": {"type": "integer", "range": [0, 30], "default": 0},
                "distance": {"type": "string", "default": "0"},
                "rx-chains": {"type": "string", "default": "0,1,2"},
                "tx-chains": {"type": "string", "default": "0,1,2"},
            },
            "vlan": {
                "vlan-mode": {"type": "select", "options": self.FIELD_OPTIONS["vlan_mode"], "default": "no-tag"},
                "vlan-id": {"type": "integer", "range": [1, 4095]},
                "bridge-mode": {"type": "string", "default": "enabled"},
            },
            "wds": {
                "wds-mode": {"type": "select", "options": self.FIELD_OPTIONS["wds_mode"], "default": "disabled"},
                "wds-default-bridge": {"type": "string"},
                "wds-default-cost": {"type": "integer", "default": 100},
                "wds-cost-range": {"type": "string", "default": "50-150"},
                "wds-ignore-ssid": {"type": "boolean", "default": False},
            }
        }
        
        return parameters