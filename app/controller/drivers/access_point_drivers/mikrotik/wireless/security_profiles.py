class MikroTikAPWirelessSecurityDriver:
    name = "mikrotikap_wireless_security"

    def __init__(self, core):
        self.core = core
        
        # Mode yang tersedia untuk security profile
        self.VALID_MODES = [
            "dynamic-keys", "static-keys-optional", 
            "static-keys-required", "none"
        ]
        
        # Authentication types
        self.AUTH_TYPES = [
            "wpa-psk", "wpa2-psk", "wpa-eap", "wpa2-eap",
            "wpa3", "wpa3-192-bit", "owe", "sae"
        ]
        
        # EAP methods
        self.EAP_METHODS = [
            "eap-tls", "eap-ttls", "peap", "fast"
        ]
        
        # Cipher types
        self.CIPHER_TYPES = [
            "tkip", "aes-ccm", "gcmp", "gcmp-256", "ccmp-256"
        ]
        
        # TLS modes
        self.TLS_MODES = [
            "no-certificates", "verify-certificate", 
            "dont-verify-certificate", "verify-certificate-with-crl"
        ]
        
        # Radius MAC format
        self.RADIUS_MAC_FORMATS = [
            "00:11:22:33:44:55", "00-11-22-33-44-55",
            "0011.2233.4455", "001122334455"
        ]
        
        # Resource path
        self.RESOURCE = "/interface/wireless/security-profiles"

    def list(self, p=None, logger=print):
        """List all security profiles"""
        pool, api = self.core.get_api()
        try:
            res = api.get_resource(self.RESOURCE)
            rows = res.get()
            
            data = []
            for idx, r in enumerate(rows):
                profile_id = r.get(".id") or r.get("name") or f"profile-{idx}"
                
                # Parse authentication types (string to list)
                auth_types_str = r.get("authentication-types", "")
                auth_types = auth_types_str.split(",") if auth_types_str else []
                
                # Parse unicast ciphers
                unicast_ciphers_str = r.get("unicast-ciphers", "")
                unicast_ciphers = unicast_ciphers_str.split(",") if unicast_ciphers_str else []
                
                # Parse group ciphers
                group_ciphers_str = r.get("group-ciphers", "")
                group_ciphers = group_ciphers_str.split(",") if group_ciphers_str else []
                
                # Parse eap methods
                eap_methods_str = r.get("eap-methods", "")
                eap_methods = eap_methods_str.split(",") if eap_methods_str else []
                
                # Parse static keys
                static_keys = {}
                for i in range(4):
                    key = r.get(f"static-key-{i}", "")
                    if key:
                        static_keys[f"key_{i}"] = {
                            "key": key,
                            "default": r.get(f"static-key-{i}-default", "") == "true",
                            "transmit": r.get(f"static-key-{i}-transmit", "") == "true"
                        }
                
                profile_data = {
                    "id": profile_id,
                    "name": r.get("name", ""),
                    "mode": r.get("mode", ""),
                    
                    # Authentication settings
                    "authentication_types": auth_types,
                    "wpa_pre_shared_key": r.get("wpa-pre-shared-key", ""),
                    "wpa2_pre_shared_key": r.get("wpa2-pre-shared-key", ""),
                    
                    # Ciphers
                    "unicast_ciphers": unicast_ciphers,
                    "group_ciphers": group_ciphers,
                    
                    # EAP settings
                    "eap_methods": eap_methods,
                    "mschapv2_username": r.get("mschapv2-username", ""),
                    "mschapv2_password": r.get("mschapv2-password", ""),
                    "supplicant_identity": r.get("supplicant-identity", ""),
                    
                    # Static keys (for static-keys mode)
                    "static_keys": static_keys if static_keys else None,
                    
                    # Group key settings
                    "group_key_update": r.get("group-key-update", ""),
                    "disable_pmkid": r.get("disable-pmkid", "") == "true",
                    
                    # Management protection
                    "management_protection": r.get("management-protection", ""),
                    "management_protection_key": r.get("management-protection-key", ""),
                    
                    # RADIUS settings
                    "radius_eap_accounting": r.get("radius-eap-accounting", "") == "true",
                    "radius_mac_accounting": r.get("radius-mac-accounting", "") == "true",
                    "radius_mac_format": r.get("radius-mac-format", ""),
                    "radius_mac_mode": r.get("radius-mac-mode", ""),
                    "radius_mac_cache": r.get("radius-mac-cache", ""),
                    
                    # TLS settings
                    "tls_mode": r.get("tls-mode", ""),
                    "tls_certificate": r.get("tls-certificate", ""),
                    
                    # Other
                    "interim_update": r.get("interim-update", ""),
                    "comment": r.get("comment", ""),
                    "default": r.get("default", "") == "true",
                    
                    "_original_data": r
                }
                
                data.append(profile_data)
            
            logger(f"wireless.security.list completed, found {len(data)} profiles")
            return data
            
        finally:
            pool.disconnect()

    def add_profile(self, p, logger=print):
        """Add new security profile"""
        pool, api = self.core.get_api()
        try:
            res = api.get_resource(self.RESOURCE)
            
            # Validasi dasar
            if not p.get("name"):
                raise Exception("Profile name is required")
            
            # Cek apakah profile sudah ada
            existing = res.get(name=p["name"])
            if existing:
                raise Exception(f"Security profile '{p['name']}' already exists")
            
            # Mode validation
            mode = p.get("mode", "dynamic-keys")
            if mode not in self.VALID_MODES:
                raise Exception(f"Invalid mode. Must be one of: {', '.join(self.VALID_MODES)}")
            
            # Build Mikrotik payload
            mikrotik_payload = {"name": p["name"], "mode": mode}
            
            # Process authentication types (list to string)
            if "authentication_types" in p:
                if isinstance(p["authentication_types"], list):
                    mikrotik_payload["authentication-types"] = ",".join(p["authentication_types"])
                else:
                    mikrotik_payload["authentication-types"] = str(p["authentication_types"])
            
            # Process ciphers
            if "unicast_ciphers" in p and isinstance(p["unicast_ciphers"], list):
                mikrotik_payload["unicast-ciphers"] = ",".join(p["unicast_ciphers"])
            
            if "group_ciphers" in p and isinstance(p["group_ciphers"], list):
                mikrotik_payload["group-ciphers"] = ",".join(p["group_ciphers"])
            
            # Process EAP methods
            if "eap_methods" in p and isinstance(p["eap_methods"], list):
                mikrotik_payload["eap-methods"] = ",".join(p["eap_methods"])
            
            # Static keys (for static-keys mode)
            if mode in ["static-keys-optional", "static-keys-required"]:
                for i in range(4):
                    key_field = f"static_key_{i}"
                    if key_field in p:
                        mikrotik_payload[f"static-key-{i}"] = p[key_field]
                    
                    # Optional: set default and transmit flags
                    default_field = f"static_key_{i}_default"
                    transmit_field = f"static_key_{i}_transmit"
                    
                    if default_field in p:
                        mikrotik_payload[f"static-key-{i}-default"] = "yes" if p[default_field] else "no"
                    if transmit_field in p:
                        mikrotik_payload[f"static-key-{i}-transmit"] = "yes" if p[transmit_field] else "no"
            
            # Pre-shared keys (for dynamic-keys mode)
            if "wpa_pre_shared_key" in p:
                mikrotik_payload["wpa-pre-shared-key"] = p["wpa_pre_shared_key"]
            if "wpa2_pre_shared_key" in p:
                mikrotik_payload["wpa2-pre-shared-key"] = p["wpa2_pre_shared_key"]
            
            # MSCHAPv2 credentials
            if "mschapv2_username" in p:
                mikrotik_payload["mschapv2-username"] = p["mschapv2_username"]
            if "mschapv2_password" in p:
                mikrotik_payload["mschapv2-password"] = p["mschapv2_password"]
            
            # Supplicant identity
            if "supplicant_identity" in p:
                mikrotik_payload["supplicant-identity"] = p["supplicant_identity"]
            
            # Group key update
            if "group_key_update" in p:
                mikrotik_payload["group-key-update"] = p["group_key_update"]
            
            # PMKID
            if "disable_pmkid" in p:
                mikrotik_payload["disable-pmkid"] = "yes" if p["disable_pmkid"] else "no"
            
            # Management protection
            if "management_protection" in p:
                mikrotik_payload["management-protection"] = p["management_protection"]
            if "management_protection_key" in p:
                mikrotik_payload["management-protection-key"] = p["management_protection_key"]
            
            # RADIUS settings
            if "radius_eap_accounting" in p:
                mikrotik_payload["radius-eap-accounting"] = "yes" if p["radius_eap_accounting"] else "no"
            if "radius_mac_accounting" in p:
                mikrotik_payload["radius-mac-accounting"] = "yes" if p["radius_mac_accounting"] else "no"
            if "radius_mac_format" in p:
                mikrotik_payload["radius-mac-format"] = p["radius_mac_format"]
            if "radius_mac_mode" in p:
                mikrotik_payload["radius-mac-mode"] = p["radius_mac_mode"]
            if "radius_mac_cache" in p:
                mikrotik_payload["radius-mac-cache"] = p["radius_mac_cache"]
            
            # TLS settings
            if "tls_mode" in p:
                mikrotik_payload["tls-mode"] = p["tls_mode"]
            if "tls_certificate" in p:
                mikrotik_payload["tls-certificate"] = p["tls_certificate"]
            
            # Interim update
            if "interim_update" in p:
                mikrotik_payload["interim-update"] = p["interim_update"]
            
            # Comment
            if "comment" in p:
                mikrotik_payload["comment"] = p["comment"]
            
            # Default profile
            if "default" in p:
                mikrotik_payload["default"] = "yes" if p["default"] else "no"
            
            # Create the profile
            result = res.add(**mikrotik_payload)
            
            # Verify creation
            created = res.get(name=p["name"])
            
            logger(f"Security profile '{p['name']}' created successfully")
            return {
                "status": "success",
                "profile": p["name"],
                "mode": mode,
                "parameters_set": len(mikrotik_payload),
                "result": result,
                "details": created[0] if created else {}
            }
            
        except Exception as e:
            logger(f"Failed to create security profile: {str(e)}")
            import traceback
            logger(f"Traceback: {traceback.format_exc()}")
            raise Exception(f"Failed to create security profile: {str(e)}")
        finally:
            pool.disconnect()

    def edit_profile(self, p, logger=print):
        """Edit existing security profile"""
        pool, api = self.core.get_api()
        try:
            res = api.get_resource(self.RESOURCE)
            
            if not p.get("name"):
                raise Exception("Profile name is required")
            
            name = p["name"]
            
            # Cek apakah profile ada
            recs = res.get(name=name)
            if not recs:
                raise Exception(f"Security profile '{name}' not found")
            
            record = recs[0]
            record_id = record.get(".id") or name
            
            # Build update payload
            update_payload = {}
            
            # Mapping field names
            field_mapping = {
                "mode": "mode",
                "authentication_types": "authentication-types",
                "wpa_pre_shared_key": "wpa-pre-shared-key",
                "wpa2_pre_shared_key": "wpa2-pre-shared-key",
                "unicast_ciphers": "unicast-ciphers",
                "group_ciphers": "group-ciphers",
                "eap_methods": "eap-methods",
                "mschapv2_username": "mschapv2-username",
                "mschapv2_password": "mschapv2-password",
                "supplicant_identity": "supplicant-identity",
                "group_key_update": "group-key-update",
                "disable_pmkid": "disable-pmkid",
                "management_protection": "management-protection",
                "management_protection_key": "management-protection-key",
                "radius_eap_accounting": "radius-eap-accounting",
                "radius_mac_accounting": "radius-mac-accounting",
                "radius_mac_format": "radius-mac-format",
                "radius_mac_mode": "radius-mac-mode",
                "radius_mac_cache": "radius-mac-cache",
                "tls_mode": "tls-mode",
                "tls_certificate": "tls-certificate",
                "interim_update": "interim-update",
                "comment": "comment",
                "default": "default"
            }
            
            for our_field, mikrotik_field in field_mapping.items():
                if our_field in p:
                    # Convert list to comma-separated string
                    if our_field in ["authentication_types", "unicast_ciphers", 
                                   "group_ciphers", "eap_methods"]:
                        if isinstance(p[our_field], list):
                            update_payload[mikrotik_field] = ",".join(p[our_field])
                        else:
                            update_payload[mikrotik_field] = str(p[our_field])
                    # Convert boolean to yes/no
                    elif our_field in ["disable_pmkid", "radius_eap_accounting", 
                                     "radius_mac_accounting", "default"]:
                        update_payload[mikrotik_field] = "yes" if p[our_field] else "no"
                    else:
                        update_payload[mikrotik_field] = str(p[our_field])
            
            # Static keys update (if provided)
            for i in range(4):
                key_field = f"static_key_{i}"
                if key_field in p:
                    update_payload[f"static-key-{i}"] = p[key_field]
                
                default_field = f"static_key_{i}_default"
                transmit_field = f"static_key_{i}_transmit"
                
                if default_field in p:
                    update_payload[f"static-key-{i}-default"] = "yes" if p[default_field] else "no"
                if transmit_field in p:
                    update_payload[f"static-key-{i}-transmit"] = "yes" if p[transmit_field] else "no"
            
            if not update_payload:
                raise Exception("No fields to update")
            
            # Perform update
            res.set(**{"numbers": record_id, **update_payload})
            
            logger(f"Security profile '{name}' updated successfully")
            return {
                "status": "success",
                "profile": name,
                "updated_fields": list(update_payload.keys())
            }
            
        except Exception as e:
            logger(f"Failed to edit security profile: {str(e)}")
            raise Exception(f"Failed to edit security profile: {str(e)}")
        finally:
            pool.disconnect()

    def delete_profile(self, p, logger=print):
        """Delete security profile"""
        pool, api = self.core.get_api()
        try:
            res = api.get_resource(self.RESOURCE)
            
            if not p.get("name"):
                raise Exception("Profile name is required")
            
            name = p["name"]
            
            # Check if profile exists and is not default
            recs = res.get(name=name)
            if not recs:
                raise Exception(f"Security profile '{name}' not found")
            
            record = recs[0]
            if record.get("default") == "true":
                raise Exception(f"Cannot delete default profile '{name}'")
            
            record_id = record.get(".id") or name
            res.remove(numbers=record_id)
            
            logger(f"Security profile '{name}' deleted successfully")
            return {"status": "success", "profile": name, "action": "deleted"}
            
        except Exception as e:
            logger(f"Failed to delete security profile: {str(e)}")
            raise Exception(f"Failed to delete security profile: {str(e)}")
        finally:
            pool.disconnect()

    def get_available_parameters(self, p=None, logger=print):
        """Get all available parameters for security profiles"""
        parameters = {
            "general": {
                "name": {"type": "string", "required": True, "description": "Profile name"},
                "mode": {"type": "select", "options": self.VALID_MODES, "required": True},
                "comment": {"type": "string", "description": "Profile description"},
                "default": {"type": "boolean", "default": False, "description": "Set as default profile"},
            },
            "authentication": {
                "authentication_types": {
                    "type": "multiselect", 
                    "options": self.AUTH_TYPES,
                    "description": "Authentication types to enable"
                },
                "wpa_pre_shared_key": {"type": "password", "description": "WPA pre-shared key"},
                "wpa2_pre_shared_key": {"type": "password", "description": "WPA2 pre-shared key"},
                "disable_pmkid": {"type": "boolean", "default": False, "description": "Disable PMKID"},
            },
            "ciphers": {
                "unicast_ciphers": {"type": "multiselect", "options": self.CIPHER_TYPES},
                "group_ciphers": {"type": "multiselect", "options": self.CIPHER_TYPES},
            },
            "eap_settings": {
                "eap_methods": {"type": "multiselect", "options": self.EAP_METHODS},
                "mschapv2_username": {"type": "string", "description": "MSCHAPv2 username"},
                "mschapv2_password": {"type": "password", "description": "MSCHAPv2 password"},
                "supplicant_identity": {"type": "string", "description": "Supplicant identity"},
            },
            "static_keys": {
                "static_key_0": {"type": "password", "description": "Static key 0"},
                "static_key_1": {"type": "password", "description": "Static key 1"},
                "static_key_2": {"type": "password", "description": "Static key 2"},
                "static_key_3": {"type": "password", "description": "Static key 3"},
                "static_key_0_default": {"type": "boolean", "description": "Set key 0 as default"},
                "static_key_0_transmit": {"type": "boolean", "description": "Transmit key 0"},
            },
            "group_key": {
                "group_key_update": {"type": "time", "default": "00:05:00", "description": "Group key update interval"},
            },
            "management_protection": {
                "management_protection": {"type": "string", "description": "Management protection type"},
                "management_protection_key": {"type": "password", "description": "Management protection key"},
            },
            "radius": {
                "radius_eap_accounting": {"type": "boolean", "default": False, "description": "Enable RADIUS EAP accounting"},
                "radius_mac_accounting": {"type": "boolean", "default": False, "description": "Enable RADIUS MAC accounting"},
                "radius_mac_format": {"type": "select", "options": self.RADIUS_MAC_FORMATS, "description": "MAC address format for RADIUS"},
                "radius_mac_mode": {"type": "string", "description": "RADIUS MAC mode"},
                "radius_mac_cache": {"type": "time", "description": "RADIUS MAC cache timeout"},
                "interim_update": {"type": "time", "description": "Interim update interval"},
            },
            "tls": {
                "tls_mode": {"type": "select", "options": self.TLS_MODES, "description": "TLS certificate verification mode"},
                "tls_certificate": {"type": "string", "description": "TLS certificate name"},
            }
        }
        
        return parameters