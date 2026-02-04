import paramiko
import time


class UnifiParamikoDriver:
    name = "paramiko"
    UNIFI_BASE = "http://11.11.11.11:3000"

    DEFAULT_USER = "ubnt"
    DEFAULT_PASS = "ubnt"

    def __init__(self, device_info):
        self.dev = device_info
        self.host = device_info["ip"]
        self.username = device_info.get("username")
        self.password = device_info.get("password")
        self.client = None
        self.connected = False

    # =====================================================
    # LOW LEVEL CONNECT
    # =====================================================
    def _connect(self, username, password):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.client.connect(
            hostname=self.host,
            username=username,
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=8,
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

    # =====================================================
    # PUBLIC CONNECT (ACTION MODE)
    # =====================================================
    def connect(self):
        """
        Digunakan oleh action:
        reboot, upgrade, inform, dll
        """

        attempts = [
            (self.username, self.password),
            (self.DEFAULT_USER, self.DEFAULT_PASS),
        ]

        last_error = None

        for user, pw in attempts:
            if not user or not pw:
                continue

            try:
                self._connect(user, pw)

                self.username = user
                self.password = pw
                self.connected = True

                return True

            except Exception as e:
                last_error = e
                self.disconnect()

        raise Exception(f"[UNIFI SSH FAILED] {last_error}")

    # =====================================================
    # DISCONNECT
    # =====================================================
    def disconnect(self):
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        self.client = None
        self.connected = False

    # =====================================================
    # EXEC INTERACTIVE
    # =====================================================
    def exec_interactive(self, command, wait=1.0):
        if not self.connected or not self.client:
            raise Exception("SSH not connected")

        channel = self.client.invoke_shell()
        channel.settimeout(5)

        time.sleep(0.3)
        if channel.recv_ready():
            channel.recv(65535)

        channel.send(command + "\n")
        time.sleep(wait)

        output = ""
        while channel.recv_ready():
            output += channel.recv(4096).decode(errors="ignore")

        channel.close()
        return output

    # =====================================================
    # PARSE INFO
    # =====================================================
    def _parse_info(self, text):
        data = {}

        for line in text.splitlines():
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
    # DISCOVERY MODE
    # =====================================================
    def get_device_info(self):
        """
        Stateless discovery:
        connect → info → disconnect
        """

        try:
            self.connect()

            out = self.exec_interactive("info")
            if not out or "Model:" not in out:
                raise Exception("invalid info output")

            info = self._parse_info(out)
            hostname = info.get("hostname")

            return {
                "identity": hostname,
                "hostname": hostname,
                "model": info.get("model"),
                "os_version": info.get("os_version"),
                "main_ip_address": info.get("main_ip_address"),
                "main_mac_address": info.get("main_mac_address"),
                "vendor": "unifi",
                "device_type": "access_point",
                "connected": True,
                "username": self.username,
                "password": self.password,
            }

        finally:
            self.disconnect()

    # =====================================================
    # QUICK TEST
    # =====================================================
    def test_connection(self):
        try:
            info = self.get_device_info()
            return True, info
        except Exception as e:
            return False, str(e)