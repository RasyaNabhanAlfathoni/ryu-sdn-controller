class MikroTikAPWirelessRegistrationDriver:
    name = "mikrotikap_wireless_registration"

    def __init__(self, core):
        self.core = core
        
        # Resource paths
        self.RESOURCES = {
            "registration": "/interface/wireless/registration-table",
            "wireless": "/interface/wireless"
        }

    def registration_list(self, p=None, logger=print):
        """
        Get list of connected wireless clients (registration table)
        """
        pool, api = self.core.get_api()
        try:
            res = api.get_resource(self.RESOURCES["registration"])
            rows = res.get()
            
            data = []
            for idx, r in enumerate(rows):
                client_data = {
                    "id": r.get(".id") or f"client-{idx}",
                    
                    # Basic client info
                    "interface": r.get("interface", ""),
                    "mac_address": r.get("mac-address", ""),
                    "radio_name": r.get("radio-name", ""),
                    "uptime": r.get("uptime", ""),
                    "ap": r.get("ap", "") == "true",
                    
                    # Activity
                    "last_activity": r.get("last-activity", ""),
                    "last_ip": r.get("last-ip", ""),
                    
                    # Signal information
                    "rx_signal": r.get("rx-signal", ""),
                    "tx_signal": r.get("tx-signal", ""),
                    "signal_strength": r.get("signal-strength", ""),
                    "signal_to_noise": r.get("signal-to-noise", ""),
                    
                    # Rate information
                    "rx_rate": r.get("rx-rate", ""),
                    "tx_rate": r.get("tx-rate", ""),
                    "rx_ccq": r.get("rx-ccq", ""),
                    "tx_ccq": r.get("tx-ccq", ""),
                    
                    # Connection details
                    "frames": r.get("frames", ""),
                    "bytes": r.get("bytes", ""),
                    "packets": r.get("packets", ""),
                    "tx_frames_timed_out": r.get("tx-frames-timed-out", ""),
                    "uptime_seconds": r.get("uptime-seconds", ""),
                    
                    # Authentication
                    "authenticated": r.get("authenticated", "") == "true",
                    "encryption": r.get("encryption", ""),
                    "group_encryption": r.get("group-encryption", ""),
                    
                    # WMM
                    "wmm_enabled": r.get("wmm-enabled", "") == "true",
                    "tx_priority": r.get("tx-priority", ""),
                    
                    # Bandwidth
                    "rate_set": r.get("rate-set", ""),
                    "distance": r.get("distance", ""),
                    "ack_timeout": r.get("ack-timeout", ""),
                    
                    # Bridge
                    "bridge_port": r.get("bridge-port", ""),
                    "bridge": r.get("bridge", ""),
                    
                    "_original_data": r
                }
                
                # Calculate human-readable values
                if client_data["uptime_seconds"]:
                    client_data["uptime_human"] = self._seconds_to_human(
                        int(client_data["uptime_seconds"])
                    )
                
                # Parse signal strength (convert to percentage if needed)
                if client_data["signal_strength"]:
                    try:
                        signal = int(client_data["signal_strength"])
                        # Convert from dBm to percentage (approx)
                        if signal <= -100:
                            client_data["signal_percentage"] = 0
                        elif signal >= -50:
                            client_data["signal_percentage"] = 100
                        else:
                            client_data["signal_percentage"] = 2 * (signal + 100)
                    except:
                        client_data["signal_percentage"] = 0
                
                data.append(client_data)
            
            logger(f"Wireless registration list completed, found {len(data)} clients")
            return data
            
        finally:
            pool.disconnect()

    def reset(self, p=None, logger=print):
        """
        Reset wireless interface counters or registration table
        
        Parameters:
        - type: "counters" or "registration" or "interface"
        - interface: Interface name (optional, if not provided resets all)
        - mac_address: Specific MAC address to reset (optional)
        """
        pool, api = self.core.get_api()
        try:
            reset_type = p.get("type", "counters").lower()
            interface = p.get("interface")
            mac_address = p.get("mac_address")
            
            result = {}
            
            if reset_type == "counters":
                # Reset interface counters
                if interface:
                    # Reset specific interface
                    res = api.get_resource(self.RESOURCES["wireless"])
                    recs = res.get(name=interface)
                    if not recs:
                        raise Exception(f"Interface '{interface}' not found")
                    
                    record = recs[0]
                    record_id = record.get(".id") or interface
                    
                    # Reset counters
                    res.reset_counters(numbers=record_id)
                    logger(f"Reset counters for interface '{interface}'")
                    result = {
                        "status": "success",
                        "action": "reset_counters",
                        "interface": interface
                    }
                else:
                    # Reset all wireless interfaces counters
                    res = api.get_resource(self.RESOURCES["wireless"])
                    res.reset_counters()
                    logger("Reset counters for all wireless interfaces")
                    result = {
                        "status": "success",
                        "action": "reset_all_counters"
                    }
                    
            elif reset_type == "registration":
                # Clear registration table (disconnect clients)
                if interface and mac_address:
                    # Disconnect specific client
                    reg_res = api.get_resource(self.RESOURCES["registration"])
                    
                    # Find the client
                    clients = reg_res.get(
                        interface=interface,
                        mac_address=mac_address
                    )
                    
                    if not clients:
                        raise Exception(f"Client {mac_address} not found on {interface}")
                    
                    client_id = clients[0].get(".id")
                    reg_res.remove(numbers=client_id)
                    
                    logger(f"Disconnected client {mac_address} from {interface}")
                    result = {
                        "status": "success",
                        "action": "disconnect_client",
                        "interface": interface,
                        "mac_address": mac_address
                    }
                    
                elif interface:
                    # Disconnect all clients from specific interface
                    reg_res = api.get_resource(self.RESOURCES["registration"])
                    clients = reg_res.get(interface=interface)
                    
                    if clients:
                        for client in clients:
                            client_id = client.get(".id")
                            if client_id:
                                reg_res.remove(numbers=client_id)
                    
                    logger(f"Disconnected all clients from interface '{interface}'")
                    result = {
                        "status": "success",
                        "action": "disconnect_all_clients",
                        "interface": interface,
                        "clients_disconnected": len(clients)
                    }
                    
                else:
                    # Clear entire registration table
                    reg_res = api.get_resource(self.RESOURCES["registration"])
                    all_clients = reg_res.get()
                    
                    if all_clients:
                        for client in all_clients:
                            client_id = client.get(".id")
                            if client_id:
                                reg_res.remove(numbers=client_id)
                    
                    logger("Cleared entire wireless registration table")
                    result = {
                        "status": "success",
                        "action": "clear_all_registration",
                        "clients_disconnected": len(all_clients)
                    }
                    
            elif reset_type == "interface":
                # Reset/reinitialize wireless interface
                if not interface:
                    raise Exception("Interface name is required for interface reset")
                
                res = api.get_resource(self.RESOURCES["wireless"])
                recs = res.get(name=interface)
                if not recs:
                    raise Exception(f"Interface '{interface}' not found")
                
                record = recs[0]
                record_id = record.get(".id") or interface
                
                # Disable then enable
                res.set(**{"numbers": record_id, "disabled": "yes"})
                import time
                time.sleep(2)  # Wait 2 seconds
                res.set(**{"numbers": record_id, "disabled": "no"})
                
                logger(f"Reset interface '{interface}' (disabled and re-enabled)")
                result = {
                    "status": "success",
                    "action": "interface_reset",
                    "interface": interface
                }
                
            else:
                raise Exception(f"Invalid reset type. Must be: counters, registration, or interface")
            
            return result
            
        except Exception as e:
            logger(f"Reset operation failed: {str(e)}")
            raise Exception(f"Reset operation failed: {str(e)}")
        finally:
            pool.disconnect()

    def get_client_details(self, p, logger=print):
        """
        Get detailed information about a specific client
        """
        pool, api = self.core.get_api()
        try:
            if not p.get("mac_address"):
                raise Exception("MAC address is required")
            
            mac_address = p["mac_address"]
            interface = p.get("interface")
            
            res = api.get_resource(self.RESOURCES["registration"])
            
            # Build query
            query = {"mac-address": mac_address}
            if interface:
                query["interface"] = interface
            
            clients = res.get(**query)
            
            if not clients:
                raise Exception(f"Client {mac_address} not found")
            
            client = clients[0]
            
            # Get additional info from wireless interface
            wireless_res = api.get_resource(self.RESOURCES["wireless"])
            iface_name = client.get("interface")
            iface_info = {}
            
            if iface_name:
                ifaces = wireless_res.get(name=iface_name)
                if ifaces:
                    iface_info = {
                        "interface_name": iface_name,
                        "ssid": ifaces[0].get("ssid", ""),
                        "mode": ifaces[0].get("mode", ""),
                        "band": ifaces[0].get("band", ""),
                        "frequency": ifaces[0].get("frequency", "")
                    }
            
            # Calculate statistics
            uptime_seconds = client.get("uptime-seconds", "0")
            try:
                uptime_sec = int(uptime_seconds)
                bytes_total = client.get("bytes", "0")
                bytes_val = int(bytes_total) if bytes_total else 0
                
                # Calculate average throughput
                if uptime_sec > 0:
                    avg_throughput = bytes_val / uptime_sec  # Bytes per second
                else:
                    avg_throughput = 0
            except:
                avg_throughput = 0
            
            details = {
                "client_info": {
                    "mac_address": client.get("mac-address", ""),
                    "interface": client.get("interface", ""),
                    "radio_name": client.get("radio-name", ""),
                    "last_ip": client.get("last-ip", ""),
                    "uptime": client.get("uptime", ""),
                    "uptime_seconds": uptime_seconds,
                    "last_activity": client.get("last-activity", ""),
                },
                "signal_info": {
                    "rx_signal": client.get("rx-signal", ""),
                    "tx_signal": client.get("tx-signal", ""),
                    "signal_strength": client.get("signal-strength", ""),
                    "signal_to_noise": client.get("signal-to-noise", ""),
                    "rx_ccq": client.get("rx-ccq", ""),
                    "tx_ccq": client.get("tx-ccq", ""),
                },
                "rate_info": {
                    "rx_rate": client.get("rx-rate", ""),
                    "tx_rate": client.get("tx-rate", ""),
                    "rate_set": client.get("rate-set", ""),
                },
                "connection_info": {
                    "authenticated": client.get("authenticated", "") == "true",
                    "encryption": client.get("encryption", ""),
                    "group_encryption": client.get("group-encryption", ""),
                    "wmm_enabled": client.get("wmm-enabled", "") == "true",
                    "distance": client.get("distance", ""),
                    "ack_timeout": client.get("ack-timeout", ""),
                },
                "statistics": {
                    "bytes": client.get("bytes", ""),
                    "packets": client.get("packets", ""),
                    "frames": client.get("frames", ""),
                    "tx_frames_timed_out": client.get("tx-frames-timed-out", ""),
                    "avg_throughput_bps": round(avg_throughput * 8, 2),  # Convert to bits/sec
                },
                "interface_info": iface_info
            }
            
            logger(f"Retrieved details for client {mac_address}")
            return details
            
        except Exception as e:
            logger(f"Failed to get client details: {str(e)}")
            raise Exception(f"Failed to get client details: {str(e)}")
        finally:
            pool.disconnect()

    def get_interface_clients(self, p, logger=print):
        """
        Get all clients connected to a specific interface
        """
        pool, api = self.core.get_api()
        try:
            if not p.get("interface"):
                raise Exception("Interface name is required")
            
            interface = p["interface"]
            
            # Verify interface exists
            wireless_res = api.get_resource(self.RESOURCES["wireless"])
            ifaces = wireless_res.get(name=interface)
            if not ifaces:
                raise Exception(f"Interface '{interface}' not found")
            
            # Get clients for this interface
            res = api.get_resource(self.RESOURCES["registration"])
            clients = res.get(interface=interface)
            
            interface_info = ifaces[0]
            
            result = {
                "interface": interface,
                "interface_info": {
                    "ssid": interface_info.get("ssid", ""),
                    "mode": interface_info.get("mode", ""),
                    "band": interface_info.get("band", ""),
                    "frequency": interface_info.get("frequency", ""),
                    "running": interface_info.get("running", "") == "true",
                },
                "client_count": len(clients),
                "clients": []
            }
            
            for client in clients:
                client_data = {
                    "mac_address": client.get("mac-address", ""),
                    "radio_name": client.get("radio-name", ""),
                    "uptime": client.get("uptime", ""),
                    "last_activity": client.get("last-activity", ""),
                    "rx_signal": client.get("rx-signal", ""),
                    "tx_signal": client.get("tx-signal", ""),
                    "rx_rate": client.get("rx-rate", ""),
                    "tx_rate": client.get("tx-rate", ""),
                    "bytes": client.get("bytes", ""),
                    "authenticated": client.get("authenticated", "") == "true",
                }
                result["clients"].append(client_data)
            
            logger(f"Found {len(clients)} clients on interface '{interface}'")
            return result
            
        except Exception as e:
            logger(f"Failed to get interface clients: {str(e)}")
            raise Exception(f"Failed to get interface clients: {str(e)}")
        finally:
            pool.disconnect()

    def _seconds_to_human(self, seconds):
        """Convert seconds to human readable format"""
        if not seconds:
            return "0s"
        
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")
        
        return " ".join(parts)