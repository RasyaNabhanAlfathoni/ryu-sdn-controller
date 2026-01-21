class MikroTikRouterWirelessScan:
    name = "mikrotikrouter_wireless_scan"

    @staticmethod
    def scan(core, params, logger=print):
        """
        Payload contoh:
        {
            "interface": "wlan1",
            "duration": 5
        }
        """

        interface = params.get("interface", "wlan1")
        duration = int(params.get("duration", 5))

        logger(f"Starting wireless scan: {interface} duration={duration}s")

        pool, api = core.get_api()

        try:
            logger("Executing wireless scan via RouterOS API - using get_resource()")
            
            # Gunakan get_resource() bukan get_binary_resource() untuk perintah CLI
            execute_resource = api.get_resource('/')
            
            # Panggil perintah execute dengan format yang benar
            result = execute_resource.call(f'interface wireless scan {interface} duration={duration}')
            
            logger(f"Execute command result: {result}")
            
            # Parse hasil scan
            results = []
            if result and isinstance(result, list):
                for item in result:
                    if isinstance(item, dict) and "address" in item:
                        results.append({
                            "address": item.get("address"),
                            "ssid": item.get("ssid"),
                            "channel": item.get("channel"),
                            "signal": int(item.get("signal") or 0),
                            "noise_floor": int(item.get("noise-floor") or 0),
                            "snr": int(item.get("snr") or 0),
                            "radio_name": item.get("radio-name"),
                            "interface": item.get("interface", interface),
                        })
                    elif isinstance(item, dict) and "ret" in item:
                        # Jika hasil dalam format text/ret
                        output = item.get("ret", "")
                        logger(f"CLI text output: {output}")
                        # Parse text output jika diperlukan
                        # Format: "AP 60:32:B1:09:2A:8C  tawon ..."

            logger(f"Wireless scan completed: {len(results)} APs found")

            return {
                "status": "success",
                "interface": interface,
                "duration": duration,
                "count": len(results),
                "results": results
            }

        except Exception as e:
            logger(f"Wireless scan failed: {e}")
            import traceback
            logger(traceback.format_exc())
            return {
                "status": "error",
                "error": str(e)
            }

        finally:
            pool.disconnect()