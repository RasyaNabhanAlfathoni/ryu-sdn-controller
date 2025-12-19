import paramiko
import time

class UnifiParamikoDriver:
    name = "paramiko"

    def __init__(self, device_info):
        self.dev = device_info
        self.host = device_info["ip"]
        self.username = device_info["username"]
        self.password = device_info["password"]
        self.client = None

    # =====================================================
    # SSH CONNECT (UniFi / dropbear compatible)
    # =====================================================
    def connect(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.client.connect(
            hostname=self.host,
            username=self.username,
            password=self.password,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
            disabled_algorithms={
                "pubkeys": [
                    "rsa-sha2-256",
                    "rsa-sha2-512"
                ],
                "macs": [
                    "hmac-sha2-256",
                    "hmac-sha2-512",
                ],
                "keys": [
                    "ecdsa-sha2-nistp256",
                    "ecdsa-sha2-nistp384",
                    "ecdsa-sha2-nistp521",
                    "ssh-ed25519"
                ]
            }
        )

    def disconnect(self):
        if self.client:
            self.client.close()

    # =====================================================
    # EXEC INTERACTIVE (WAJIB UNTUK UNIFI)
    # =====================================================
    def exec_interactive(self, command, wait=1.0):
        channel = self.client.invoke_shell()
        channel.settimeout(5)

        # bersihkan banner login
        time.sleep(0.3)
        if channel.recv_ready():
            channel.recv(65535)

        # kirim command
        channel.send(command + "\n")
        time.sleep(wait)

        output = ""
        while channel.recv_ready():
            output += channel.recv(4096).decode(errors="ignore")

        channel.close()
        return output

    # =====================================================
    # PARSE `info` OUTPUT (KHUSUS UNIFI)
    # =====================================================
    def _parse_info(self, text):
        """
        Model:       UAP-LRv2
        Version:     4.3.28.11361
        MAC Address: fc:ec:da:0c:2f:68
        IP Address:  192.168.100.88
        Hostname:    UBNT
        Uptime:      38680 seconds
        """
        data = {}

        for line in text.splitlines():
            line = line.strip()
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            mapping = {
                "model": "model",
                "version": "os_version",
                "mac address": "main_mac_address",
                "ip address": "main_ip_address",
                "hostname": "hostname",
                "uptime": "uptime",
            }

            if key in mapping:
                data[mapping[key]] = value

        return data

    # =====================================================
    # PUBLIC API (dipakai controller)
    # =====================================================
    def get_device_info(self):
        try:
            self.connect()

            out = self.exec_interactive("info")

            if not out or "Model:" not in out:
                raise Exception("Empty info output")

            info = self._parse_info(out)

            print("RAW INFO OUTPUT:\n", out)
            print("PARSED INFO:", info)

            hostname = info.get("hostname")

            return {
                # identity
                "identity": hostname,
                "hostname": hostname,

                # device info
                "model": info.get("model"),
                "os_version": info.get("os_version"),

                # network (INI SEKARANG AMAN)
                "main_ip_address": info.get("main_ip_address"),
                "main_mac_address": info.get("main_mac_address"),

                # metadata
                "vendor": "unifi",
                "device_type": "access_point",
                "connected": True
            }

        except Exception as e:
            raise Exception(f"[UNIFI SSH FAILED] {e}")

        finally:
            self.disconnect()

    def test_connection(self):
        try:
            self.connect()
            out = self.exec_interactive("info")
            return True, out
        except Exception as e:
            return False, str(e)
        finally:
            self.disconnect()