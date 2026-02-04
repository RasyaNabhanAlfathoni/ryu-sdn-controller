class UnifiAPReboot:
    name = "unifi_ap_reboot"

    @staticmethod
    def run(driver, logger=print):

        logger(f"Connecting to {driver.host} as {driver.username}")

        try:
            driver.connect()
            logger("Connected")

            logger("Sending reboot command...")
            out = driver.exec_interactive("reboot")

            if out:
                for line in out.splitlines():
                    logger(f"[UNIFI-OUT] {line}")

            logger("Reboot command sent")
            logger("Device will disconnect shortly")

            return {
                "status": "rebooting",
                "ip": driver.host
            }

        except Exception as e:
            logger(f"[UNIFI-ERROR] {e}")
            raise

        finally:
            driver.disconnect()