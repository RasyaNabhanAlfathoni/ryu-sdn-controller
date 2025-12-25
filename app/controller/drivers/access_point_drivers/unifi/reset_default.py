class UnifiAPResetDefault:
    name = "unifi_ap_reset_default"

    @staticmethod
    def run(driver, logger=print):

        logger(f"[UNIFI] Connecting to {driver.host} as {driver.username}")

        try:
            driver.connect()
            logger("[UNIFI] Connected")

            logger("[UNIFI] Sending reset default command...")
            out = driver.exec_interactive("set-default")

            if out:
                for line in out.splitlines():
                    logger(f"[UNIFI-OUT] {line}")

            logger("[UNIFI] Reset default command sent")
            logger("[UNIFI] Device will disconnect shortly")

            return {
                "status": "resetting to default",
                "ip": driver.host
            }

        except Exception as e:
            logger(f"[UNIFI-ERROR] {e}")
            raise

        finally:
            driver.disconnect()